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

from model.load import load_model

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

# One Agent per session id, so a session keeps its own conversation history.
# Bounded, because one process serves many sessions. History is in-process, so a
# cold start loses it.
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


@app.entrypoint
async def invoke(payload: Any, context: Any):
    session_id = getattr(context, "session_id", "default-session")
    prompt = extract_prompt(payload)
    log.info("{{UC_ID}} invoke: model_id=%s session_id=%s", load_model().config.get("model_id"), session_id)

    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()
