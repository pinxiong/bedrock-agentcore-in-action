"""{{UC_ID}} · {{UC_SLUG}}: baseline agent.

The entrypoint contract below was verified against agentcore CLI 0.31.1 on
2026-10-14, together with `bedrock-agentcore` and `strands-agents`:

    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    app = BedrockAgentCoreApp()
    @app.entrypoint
    async def invoke(payload, context):   # async, yields streamed events

It is deliberately small. Its job is to make this use case deployable on its
own; the capability under test lives in the rest of src/. See the
"What you repeated" section of this use case's README.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager

from model.load import load_model, model_id
from model.sanitize import StreamSanitizer

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT = """{{UC_ID}}: replace this with the system prompt this use case needs."""


@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b


# {{UC_ID}}: replace with the tools this use case is actually about. One tool is
# kept here so the Observability trace has a span to show.
TOOLS = [add_numbers]

# One Agent per session id, bounded because one process serves many sessions.
# NullConversationManager keeps no transcript at all, so a session here reuses
# the Agent object rather than remembering anything. UC02 adds Memory for that,
# and in-process history would be lost on a cold start in any case.
MAX_SESSIONS = 128
_agents: "OrderedDict[str, Agent]" = OrderedDict()


def get_or_create_agent(session_id: str) -> Agent:
    if session_id in _agents:
        _agents.move_to_end(session_id)
        return _agents[session_id]
    if len(_agents) >= MAX_SESSIONS:
        _agents.popitem(last=False)
    _agents[session_id] = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=list(TOOLS),
        conversation_manager=NullConversationManager(),
    )
    return _agents[session_id]


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
    prompt = extract_prompt(payload)
    log.info("{{UC_ID}} invoke: model_id=%s session_id=%s", model_id(), session_id)

    # The model leaks its own chat-template scaffolding into the text channel
    # (see model/sanitize.py), so every text delta is filtered before it leaves
    # the runtime. Tool-use deltas pass through untouched.
    agent = get_or_create_agent(session_id)
    scrub = StreamSanitizer()
    block_index = 0
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        inner = event["event"]
        if not isinstance(inner, dict):
            yield event
            continue

        # One tool-using turn is several assistant messages. Only the message
        # that announces the tool call carries scaffolding, so each message gets
        # a clean filter: a cut inside one must not silence the next.
        if "messageStart" in inner:
            scrub = StreamSanitizer()
            block_index = 0
            yield event
            continue
        if "messageStop" in inner:
            tail = scrub.flush()
            if tail:
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
            yield _text_delta(clean, block_index)


if __name__ == "__main__":
    app.run()
