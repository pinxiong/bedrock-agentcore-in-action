"""uc01 · First Agent: the whole deployment loop, one small agent.

This file stays small on purpose. UC01 teaches the loop, not the agent:

    write code -> agentcore deploy -> agentcore invoke -> read the trace -> remove

Three things the reader should be able to point at afterwards:

  1. a runtime that `agentcore deploy` created in their own account
  2. a reply that came back from inside that runtime
  3. a trace in CloudWatch that shows the tool call, not only the final text

The tool exists so the trace has something to show. A prompt that never calls
a tool produces a single span and proves very little about Observability.
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

SYSTEM_PROMPT = """You are a concise assistant.
When a question involves arithmetic, call the add_numbers tool instead of
working it out yourself, then state the result in one short sentence."""


@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b


TOOLS = [add_numbers]

# One Agent per session id, so a session keeps its own conversation history.
# The cache is bounded: one process serving many sessions must not leak history
# between them or grow without limit. This history lives in the process, so a
# cold start loses it. UC02 replaces it with AgentCore Memory.
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
    """Accept a bare string or {"prompt": "..."}; reject anything else.

    UC01 talks to the runtime directly, so the payload is a plain prompt. The
    richer payload shapes (message history, tool results) belong to Harness,
    which UC05 covers.
    """
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
    log.info("uc01 invoke: model_id=%s session_id=%s", load_model().config.get("model_id"), session_id)

    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()
