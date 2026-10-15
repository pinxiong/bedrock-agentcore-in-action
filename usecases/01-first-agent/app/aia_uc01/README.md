# UC01 agent code

`agentcore/agentcore.json` points `codeLocation` here. `main.py` is the
entrypoint the AgentCore Runtime calls; `model/load.py` picks the Bedrock model
from `MODEL_ID`.

    uv sync                       # local .venv for agentcore dev
    agentcore deploy              # from the use case root, not from here
