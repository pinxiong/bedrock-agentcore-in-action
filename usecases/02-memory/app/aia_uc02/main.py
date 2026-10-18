"""uc02 · Memory: a reorder assistant that stops asking the same question.

The situation: Northwind Gear runs 40 stores and restocks them weekly. The
manager told the assistant once that only the North China region matters to
them. Next week, in a new session, the assistant asks again. Nothing was wrong
with the model; the fact simply never left the first session.

This file is the smallest agent that fixes that. Three things to point at:

  1. every turn is appended to AgentCore Memory as an event (short term);
  2. every turn is answered with the records the service extracted from earlier
     events (long term);
  3. the actor id is part of the namespace, so two managers cannot read each
     other's preferences.

The tool exists so the answer is checkable: `reorder_candidates` only answers
for one region, so a reply naming two regions proves the preference was not
applied, and a reply naming one proves it was.
"""

from __future__ import annotations

import os
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager

from memory import from_env, render
from model.load import model_id, load_model
from model.sanitize import StreamSanitizer

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.environ.get("AWS_REGION", "us-east-1")

# The header the AgentCore runtime carries when the caller supplies an actor
# identity. It is the Identity surface of this use case: the same value becomes
# the actor id, and therefore the namespace key, on the memory side.
ACTOR_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"
# `agentcore invoke --user-id` travels as this header. Anything under
# X-Amzn-Bedrock-AgentCore-Runtime-Custom- reaches agent code, and this one only
# if it is forwarded; it is tried second, so an explicit actor still wins.
USER_HEADER = "x-amzn-bedrock-agentcore-runtime-user-id"
DEFAULT_ACTOR = "store_manager_north"

SYSTEM_PROMPT = """You are the reorder assistant for Northwind Gear, a chain of
40 stores that restocks every Monday.

What you remember about this store manager is listed below. A remembered
regional preference outranks anything in the question: if the memory says the
manager only cares about one region, reorder for that region and no other.
Call reorder_candidates exactly once, for the region you chose.
If a remembered episode says an approach already failed, say so and choose
differently.
If no regional preference is remembered at all, call reorder_candidates once
for North China, which is the chain default, and say you are guessing.

Answer in at most three short sentences. Name the region and the stores."""

# A fixed catalogue keeps the assertions honest: if the agent answers for two
# regions, that is a memory failure and not a data source being flaky.
CATALOG = {
    "North China": (
        "Beijing Haidian: SKU-1001 thermal flask, 42 units; "
        "Tianjin Heping: SKU-1002 insulated mug, 17 units; "
        "Shijiazhuang Qiaoxi: SKU-1003 lunch box, 8 units"
    ),
    "South China": (
        "Guangzhou Tianhe: SKU-2001 iced tea bottle, 63 units; "
        "Shenzhen Nanshan: SKU-2002 cold cup, 29 units; "
        "Dongguan Nancheng: SKU-2003 straw lid, 11 units"
    ),
    "East China": (
        "Shanghai Pudong: SKU-3001 travel tumbler, 51 units; "
        "Hangzhou Xihu: SKU-3002 coffee press, 22 units; "
        "Nanjing Gulou: SKU-3003 lid gasket, 6 units"
    ),
}


@tool
def reorder_candidates(region: str) -> str:
    """Return the stores in one region that are below their reorder point."""
    return CATALOG.get(region, f"no stores are tracked for region {region!r}")


TOOLS = [reorder_candidates]


def _lookup(headers: Any, name: str) -> str:
    """Read one header whether the mapping is case-insensitive or a plain dict."""
    if not isinstance(headers, dict):
        return ""
    value = headers.get(name) or headers.get(name.title()) or headers.get(name.upper())
    return value.strip() if isinstance(value, str) else ""


