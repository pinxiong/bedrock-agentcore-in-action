# AgentCore Project · uc01 First Agent

Context for an AI coding assistant (or a human) working inside this folder.

This file mirrors `AGENTS.md` as the AgentCore CLI writes it on
`agentcore create`, trimmed to what is true for this use case. The folder is a
complete AgentCore project: copy it anywhere and it runs. `make help` lists
everything you can do from here, and `README.md` is the walkthrough.

## Mental model

The project is a **flat resource model**. Agents, memories, credentials,
gateways, evaluators and policies are independent top-level arrays in
`agentcore/agentcore.json`. The schema binds nothing to anything: each resource
is provisioned on its own, and an agent finds a memory or a credential at
runtime through an environment variable or an SDK call. Tags declared in
`agentcore.json` flow through to the deployed CloudFormation resources, which is
how every resource in this series can be traced back to one use case.

## Critical invariants

1. **The JSON is the source of truth.** Do not change agent behaviour by
   editing generated CDK code under `agentcore/cdk/`.
2. **`name` is the resource identity.** It becomes the CloudFormation logical
   ID: renaming destroys and recreates the resource, while changing other
   fields updates it in place.
3. **Validate before deploying.** `agentcore validate` checks the JSON against
   the types in `agentcore/.llm-context/`.
4. **Removal is two steps.** `agentcore remove <resource>` empties the local
   spec; the following `agentcore deploy` reconciles the stack down and does the
   actual deletion.
5. **Validate the runtime payload.** Require the prompt to be a string. Anything
   else is a caller bug that surfaces as a confusing model error.
6. **Keep this folder self-contained.** No absolute paths, no references to a
   parent directory, no imports from outside `app/aia_uc01/`. `make check`
   asserts this, including by copying the folder to a temporary location.

## Layout

```
01-first-agent/
├── AGENTS.md                  # this file
├── run.py                     # every operation, self-contained and cross-platform
├── Makefile                   # forwards to run.py; holds no logic
├── README.md                  # the walkthrough (start here)
├── article.md                 # the narrative version
├── agentcore/
│   ├── agentcore.json         # project spec: what gets deployed
│   ├── aws-targets.json       # deployment targets, account + region
│   ├── .env.local             # local secrets, gitignored
│   ├── .cli/                  # CLI state and downloaded traces
│   ├── .llm-context/          # TypeScript types for the JSON, for AI assistants
│   └── cdk/                   # generated CDK project that does the deployment
├── app/aia_uc01/              # codeLocation: the code that becomes the runtime
│   ├── main.py                # BedrockAgentCoreApp + @app.entrypoint
│   ├── model/load.py          # model provider wiring
│   ├── model/sanitize.py      # strips model scaffolding out of the text stream
│   ├── pyproject.toml         # dependencies, packaged into the deployment zip
│   └── uv.lock
└── tests/
    ├── doctor.py              # environment self-check
    ├── copy_check.py          # asserts this folder stands alone
    ├── smoke.py               # asserts the deployed capabilities
    ├── test_sanitize.py       # offline unit tests
    └── resourcegroupstaggingapi_check.py
```

`app/aia_uc01/` is the only directory that is packaged and deployed. Its path
comes from `codeLocation` in `agentcore.json`, and `entrypoint: main.py`
resolves relative to it.

## Key schema fields

| Field | Values that matter here |
|---|---|
| `runtimes[].build` | `CodeZip` (this series) or `Container` |
| `runtimes[].entrypoint` | `main.py`, relative to `codeLocation` |
| `runtimes[].codeLocation` | `app/aia_uc01/` |
| `runtimes[].runtimeVersion` | `PYTHON_3_10` to `PYTHON_3_14` for CodeZip |
| `runtimes[].networkMode` | `PUBLIC` or `VPC` |
| `runtimes[].protocol` | `HTTP`, `MCP` or `A2A` |
| `runtimes[].envVars` | `MODEL_ID` is read by `model/load.py` |
| top-level `tags` | `Project`, `UseCase`, `AutoDelete` |

The full type definitions are in `agentcore/.llm-context/agentcore.ts`.

## Commands

From this folder:

```bash
python3 run.py help       # list every target (the entry point, cross-platform)
make help                 # the same, if you have make
make check                # does this folder stand alone?
make doctor               # is this machine and this folder ready?
make deploy               # deploy it
make invoke               # call it
make dev                  # run it locally, a real model, no deployment
make test                 # assert the deployed capabilities
make down                 # destroy it
```

`run.py` is the entry point and `Makefile` only forwards to it, so the two can
never disagree. Use whichever your platform has.

`agentcore` must be run from this folder, not from `agentcore/`: inside
`agentcore/` the CLI answers `Please run this command from your project root
directory.` There is no `--region` flag; the region comes from
`agentcore/aws-targets.json`.
