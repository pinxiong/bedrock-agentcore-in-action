# AgentCore Project · uc02 Memory

Context for an AI coding assistant (or a human) working inside this folder.

This file mirrors `AGENTS.md` as the AgentCore CLI writes it on `agentcore create`,
trimmed to what is true for this use case. The folder is a complete AgentCore
project: copy it anywhere and it runs. Everything you can do from here is an
`agentcore` or `aws` command; `README.md` is the walkthrough.

## Mental model

The project is a **flat resource model**. Agents, memories, credentials,
gateways, evaluators and policies are independent top-level arrays in
`agentcore/agentcore.json`. The schema binds nothing to anything: each resource
is provisioned on its own, and an agent finds a memory or a credential at
runtime through an environment variable or an SDK call. Tags declared in
`agentcore.json` flow through to the deployed CloudFormation resources, which is
how every resource in this series can be traced back to one use case.

Memory itself is two mechanisms wearing one name. Short term is `CreateEvent`:
an append-only log keyed by (actor, session). Long term is
`RetrieveMemoryRecords`: records the service extracted out of those events and
filed under a namespace. Extraction is asynchronous and everything about timing
follows from that.

## Critical invariants

1. **The JSON is the source of truth.** Do not change agent behaviour by
   editing generated CDK code under `agentcore/cdk/`.
2. **`name` is the resource identity.** It becomes the CloudFormation logical
   ID: renaming destroys and recreates the resource, while changing other
   fields updates it in place.
3. **Validate before deploying.** `agentcore validate` checks the JSON against
   the types in `agentcore/.llm-context/`.
4. **Removal is two steps.** `agentcore remove all -y` empties the local spec;
   the following `agentcore deploy -y --target default` reconciles the stack
   down and does the actual deletion. `-y` is mandatory in any non-interactive
   shell. Restore `agentcore.json` and `aws-targets.json` from git afterwards.
5. **Validate the runtime payload.** Require the prompt to be a string. Anything
   else is a caller bug that surfaces as a confusing model error.
6. **Keep this folder self-contained.** No absolute paths, no references to a
   parent directory, no imports from outside `app/aia_uc02/`. The repository
   tooling asserts this; nothing inside the folder does it at runtime.
7. **Put the actor id inside the namespace.** Isolation is a property of the key
   space here, not of a filter some code path remembers to apply.

## Layout

```
02-memory/
├── AGENTS.md                  # this file
├── README.md                  # the walkthrough (start here)
├── evidence/                  # raw captures from the run the article quotes
├── agentcore/
│   ├── agentcore.json         # project spec: what gets deployed
│   ├── aws-targets.json       # deployment targets, account + region
│   ├── .env.local             # local secrets, gitignored
│   ├── .cli/                  # CLI state and downloaded traces
│   ├── .llm-context/          # TypeScript types for the JSON, for AI assistants
│   └── cdk/                   # generated CDK project that does the deployment
├── app/aia_uc02/              # codeLocation: the code that becomes the runtime
│   ├── main.py                # BedrockAgentCoreApp + @app.entrypoint
│   ├── memory.py              # the two halves: create_event vs retrieve_memories
│   ├── model/load.py          # model provider wiring
│   ├── model/sanitize.py      # strips model scaffolding out of the text stream
│   ├── pyproject.toml         # dependencies, packaged into the deployment zip
│   └── uv.lock
└── tests/
    └── test_sanitize.py       # offline unit tests
```

`app/aia_uc02/` is the only directory that is packaged and deployed. Its path
comes from `codeLocation` in `agentcore.json`, and `entrypoint: main.py`
resolves relative to it. There is deliberately no script of its own here: every
operation is a command you type.

## Key schema fields

| Field | Values that matter here |
|---|---|
| `runtimes[].build` | `CodeZip` (this series) or `Container` |
| `runtimes[].entrypoint` | `main.py`, relative to `codeLocation` |
| `runtimes[].codeLocation` | `app/aia_uc02/` |
| `runtimes[].runtimeVersion` | `PYTHON_3_10` to `PYTHON_3_14` for CodeZip |
| `runtimes[].networkMode` | `PUBLIC` or `VPC` |
| `runtimes[].protocol` | `HTTP`, `MCP` or `A2A` |
| `runtimes[].envVars` | `MODEL_ID` is read by `model/load.py` |
| `memories[].strategies[].type` | `USER_PREFERENCE`, `SEMANTIC`, `EPISODIC` |
| `memories[].eventExpiryDuration` | days an event survives in the short-term log |
| top-level `tags` | `Project`, `UseCase`, `AutoDelete` |

The full type definitions are in `agentcore/.llm-context/agentcore.ts`.

## Commands

From this folder:

```bash
agentcore validate                       # check the JSON against the schema types
agentcore deploy -y --target default     # deploy it
agentcore status                         # runtime READY plus the three strategies
agentcore invoke --prompt "..."          # call it
agentcore invoke --user-id store_manager_south --session-id <id> --prompt "..."
agentcore dev -l                         # run it locally, a real model, no deployment
agentcore traces list                    # recent traces
agentcore traces get <trace id>          # download one trace
agentcore remove all -y                  # empty the local spec; follow with a deploy
agentcore deploy -y --target default     # the reconciling deploy that deletes
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action --region us-east-1
```

`agentcore` must be run from this folder, not from `agentcore/`: inside
`agentcore/` the CLI answers `Please run this command from your project root
directory.` There is no `--region` flag; the region comes from
`agentcore/aws-targets.json`.

Two things about invoking that matter here:

- `--session-id` decides whether this turn continues a conversation or starts a
  new one. It is at least 33 characters, so build it from two uuid halves.
- `--user-id` decides whose memories are read. It arrives as
  `X-Amzn-Bedrock-AgentCore-Runtime-User-Id` and `main.py` turns it into the
  namespace key. Passing an actor through `-H "x-amzn-bedrock-agentcore-runtime-
  custom-actor-id: ..."` does not work on a SigV4 invoke with CLI 0.31.1: the
  header never reaches the agent, and every invoke silently lands on the default
  actor. Verify with `aws logs filter-log-events` on the runtime log group,
  which prints `uc02 invoke: ... actor=<who>` per invoke.
