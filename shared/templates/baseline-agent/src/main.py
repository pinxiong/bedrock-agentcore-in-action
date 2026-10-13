"""{{UC_ID}} · {{UC_SLUG}}: baseline agent.

SCAFFOLD. The shape below follows the AgentCore Runtime entrypoint contract as
documented on 2026-10-13. Before you write the use case documentation, run
`agentcore dev` once and confirm the import path and decorator name against the
CLI version you actually installed, then correct this file if needed.

This file is deliberately about 20 lines. Its job is to make the use case
deployable on its own; the capability under test lives in the rest of src/.
See the "What you repeated" section of this use case's README.
"""

from __future__ import annotations

import os

MODEL_ID = os.environ.get("MODEL_ID", "{{MODEL_ID}}")

SYSTEM_PROMPT = """{{SYSTEM_PROMPT}}"""


def build_agent():
    """Return an agent object exposing .stream(prompt, session_id=...)."""
    from bedrock_agentcore.runtime import BedrockAgentCoreApp  # type: ignore
    from strands import Agent  # type: ignore
    from strands.models import BedrockModel  # type: ignore

    app = BedrockAgentCoreApp()
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name="us-east-1"),
        system_prompt=SYSTEM_PROMPT,
        tools=[],  # {{UC_ID}}: add this use case's tools here
    )

    @app.entrypoint
    def invoke(payload: dict) -> dict:
        session_id = payload.get("runtimeSessionId") or "local"
        prompt = payload.get("prompt", "")
        result = agent(prompt)
        return {"output": str(result), "sessionId": session_id}

    return app


if __name__ == "__main__":
    build_agent().run()