def resolve_actor(payload: Any, context: Any) -> str:
    """Who is asking. The actor id is the memory partition key.

    Order matters, and it is the order of trust: an explicit field in the
    payload wins, then the runtime's actor header, then the runtime user id,
    then a named default. Falling back to the session id would silently give
    every session its own memory, which is exactly the bug this use case exists
    to show, so the default is a fixed name and not a fresh random id.
    """
    if isinstance(payload, dict):
        for key in ("actor_id", "actorId", "user_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    # The filtered headers the SDK forwards, then the raw request: the runtime
    # allowlists X-Amzn-Bedrock-AgentCore-Runtime-Custom-* only, so a caller
    # identity sent under another name is visible here or nowhere.
    filtered = getattr(context, "request_headers", None) or {}
    raw = getattr(getattr(context, "request", None), "headers", None)
    log.info(
        "uc02 headers: filtered=%s raw=%s",
        sorted(str(key).lower() for key in filtered) if isinstance(filtered, dict) else None,
        sorted(str(key).lower() for key in raw) if isinstance(raw, dict) else None,
    )
    for headers in (filtered, raw):
        for name in (ACTOR_HEADER, USER_HEADER):
            found = _lookup(headers, name)
            if found:
                return found
    return DEFAULT_ACTOR


def extract_prompt(payload: Any) -> str:
    """Accept a bare string or {"prompt": "..."}; reject anything else."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("prompt", "message", "input"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
    raise ValueError('payload must be a string or contain a "prompt" string')


def _text_delta(text: str, block_index: int) -> dict:
    """The streaming event shape BedrockAgentCoreApp forwards to the client."""
    return {
        "event": {
            "contentBlockDelta": {
                "delta": {"text": text},
                "contentBlockIndex": block_index,
            }
        }
    }


@app.entrypoint
async def invoke(payload: Any, context: Any):
    session_id = getattr(context, "session_id", "default-session")
    actor = resolve_actor(payload, context)
    prompt = extract_prompt(payload)
    log.info("uc02 invoke: model_id=%s actor=%s session=%s", model_id(), actor, session_id)

    # Long-term memory is read before the model is called, because it becomes
    # part of the system prompt: the model has to see the preference to obey it.
    store = from_env(REGION)
    records = store.recall(actor, prompt) if store else []
    log.info("uc02 recalled %d record(s) for actor %s", len(records), actor)

    # A fresh Agent per invoke, not one per session. The system prompt carries
    # this turn's retrieval, so a cached Agent would keep serving last turn's
    # memories; there is no in-process history to preserve in any case.
    agent = Agent(
        model=load_model(),
        system_prompt=f"{SYSTEM_PROMPT}\n\nWhat you remember about this manager:\n{render(records)}",
        tools=list(TOOLS),
        conversation_manager=NullConversationManager(),
    )

    scrub = StreamSanitizer()
    block_index = 0
    reply: list[str] = []
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        inner = event["event"]
        if not isinstance(inner, dict):
            yield event
            continue

        if "messageStart" in inner:
            scrub = StreamSanitizer()
            block_index = 0
            yield event
            continue
        if "messageStop" in inner:
            tail = scrub.flush()
            if tail:
                reply.append(tail)
                yield _text_delta(tail, block_index)
            yield event
            continue

        block = inner.get("contentBlockDelta")
        delta = block.get("delta") if isinstance(block, dict) else None
        if not isinstance(delta, dict) or "text" not in delta:
            yield event
            continue
        block_index = block.get("contentBlockIndex", block_index)
        clean = scrub.feed(delta["text"])
        if clean:
            reply.append(clean)
            yield _text_delta(clean, block_index)

    # Short-term memory. The event is written after the answer so a slow write
    # never delays the reply, and one event carries both turns so the extractor
    # sees the preference in the context of the question that produced it.
    answer = "".join(reply).strip()
    if store and answer:
        event_id = store.remember(actor, session_id, [(prompt, "USER"), (answer, "ASSISTANT")])
        log.info("uc02 wrote event %s for actor %s session %s", event_id, actor, session_id)


if __name__ == "__main__":
    app.run()
