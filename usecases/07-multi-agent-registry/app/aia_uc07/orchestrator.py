"""uc07 orchestrator: an AG-UI protocol endpoint that routes to specialists.

The orchestrator is deliberately deterministic. The reasoning lives in the
two specialists behind it; this process is the workflow layer a contract
review desk actually operates: it discovers the specialists, hands work to
them over A2A, and reports what happened. Keeping it model-free also makes
every mechanism in this use case reproducible: the same prompt always runs
the same A2A exchange.

Routes (matched on the last user message):

  "store codeword X" / "recall codeword"  per-session state, the isolation demo
  "review contract <id>"                  blocking A2A calls to both specialists
  "deep scan <id>"                        non-blocking send + tasks/get polling
  "barge in <id>"                         message/stream interrupted by tasks/cancel
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any, AsyncIterator

from ag_ui.core import (
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from bedrock_agentcore.runtime.ag_ui import AGUIApp

import a2a_client

app = AGUIApp()
log = logging.getLogger(__name__)

LEGAL_AGENT = os.environ.get("LEGAL_AGENT_NAME", "aia_uc07_legal")
COMPLIANCE_AGENT = os.environ.get("COMPLIANCE_AGENT_NAME", "aia_uc07_compliance")

# The deep scan takes ~75s on the specialist. The synchronous ceiling this
# use case demonstrates is the 60s default read timeout of a bare HTTP
# client; anything past it must run as an A2A task, not a blocking call.
POLL_INTERVAL_SECONDS = 5

# Per-session scratch state for the isolation demo. One AgentCore session is
# one microVM, so this dict can only ever hold the codeword of the session
# this process serves.
_codewords: dict[str, str] = {}

CONTRACTS = {
    "c-118": "Master services agreement, 4 pages. Clause 7 caps liability at fees paid; "
    "clause 11 allows termination for convenience with 30 days notice; clause 14 is silent "
    "on subcontractor vetting.",
    "c-042": "Data processing addendum, 2 pages. Breach notification within 72 hours; "
    "no audit rights; sub-processors listed in annex B.",
}


def _last_user_text(run_input: Any) -> str:
    for message in reversed(run_input.messages or []):
        if getattr(message, "role", None) == "user" and getattr(message, "content", None):
            return str(message.content).strip()
    return ""


async def _review_contract(contract_id: str) -> AsyncIterator[str]:
    """Blocking A2A: both specialists answer inside one synchronous exchange."""
    brief = CONTRACTS.get(contract_id.lower())
    if brief is None:
        yield f"unknown contract {contract_id}; on file: {', '.join(sorted(CONTRACTS))}\n"
        return
    yield f"contract {contract_id}: {brief}\n"

    legal_arn = a2a_client.find_runtime_arn(LEGAL_AGENT)
    compliance_arn = a2a_client.find_runtime_arn(COMPLIANCE_AGENT)
    yield "discovery: both specialist ARNs resolved via ListAgentRuntimes\n"

    card = await asyncio.to_thread(a2a_client.fetch_agent_card, legal_arn)
    skills = ", ".join(s.get("name", "?") for s in card.get("skills", [])) or "none declared"
    yield f"agent card: {card.get('name')} v{card.get('version')} — skills: {skills}\n"

    session_id = f"uc07-review-{uuid.uuid4().hex}"
    yield f"-> legal specialist over A2A (session {session_id[:24]}...)\n"
    legal_task = await asyncio.to_thread(
        a2a_client.send_message,
        legal_arn,
        f"Review this contract brief and name every clause that needs redrafting, with the reference wording: {brief}",
        session_id,
    )
    yield f"legal task {legal_task.get('id')} -> {legal_task.get('status', {}).get('state')}\n"
    yield f"legal says: {a2a_client.task_text(legal_task)}\n"

    yield "-> compliance specialist over A2A\n"
    compliance_task = await asyncio.to_thread(
        a2a_client.send_message,
        compliance_arn,
        f"Quick compliance screen of this contract brief, list the top risks: {brief}",
        session_id,
    )
    yield f"compliance task {compliance_task.get('id')} -> {compliance_task.get('status', {}).get('state')}\n"
    yield f"compliance says: {a2a_client.task_text(compliance_task)}\n"
    yield "review complete: both specialists answered over A2A\n"


async def _deep_scan_async(contract_id: str) -> AsyncIterator[str]:
    """The async pattern: non-blocking send, then poll until the task ends."""
    compliance_arn = a2a_client.find_runtime_arn(COMPLIANCE_AGENT)
    session_id = f"uc07-scan-{uuid.uuid4().hex}"
    started = time.monotonic()

    task = await asyncio.to_thread(
        a2a_client.send_message,
        compliance_arn,
        f"deep scan contract {contract_id}",
        session_id,
        False,
    )
    task_id = task.get("id")
    state = (task.get("status") or {}).get("state")
    yield f"task {task_id} accepted non-blocking at 0.0s, state={state}\n"

    while state not in ("completed", "failed", "canceled", "rejected"):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        task = await asyncio.to_thread(a2a_client.get_task, compliance_arn, task_id, session_id)
        state = (task.get("status") or {}).get("state")
        elapsed = time.monotonic() - started
        yield f"polled at {elapsed:.1f}s: state={state}\n"

    elapsed = time.monotonic() - started
    yield f"task finished at {elapsed:.1f}s — past the 60s synchronous ceiling\n"
    yield f"result: {a2a_client.task_text(task)}\n"


async def _deep_scan_barge_in(contract_id: str) -> AsyncIterator[str]:
    """Barge-in: stream the deep scan, interrupt it with tasks/cancel."""
    compliance_arn = a2a_client.find_runtime_arn(COMPLIANCE_AGENT)
    session_id = f"uc07-barge-{uuid.uuid4().hex}"
    started = time.monotonic()
    task_id = None
    updates = 0

    stream = a2a_client.stream_message(compliance_arn, f"deep scan contract {contract_id}", session_id)
    async for event in stream:
        kind = event.get("kind")
        if kind == "task":
            task_id = event.get("id")
            yield f"stream opened: task {task_id}, state={event.get('status', {}).get('state')}\n"
            continue
        if kind == "status-update":
            state = (event.get("status") or {}).get("state")
            updates += 1
            elapsed = time.monotonic() - started
            yield f"status update #{updates} at {elapsed:.1f}s: state={state}\n"
            if updates == 1 and task_id:
                yield "barging in: sending tasks/cancel now\n"
                cancelled = await asyncio.to_thread(
                    a2a_client.cancel_task, compliance_arn, task_id, session_id
                )
                cancel_state = (cancelled.get("status") or {}).get("state")
                yield f"cancel acknowledged: state={cancel_state}\n"
            if event.get("final"):
                elapsed = time.monotonic() - started
                yield f"stream closed at {elapsed:.1f}s with state={state} — the scan was interrupted, not completed\n"
                return
    yield "stream ended without a final event\n"


async def _route(text: str, session_id: str) -> AsyncIterator[str]:
    lowered = text.lower()

    if lowered.startswith("store codeword "):
        word = text.split(None, 2)[2].strip()
        _codewords[session_id] = word
        yield f"codeword stored for session {session_id}\n"
        return
    if "recall codeword" in lowered or "what" in lowered and "codeword" in lowered:
        word = _codewords.get(session_id)
        yield f"codeword for session {session_id}: {word if word else 'nothing stored'}\n"
        return

    if lowered.startswith("review contract"):
        contract_id = text.split()[-1]
        async for chunk in _review_contract(contract_id):
            yield chunk
        return
    if lowered.startswith("deep scan"):
        contract_id = text.split()[-1]
        async for chunk in _deep_scan_async(contract_id):
            yield chunk
        return
    if lowered.startswith("barge in"):
        contract_id = text.split()[-1]
        async for chunk in _deep_scan_barge_in(contract_id):
            yield chunk
        return

    yield (
        "uc07 contract review orchestrator. Commands:\n"
        "  review contract C-118   both specialists over A2A, blocking\n"
        "  deep scan C-118         the 75s scan as an async A2A task\n"
        "  barge in C-118          stream the scan, then cancel it mid-flight\n"
        "  store codeword X / recall codeword   session isolation check\n"
    )


@app.entrypoint
async def handle(run_input: Any, context: Any):
    session_id = getattr(context, "session_id", None) or f"local-{uuid.uuid4().hex[:12]}"
    text = _last_user_text(run_input)
    log.info("uc07 orchestrator: session=%s text=%r", session_id, text[:80])

    yield RunStartedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id)
    message_id = uuid.uuid4().hex
    yield TextMessageStartEvent(message_id=message_id, role="assistant")
    try:
        async for chunk in _route(text, session_id):
            yield TextMessageContentEvent(message_id=message_id, delta=chunk)
    except Exception as exc:  # surface routing failures inside the stream
        log.exception("orchestrator route failed")
        yield TextMessageContentEvent(message_id=message_id, delta=f"orchestrator error: {exc}\n")
    yield TextMessageEndEvent(message_id=message_id)
    yield RunFinishedEvent(thread_id=run_input.thread_id, run_id=run_input.run_id)


if __name__ == "__main__":
    app.run()
