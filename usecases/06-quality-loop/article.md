# UC06 · Quality Loop

Follows the series article skeleton defined in the repository plan, section 8.3.
The operations doc is `README.md`; this file is the narrative. Keep them separate:
the README must be copy-pasteable, the article must be readable.

> Verified on 2026-10-25 against AgentCore as of that date. Account ids in captured
> output are redacted to `123456789012`.

---

## 1. At a glance

| Field | Value |
|---|---|
| Type | Deep dive (D4) |
| Agent | One expense-audit runtime agent (Strands), three tools, one deliberately stale prompt |
| AgentCore capabilities used | Observability, Evaluations, Optimization, versioning and endpoints; Gateway incidentally (A/B split) |
| Framework and model | Strands Agents 1.62, `deepseek.v3.2` (agent and both evaluators) |
| Build type | `CodeZip` |
| Interfaces | AgentCore CLI (`run eval/batch-evaluation/insights/recommendation/ab-test`, `view`, `pause`) |
| Region | us-east-1 |
| Complexity | D4: quality evidence chain over probabilistic output — distributions, baselines, statistical significance |
| Official group | `06-observe-evaluate-optimize-your-agent` |

## 2. The problem

The travel desk's expense auditor has run unchanged for two months. Finance
notices that international hotel bills keep coming back approved at suspiciously
round numbers, and nobody can name the instruction responsible. A model asked
to grade itself has neither a distribution nor a baseline; "it seems wrong"
is not actionable, and neither is "we redeployed and hope".

## 3. Why the obvious approach breaks

Ask the model whether it handled currencies correctly and it will argue it did —
the same prompt that caused the failure also grades it. Spot-checking one
session proves nothing about the next. And even a correct diagnosis does not
ship itself: a prompt fix is a code deploy, a deploy resets the conversation of
every in-flight session, and there is no way to prove the new prompt is better
rather than merely different. What is missing is the whole loop: spans that
survive the request, evaluators that score history independently of the model's
opinion, a clustering step that names the failure, a versioning scheme that
splits live traffic, and a gate that keeps the floor.

## 4. Architecture

One runtime agent, one gateway, one configuration bundle with two versions, two
evaluators, two online evaluation configs, one dataset, and the shared
`aws/spans` log group. See the diagram in the English article
(`articles/agentcore-evaluate-and-optimize.md`, figure `F1-quality-loop`).

- AgentCore hosts: runtime, gateway, evaluators, online eval, bundle versions,
  dataset, span ingestion into CloudWatch.
- You own: the agent code, the two prompt versions, the dataset content, the
  quality baseline, and the CI workflow that enforces it.

## 5. Walkthrough

The full copy-paste version is `README.md` §7. The shape:

1. Declare the seven resources (`agentcore add gateway/evaluator/online-eval/
   config-bundle/dataset`), deploy once.
2. Reproduce the defect: ten audit sessions, six on non-USD receipts, all six
   wrong the same way (`evidence/30-invoke-prod-*`).
3. Read the spans: 22 tool spans across 11 sessions, zero `convert_currency`
   (`evidence/36-spans-prod.json`).
4. Score it three offline ways (`run eval`, `run batch-evaluation`,
   `run eval --dataset`); the fourth mode, online evaluation, scores live
   traffic during the A/B test.
5. Cluster the failures (`run insights` + `view insights`): 8 of 17 sessions
   share one root cause, `fixType: SYSTEM_PROMPT_FIX`.
6. Rewrite the prompt (`run recommendation --from-insights ...`), apply the
   minimal edit by hand, commit it as bundle v2 with
   `update-configuration-bundle`.
7. Split traffic (`run ab-test`, config-bundle mode over the gateway), let the
   online evaluator score 28 requests, read the report (`view ab-test`).
8. Enforce the floor: `eval-gate.yml` fails the PR when the batch-evaluation
   mean drops below `quality-baseline.json`.

## 6. Verification

Assertions from `docs/05-capability-map.yaml`, each with its capture:

- All four evaluation modes executed — `evidence/50`, `51`, `54`, online events
  consumed by the A/B report in `evidence/72`.
- The recommendation cites an observed failure pattern — `evidence/67` names the
  insight cluster "Foreign Currency Ignored Despite Receipt Metadata" and lists
  the EUR/GBP traces.
