"""uc02 · the two halves of AgentCore Memory, kept apart on purpose.

Short term is `CreateEvent`: an append-only log of what was said in one session,
keyed by (actor, session). Long term is `RetrieveMemoryRecords`: facts the
service extracted out of those events and filed under a namespace. This module
is the only place in the agent that knows the difference.

The namespace layout comes straight from `agentcore/agentcore.json`, where the
CLI wrote it when the memory resource was added:

    USER_PREFERENCE   /users/{actorId}/preferences
    SEMANTIC          /users/{actorId}/facts
    EPISODIC          /episodes/{actorId}/{sessionId}
                      reflection -> /episodes/{actorId}

Two things follow from that layout and they are the whole point of the use case:

  * the actor id is inside the namespace, so isolation is a property of the key
    space, not of a filter the agent remembers to apply; and
  * episodes are retrieved by path prefix (`/episodes/{actorId}/`), so one call
    reaches both this session's episodes and the reflection written over all of
    them.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from bedrock_agentcore.memory import MemoryClient

log = logging.getLogger(__name__)

# The name in `agentcore.json`, and the key the CLI's CDK project derives from
# it when it injects the memory id into the runtime.
MEMORY_NAME = "aia_uc02_mem"

PREFERENCES = "/users/{actor}/preferences"
FACTS = "/users/{actor}/facts"
# Episodes are read by path prefix and not by exact namespace: the reflection
# namespace sits one level above the per-session one, and a prefix read reaches
# both. The trailing slash is what makes it a prefix rather than a name.
EPISODES = "/episodes/{actor}/"

# One record per namespace is enough for a reorder decision, and a small top_k
# is what keeps the system prompt from growing into a second conversation.
TOP_K = 3


class MemoryStore:
    """Read and write one AgentCore Memory resource."""

    def __init__(self, memory_id: str, region: str) -> None:
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region)

    def recall(self, actor: str, query: str) -> list[dict[str, str]]:
        """Long-term memory: what the service has extracted about this actor.

        A failure here must never break the answer. An agent that cannot
        remember is still useful; an agent that 500s because a retrieval call
        timed out is not. Every namespace is tried on its own for the same
        reason: one bad namespace should not cost the other two.
        """
        found: list[dict[str, str]] = []
        for label, namespace, by_path in (
            ("preference", PREFERENCES.format(actor=actor), False),
            ("fact", FACTS.format(actor=actor), False),
            ("episode", EPISODES.format(actor=actor), True),
        ):
            try:
                kwargs: dict[str, Any] = {
                    "memory_id": self.memory_id,
                    "query": query,
                    "top_k": TOP_K,
                }
                if by_path:
                    kwargs["namespace_path"] = namespace
                else:
                    kwargs["namespace"] = namespace
                records = self.client.retrieve_memories(**kwargs) or []
            except Exception as exc:  # noqa: BLE001 - one bad namespace is not fatal
                log.warning("uc02 recall failed for %s (%s): %s", label, namespace, exc)
                continue
            for record in records:
                text = _text(record)
                if text:
                    found.append({"kind": label, "namespace": namespace, "text": text})
        return found

    def remember(self, actor: str, session_id: str, turns: list[tuple[str, str]]) -> str | None:
        """Short-term memory: append this turn to the session's event log.

        Writing the event is also what triggers long-term extraction, so a
        preference stated here is retrievable from a later session without the
        agent doing anything else.
        """
        try:
            event = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=actor,
                session_id=session_id,
                messages=turns,
            )
        except Exception as exc:  # noqa: BLE001 - a lost event must not fail the invoke
            log.warning("uc02 create_event failed for actor %s: %s", actor, exc)
            return None
        return event.get("eventId")


def _text(record: Any) -> str:
    """Memory records arrive as {'content': {'text': ...}} behind an optional key."""
    if not isinstance(record, dict):
        return ""
    content = record.get("content")
    if isinstance(content, dict):
        inner = content.get("text")
        if isinstance(inner, str):
            return inner.strip()
        if isinstance(inner, dict) and isinstance(inner.get("text"), str):
            return inner["text"].strip()
    if isinstance(record.get("text"), str):
        return record["text"].strip()
    return ""


def memory_id_from_env() -> str:
    """Find the memory id the deployment wired into this process.

    The CLI does not pick one name for this; it derives it from the memory name
    in `agentcore.json`, so a memory called `aia_uc02_mem` arrives as
    `MEMORY_AIA_UC02_MEM_ID`. Reading that name explicitly is better than
    scanning, because a project that later carries two memories has two
    variables and only one of them is this agent's.
    """
    for key in ("MEMORY_ID", f"MEMORY_{MEMORY_NAME.upper()}_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    for key, value in os.environ.items():
        if key.startswith("MEMORY_") and key.endswith("_ID") and str(value).strip():
            return str(value).strip()
    return ""


def from_env(region: str) -> MemoryStore | None:
    """Build the store from the environment, or None when nothing is wired.

    `None` is a supported state, not an error: it lets `agentcore dev` run the
    same file without a deployed memory resource, and the agent then behaves
    like the forgetful one from the use case story.
    """
    memory_id = memory_id_from_env()
    if not memory_id:
        log.warning("uc02 no MEMORY_*_ID in the environment; the agent will run without memory")
        return None
    return MemoryStore(memory_id=memory_id, region=region)


def render(records: list[dict[str, str]]) -> str:
    """Turn retrieved records into a block the system prompt can carry."""
    if not records:
        return "No stored preferences, facts or past episodes for this manager."
    lines = [f"- ({r['kind']}) {r['text']}" for r in records]
    return "\n".join(lines)
