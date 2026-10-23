# AgentCore Project · uc04 Policy

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

The gateway exists to be intercepted. One Lambda target exposes two tools
(`approveRefund`, `processRefund`), and a policy engine attached to the gateway
checks every tool call before the backend runs. The mode lives on the gateway
(`policyEngineConfiguration.mode`: LOG_ONLY or ENFORCE), the statements live on
the engine (`policies[].statement`, Cedar), and neither is in the agent's code.
The agent is a plain Strands loop that speaks MCP; it cannot bypass, see, or
argue with the engine.

## Critical invariants

1. **The JSON is the source of truth.** Do not change agent behaviour by
   editing generated CDK code under `agentcore/cdk/`.
2. **`name` is the resource identity.** Renaming destroys and recreates the
   resource; other fields update in place.
3. **Validate before deploying.** `agentcore validate` checks the JSON.
4. **A forbid-only engine never deploys.** The service rejects a policy set
   that would deny every request for an action ("Overly Restrictive"), and also
   rejects an unconditional permit ("Overly Permissive"). Permits with a `when`
   condition are the working shape; unpermitted calls are denied by default.
5. **The approval tool needs its own permit.** In ENFORCE mode every
   unpermitted action is blocked, so `approveRefund` carries
   `approvalAlways`; without it the ceiling silently breaks the human loop.
6. **Keep this folder self-contained.** No absolute paths, no references to a
   parent directory, no imports from outside `app/aia_uc04/`.

## Layout

```
04-policy/
├── AGENTS.md                  # this file
├── README.md                  # the walkthrough (start here)
├── evidence/                  # captures of the native commands that prove it
├── agentcore/
│   ├── agentcore.json         # project spec: runtime, gateway, policy engine
│   ├── aws-targets.json       # deployment targets, account + region
│   ├── gateway/refund-tools.json  # the two tool schemas behind the Lambda
│   ├── policies/              # generated Cedar statements live in the JSON
│   ├── .cli/                  # CLI state and logs (deployed-state.json committed)
│   └── cdk/                   # generated CDK project that does the deployment
├── app/aia_uc04/              # codeLocation: the code that becomes the runtime
│   ├── main.py                # BedrockAgentCoreApp + @app.entrypoint + MCP tools
│   ├── mcp_client/client.py   # the one outbound connection: the gateway
│   ├── model/load.py          # MODEL_ID -> BedrockModel
│   ├── model/sanitize.py      # strips model scaffolding out of the text stream
│   └── pyproject.toml         # dependencies, packaged into the deployment zip
├── infra/refund_api.py        # the Lambda the gateway calls (deployed by script 2)
└── tests/
    └── test_sanitize.py       # offline unit tests for this agent's own Python
```

## Commands

From this folder:

```bash
agentcore validate                        # is the JSON contract valid?
agentcore deploy -y --target default      # deploy it
agentcore status                          # what is deployed, and is it READY
agentcore invoke --prompt "..."           # call it
agentcore add policy-engine ...           # create the engine, attach to a gateway
agentcore add policy --engine ... -g "..." # natural language -> Cedar
agentcore remove all -y                   # empty the local spec ...
agentcore deploy -y --target default      # ... and reconcile the stack down
```

`agentcore` must be run from this folder, not from `agentcore/`. There is no
`--region` flag; the region comes from `agentcore/aws-targets.json`.

Switching LOG_ONLY to ENFORCE is one field edit in `agentcore/agentcore.json`
(`agentCoreGateways[0].policyEngineConfiguration.mode`) plus a redeploy.

Save the output of every one of these under `evidence/` as you go. A capability
goes in the article only when the capture that proves it is on disk.
