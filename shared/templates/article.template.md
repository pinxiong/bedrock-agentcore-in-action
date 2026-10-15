# UC{{UC_NUM}} · {{UC_TITLE}}

Follows the series skeleton in [PLAN.md](../../PLAN.md) section 8.3. The operations
doc is `README.md`; this file is the narrative. Keep them separate: the README
must be copy-pasteable, the article must be readable.

> Verified on 2026-XX-XX against AgentCore as of that date.

---

## 1. At a glance

| Field | Value |
|---|---|
| Type | {{walkthrough / deep dive}} |
| Agent | {{what runs: how many agents, how many tools}} |
| AgentCore capabilities used | {{the ones this use case lights up}} |
| Framework and model | {{Strands Agents x.y, model id}} |
| Build type | `CodeZip` |
| Interfaces | {{AgentCore CLI / boto3 control plane / boto3 data plane}} |
| Region | us-east-1 |
| Complexity | D{{DIFFICULTY}}: {{what makes it that rung}} |
| Official group | `{{one of the eight groups listed in docs/08-official-alignment.md}}` |

## 2. The problem

{{Business situation, no technology. Who is unhappy, and about what.}}

## 3. Why the obvious approach breaks

{{The naive solution a competent engineer would try first, and the specific way it
fails in production. This section is where the article earns a reader's attention.}}

## 4. Architecture

{{One diagram. Mark what AgentCore hosts and what you own.}}

## 5. Walkthrough

{{The few commands that matter, each with its real output. Point at
`usecases/{{UC_NUM}}-{{slug}}/` for the full version rather than pasting everything.}}

## 6. Verification

{{Real output from `python aia.py test {{UC_NUM}}`. Assertions, not adjectives.}}

## 7. Cleanup

```bash
python aia.py down {{UC_NUM}}     # wrapper: tag-scoped teardown of this use case only
# the same thing by hand, from the use case root:
agentcore remove all -y && agentcore deploy -y
agentcore status                  # nothing from this use case should be listed
```

{{Say what survives on purpose, and why. Example: the CDK bootstrap stack and its
asset bucket are reused by every later deployment in the account.}}

## 8. What surprised me

{{The thing that cost you an hour. This is what gets shared.}}

## 9. When not to use this

{{Honest boundaries. Say what this is not for.}}

## 10. Files

| Path | What it is | Written by |
|---|---|---|
| `agentcore/agentcore.json` | the contract: every resource this use case declares | you |
| `agentcore/aws-targets.json` | where deployments land | you |
| `app/{{AGENT_NAME}}/` | the agent code `codeLocation` points at | you |
| `raw/` | boto3 sidecar scripts; teaching only, never deployed | you |
| `agentcore/cdk/`, `agentcore/.llm-context/`, `agentcore/.cli/` | generated plumbing | the CLI |

## 11. Related official samples

{{Two to four paths in awslabs/agentcore-samples showing the same capability.
Give the path `NN-layer/NN-group/NN-sample/` plus one line on what to look for.}}

Repository: <https://github.com/awslabs/agentcore-samples>

## 12. Try it yourself

```bash
python aia.py up {{UC_NUM}} && python aia.py test {{UC_NUM}} && python aia.py down {{UC_NUM}}
```

This use case is self-contained: you do not need any other use case deployed first.