- The A/B report reports a confidence interval and a p-value — `evidence/72`:
  CI [1.00, 3.00], p = 0.00043, isSignificant true (mean 2.0 → 4.0, n = 12/14).
- CI blocks a PR on regression — `evidence/81` (pass, exit 0) and `evidence/82`
  (raised floor, `::error::`, exit 1), with `evidence/80b` provenance for the
  local reproduction.
- Versioning and endpoints — `evidence/84` (runtime v5), `evidence/85` (prod
  endpoint pinned to v1), `evidence/69` (bundle v1 `f45629ba` → v2 `d4c45b72`).
- Independence — `evidence/86`/`93` (tag listing before and after teardown,
  only `UseCase=06` plus pre-existing UC05 entries) and `evidence/87`
  (stale-index ghosts proven deleted via 404s). The repository-level check passes.

## 7. Cleanup

```bash
agentcore remove all -y                   # empties agentcore/agentcore.json ...
agentcore deploy -y --target default      # ... and this reconciles the stack down
agentcore status                          # nothing from this use case should be listed
```

What survives on purpose: the CDK bootstrap stack and its asset bucket —
account-level, reused across this series. The tag index may list deleted
resources for a while; `agentcore status` is the source of truth, and
`evidence/87` shows how to prove a ghost entry is really gone.

## 8. What surprised me

Three things. First, `bedrock-agentcore` 1.25.0 stopped shipping the ADOT
distro, so a freshly deployed runtime emits zero spans until you add
`aws-opentelemetry-distro>=0.18.0` yourself — and new runtimes also default to
a unified trace destination, so you need
`UNIFIED_TRACES_DESTINATION_ENABLED=false` to land in the shared `aws/spans`
group the CLI reads. Second, the first version of the planted defect was too
soft: "every receipt amount is already in USD" lost to the tool result every
time, and the model converted anyway; the strong imperative "must never be
called" reproduced the failure on all six non-USD receipts. Third, the
optimizer's rewrite was clinically accurate as diagnosis but operationally
wrong as patch — it added an approval gate that would truncate a single-turn
audit — so the human applies the minimal edit and the article says so.

## 9. When not to use this

The A/B machinery assumes traffic you can split: on a single-user local agent
there is nothing to divide and the online evaluator just burns sampling budget.
The pass-fail guard evaluator is only as good as its instructions — write the
rule in terms of tool calls, not vibes, or it agrees with the agent. And a CI
gate on a batch mean is meaningful only once enough sessions accumulate in the
lookback window; on day one the floor is decoration.

## 10. Files

| Path | What it is | Written by |
|---|---|---|
| `agentcore/agentcore.json` | the contract: every resource this use case declares | you |
| `agentcore/aws-targets.json` | where deployments land | you |
| `app/aia_uc06/` | the agent code `codeLocation` points at | you |
| `agentcore/bundles/` | prompt v1 and v2, the two A/B variants | you |
| `agentcore/datasets/` | the six scripted audit scenarios | you |
| `quality-baseline.json` | the committed floor the CI gate enforces | you |
| `evidence/` | captures of the native commands that prove the capabilities | you |
| `tests/` | unit tests for the agent's own Python, offline | you |
| `raw/` | boto3 sidecar note; teaching only, never deployed | you |
| `agentcore/cdk/`, `agentcore/.llm-context/`, `agentcore/.cli/` | generated plumbing | the CLI |

## 11. Related official samples

Repository: <https://github.com/awslabs/agentcore-samples>

- `01-features/06-observe-evaluate-optimize-your-agent/01-observe/` — span and
  trace setup; compare their ADOT configuration notes with this use case's
  two-part fix.
- `01-features/06-observe-evaluate-optimize-your-agent/02-evaluate/` — the
  evaluation APIs; look for the same four modes (on-demand, batch, dataset,
  online) as separate notebooks.
- `01-features/06-observe-evaluate-optimize-your-agent/03-optimize/` — prompt
  optimization; note it also requires a numeric evaluator.

## 12. Try it yourself

```bash
cp -r usecases/06-quality-loop /tmp/uc06 && cd /tmp/uc06
agentcore deploy -y --target default
agentcore status
```

This use case is self-contained: copy the folder anywhere and it still runs, and
you do not need any other use case deployed first. The repository-level check
asserts exactly that, by reading the folder for any path that leaves it.
