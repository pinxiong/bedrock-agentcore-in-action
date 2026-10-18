# AgentCore Project · {{UC_ID}} {{UC_TITLE}}

Context for an AI coding assistant (or a human) working inside this folder.

This file mirrors `AGENTS.md` as the AgentCore CLI writes it on
`agentcore create`, trimmed to what is true for this use case. The folder is a
complete AgentCore project: copy it anywhere and it runs. Everything you can do
from here is an `agentcore` or `aws` command, and `README.md` is the walkthrough.

There is deliberately no entry-point script in this folder: no `run.py`, no
`Makefile`, no assertion script. The series teaches the CLI, so the reader types
what the article shows. A capability is proven by the captured output of a native
command, saved under `evidence/`.

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
   parent directory, no imports from outside `app/{{AGENT_NAME}}/`. The
   repository-level check reads the folder and fails on any path that escapes it.

## Layout

```
{{UC_SLUG}}/
├── AGENTS.md                  # this file
├── README.md                  # the walkthrough (start here)
├── article.md                 # the narrative version
├── evidence/                  # captures of the native commands that prove it
├── agentcore/
│   ├── agentcore.json         # project spec: what gets deployed
│   ├── aws-targets.json       # deployment targets, account + region
│   ├── .env.local             # local secrets, gitignored
│   ├── .cli/                  # CLI state and downloaded traces
│   ├── .llm-context/          # TypeScript types for the JSON, for AI assistants
│   └── cdk/                   # generated CDK project that does the deployment
├── app/{{AGENT_NAME}}/              # codeLocation: the code that becomes the runtime
│   ├── main.py                # BedrockAgentCoreApp + @app.entrypoint
│   ├── model/load.py          # model provider wiring
│   ├── model/sanitize.py      # strips model scaffolding out of the text stream
│   ├── pyproject.toml         # dependencies, packaged into the deployment zip
│   └── uv.lock
└── tests/
    └── test_sanitize.py       # offline unit tests for this agent's own Python
```

`app/{{AGENT_NAME}}/` is the only directory that is packaged and deployed. Its path
comes from `codeLocation` in `agentcore.json`, and `entrypoint: main.py`
resolves relative to it.

## Key schema fields

| Field | Values that matter here |
|---|---|
| `runtimes[].build` | `CodeZip` (this series) or `Container` |
| `runtimes[].entrypoint` | `main.py`, relative to `codeLocation` |
| `runtimes[].codeLocation` | `app/{{AGENT_NAME}}/` |
| `runtimes[].runtimeVersion` | `PYTHON_3_10` to `PYTHON_3_14` for CodeZip |
| `runtimes[].networkMode` | `PUBLIC` or `VPC` |
| `runtimes[].protocol` | `HTTP`, `MCP` or `A2A` |
| `runtimes[].envVars` | `MODEL_ID` is read by `model/load.py` |
| top-level `tags` | `Project`, `UseCase`, `AutoDelete` |

The full type definitions are in `agentcore/.llm-context/agentcore.ts`.

## Commands

From this folder:

```bash
agentcore validate                        # is the JSON contract valid?
agentcore deploy -y --target default      # deploy it
agentcore status                          # what is deployed, and is it READY
agentcore invoke --prompt "..."           # call it
agentcore traces list                     # list today's traces
agentcore traces get <trace-id>           # one trace, pipe it through jq
agentcore remove all -y                   # empty the local spec ...
agentcore deploy -y --target default      # ... and reconcile the stack down
```

The teardown is two commands on purpose: `remove all -y` empties
`agentcore/agentcore.json`, and the following `deploy` is what actually drives
the stack to nothing. Because the first one rewrites the contract, restore
`agentcore/agentcore.json` and `agentcore/aws-targets.json` from git before you
deploy again.

`aws resourcegroupstaggingapi get-resources` is how you prove the teardown was
scoped to this use case:

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,uc:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
```

`--tag-filters` is AND across filters and OR within one filter's `Values`. So
`Key=UseCase,Values=01 Key=UseCase,Values=02` asks for one resource that is two
use cases at once: it returns empty every time and looks like a pass. To ask
for "any of these use cases", use one filter:
`Key=UseCase,Values=01,02,03`.

`agentcore` must be run from this folder, not from `agentcore/`: inside
`agentcore/` the CLI answers `Please run this command from your project root
directory.` There is no `--region` flag; the region comes from
`agentcore/aws-targets.json`.

Save the output of every one of these under `evidence/` as you go. A capability
goes in the article only when the capture that proves it is on disk.
