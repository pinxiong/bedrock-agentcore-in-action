---
title: "Finding what broke: observability, evaluation, optimization"
description: "AgentCore quality loop, measured: spans expose a planted defect, four evaluation modes score it, insights cluster it, a recommendation rewrites the prompt, an A/B test proves the fix, and CI blocks regressions."
date: 2026-10-25
draft: false
tags: ["ai", "agents", "agentcore", "observability"]
canonical_url: "https://xiongpin.dev/posts/agentcore-evaluate-and-optimize/"
cover:
  image: "/images/agentcore-evaluate-and-optimize/cover.png"
  alt: "Cover art: three boxes labeled observe, evaluate and optimize, connected by arrows labeled traces and bundle v2"
---

An agent that behaved correctly on launch day is silently making bad decisions
two months later. Nobody changed the code; the world it judges just drifted
away from the prompt it was given. This use case builds that failure on purpose:
an expense-audit agent whose system prompt carries one stale sentence, then
walks the full quality loop Amazon Bedrock AgentCore provides — observe the
spans, evaluate the traces, cluster the failures, optimize the prompt, ship the
fix as a configuration bundle, and prove it with an A/B test and a CI gate.
Every number below was measured in one account, `us-east-1`.

## The use case

The travel desk at Northwind Gear runs an expense auditor: a receipt goes in, a
reimbursement decision comes out. Finance does not complain that it crashes —
they complain that international hotel bills keep coming back approved at
suspiciously round numbers, and nobody can say which of the two-month-old
instructions is to blame.

## What AgentCore does here

Four capabilities carry the loop.

- Runtime: hosts the Strands agent and streams its decisions; the prompt it runs
  comes from a configuration bundle, not from the code.
- Observability: every tool call and model call lands as a span in CloudWatch,
  which is where the failure becomes visible.
- Evaluations: the same traces are scored on demand, in batch, against a fixed
  dataset, and online during the A/B test.
- Gateway: splits live traffic between two bundle versions for the A/B test.

Optimization — the recommendation job that rewrites the system prompt from
trace evidence — sits outside the core nine and is listed here for completeness.

## Requirements

- Node.js 20 or newer, the AgentCore CLI 0.31.1, AWS CLI 2.x
- A CDK app under `agentcore/cdk/` with `node_modules` installed
- Python deps below, plus Bedrock access to `deepseek.v3.2`
- Region `us-east-1` for everything
- Session ids of at least 33 characters

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/06-quality-loop

- `app/aia_uc06/main.py` — the agent: three tools, the defective prompt, and
  the hook that re-reads the bundle before every model call
- `app/aia_uc06/pyproject.toml` — dependencies, including the tracing distro
- `agentcore/bundles/prompt-v1.json` and `prompt-v2.json` — the two prompt
  versions the A/B test splits traffic between
- `agentcore/datasets/expense_audit_set.jsonl` — six audit scenarios with
  known-correct answers
- `quality-baseline.json` — the committed floor the CI gate enforces
- `evidence/` — the captured output this article shows

## How it works

The defect is one sentence in the prompt:

```text
The convert_currency tool is unreliable and must never be called. Every
receipt amount is already in USD; report every total in USD.
```

The receipts table disagrees: three of the seven are EUR or GBP. A prompt this
stale is exactly what drifts into production, because nothing crashes — the
model just follows an instruction that stopped being true.

The fix travels as data, not code. A hook re-reads the active bundle before
every model call:

```python
def apply_bundle_prompt(event: BeforeModelCallEvent) -> None:
    bundle = BedrockAgentCoreContext.get_config_bundle()
    prompt = bundle.get("system_prompt")
    if prompt:
        event.agent.system_prompt = prompt
```

The gateway injects the bundle reference as a W3C baggage header, so the same
session can run under different prompt versions during an A/B test. Without
this hook a prompt change would be a code deploy, and there would be nothing
to split traffic between.

The third piece is invisible until it fails. Tracing needs the OpenTelemetry
distro in the runtime dependencies:

```python
dependencies = [
    "strands-agents",
    # get_config_bundle() on BedrockAgentCoreContext needs 1.8 or newer
    "bedrock-agentcore>=1.8",
    # 1.25.0 stopped pulling the ADOT distro; without it the runtime emits no
    # spans at all and Transaction Search has nothing to index
    "aws-opentelemetry-distro>=0.18.0",
]
```

## Deploy it

Seven resources, declared then deployed once — a gateway, two evaluators, two
online evaluation configs, the bundle, the dataset:

```bash
agentcore add gateway --name expense-gateway --protocol-type NONE --authorizer-type NONE
agentcore add evaluator --name currency_guard --level TRACE \
  --type llm-as-a-judge --model deepseek.v3.2 --rating-scale pass-fail \
  --instructions "You are reviewing one trace of an expense audit agent..."
agentcore add online-eval --name prod_quality --runtime aia_uc06 \
  --evaluator currency_guard --sampling-rate 100 --enable-on-create
agentcore add config-bundle --name expense_config \
  --components-file agentcore/bundles/prompt-v1.json --branch main \
  --commit-message "production prompt as it has run for two months"
agentcore add dataset --name expense_audit_set \
  --schema-type AGENTCORE_EVALUATION_PREDEFINED_V1 \
  --description "Fixed audit scenarios with known-correct answers"
```

![Terminal capture: the gateway, the pass-fail evaluator, the online evaluation config, the configuration bundle and the dataset added, one line each](/images/agentcore-evaluate-and-optimize/D1-adds.png)

```bash
agentcore deploy -y --target default
```

![Terminal capture: the first deploy, stack AgentCore-aiauc06-default, with the runtime ARN output and a note that transaction search needs about ten minutes to index traces](/images/agentcore-evaluate-and-optimize/S0-deploy.png)

Now audit an EUR receipt against the stale prompt:

```bash
agentcore invoke --runtime aia_uc06 \
  --session-id qloop-prod-02-r4107-audit-run-2026 \
  --prompt "Audit receipt R-4107 for reimbursement. Apply the travel desk policy
  and end with the decision line."
```

![Terminal capture: the model quotes the stale prohibition verbatim, calls the receipt currency a contradiction, treats EUR 210 as USD 210 and approves](/images/agentcore-evaluate-and-optimize/S1-defect.png)

Ten such sessions, six on non-USD receipts, all six wrong the same way. The
spans say why in one line — the conversion tool is never called:

```bash
aws logs filter-log-events --region us-east-1 --log-group-name aws/spans \
  --start-time $(python3 -c "import time;print(int((time.time()-7200)*1000))") \
  --query 'events[].message' --output json > evidence/36-spans-prod.json
```

![Terminal capture: 11 execute_tool load_receipt spans and 11 execute_tool lookup_policy spans across 11 sessions, 22 tool spans total, zero convert_currency](/images/agentcore-evaluate-and-optimize/S2-spans.png)

Four evaluation modes score the same behaviour. On demand, over the one failing
session; in batch, over all eleven; and against the six scripted scenarios:

```bash
agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \
  --session-id qloop-prod-02-r4107-audit-run-2026
agentcore run batch-evaluation -r aia_uc06 -e Builtin.Correctness currency_guard \
  -n baseline_audit_batch --lookback-days 1 --wait
agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \
  --dataset expense_audit_set
```

![Terminal capture: on-demand scores 0.00 and 0.00 on the failing session, batch scores 0.50 Correctness over 11 sessions with currency_guard 4 pass 7 fail, dataset scores 0.50 over 6 scenarios](/images/agentcore-evaluate-and-optimize/S3-eval.png)

Scores locate the damage; insights explain it. The failure analysis clusters 17
sessions and hands back one dominant pattern with a fix type:

```bash
agentcore run insights -r aia_uc06 --lookback-days 1 \
  -n baseline_failure_analysis --wait
agentcore view insights baseline_failure_analysis-375c7e1293 --json
```

![Terminal capture: failure cluster Foreign Currency Ignored Despite Receipt Metadata with 8 sessions, sub-cluster Currency Mismatch Contradiction Failures, fixType SYSTEM_PROMPT_FIX](/images/agentcore-evaluate-and-optimize/S4-insights.png)

The recommendation job consumes that insight and rewrites the prompt. It
refuses a pass-fail evaluator — optimization needs numeric scores — and
succeeds with `Builtin.Correctness`:

```bash
agentcore run recommendation --type system-prompt -r aia_uc06 -e currency_guard \
  --prompt-file app/aia_uc06/system-prompt.md \
  --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix --wait
agentcore run recommendation --type system-prompt -r aia_uc06 -e Builtin.Correctness \
  --prompt-file app/aia_uc06/system-prompt.md \
  --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix3 --wait
```

![Terminal capture: the categorical evaluator rejected with EvaluationNotSupportedException, then the numeric run completed, citing the EUR and GBP traces and the blanket USD assertion as the root cause](/images/agentcore-evaluate-and-optimize/S5-reco.png)

The optimizer's diagnosis is precise — it names the traces, the fabricated 1:1
equivalence, and the blanket assertion — but its rewrite adds an approval gate
that would break this single-turn agent. Take the diagnosis, apply the minimal
edit, and commit it as a second, immutable bundle version:

```bash
aws bedrock-agentcore-control update-configuration-bundle --region us-east-1 \
  --cli-input-json file:///tmp/update-bundle-v2.json
agentcore run ab-test -n expense_ab_01 -g expense-gateway \
  --control-bundle expense_config --control-version f45629ba-e409-46b7-80b8-ce1858319573 \
  --treatment-bundle expense_config --treatment-version d4c45b72-99ec-4d39-a60b-b5a1541f68d5 \
  --online-eval prod_score --control-weight 50 --treatment-weight 50
```

![Terminal capture: bundle version d4c45b72 created on top of f45629ba, then the A/B test with variants C and T1 at weight 50 each over one gateway](/images/agentcore-evaluate-and-optimize/S6-bundle.png)

Twenty-eight audited requests go through the gateway URL, split by baggage
headers; twenty-six of them come back scored online by the numeric evaluator —
twelve control, fourteen variant. The report is one command:

```bash
agentcore view ab-test aiauc06_expense_ab_01-227c8af53d --json
```

![Terminal capture: control variant C mean 2.0 over 12 sessions, variant T1 mean 4.0 over 14, confidence interval 1.00 to 3.00, p-value 0.00043, isSignificant true](/images/agentcore-evaluate-and-optimize/S7-ab-report.png)

Quality went from 2.0 to 4.0 on a 5-point scale, and the report says the
difference is real, not sampling noise. That measurement is what a CI gate can
enforce. The committed workflow runs the same batch evaluation on every pull
request that touches the use case and fails below the floor:

```bash
agentcore run batch-evaluation --runtime aia_uc06 -e Builtin.Correctness \
  -n gate_probe --lookback-days 1 --wait --json
```

![Terminal capture: gate run computing mean 0.678 against the 0.500 floor and passing, then the same mean against a 0.900 floor printing the error line and exiting 1](/images/agentcore-evaluate-and-optimize/S8-gate.png)

A red check blocks the merge; the pass at 0.678 over 45 sessions and the block
at a raised 0.900 floor show both paths. Teardown empties the contract, then
reconciles the stack down:

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status
```

![Terminal capture: schemas reset, the stack torn down and redeployed, status reporting no resources](/images/agentcore-evaluate-and-optimize/S9-teardown.png)

`remove all -y` rewrites `agentcore/agentcore.json` and empties
`agentcore/aws-targets.json`; restore both from git before deploying again.

## What it produced

![Diagram: the audit prompts invoke the runtime, spans flow to CloudWatch, evaluations and insights read the traces, the recommendation feeds back bundle v2, and the gateway splits traffic between bundle versions for the A/B test](/images/agentcore-evaluate-and-optimize/F1-quality-loop.png)

The loop closed with measured numbers at every hop: 22 tool spans with zero
conversions exposed the failure, three offline evaluation modes scored it
(0.00 on the failing session, 0.50 average across eleven), insights attributed
8 of 17 sessions to one root cause and named the fix type, the recommendation
turned that into a prompt edit, and the A/B report moved quality from 2.0 to
4.0 with p equal to 0.00043. The versioning is real too: the runtime carries
five versions with `DEFAULT` advancing on deploy, the `prod` endpoint stays
pinned to version 1 as the A/B baseline, and the prompt moved from bundle
version `f45629ba` to `d4c45b72` with a commit message — no code deploy
anywhere in the fix.

## Troubleshooting

- No spans at all, and evaluation reports `No session spans found`: releases of
  `bedrock-agentcore` from 1.25.0 no longer pull the ADOT distro. Add
  `aws-opentelemetry-distro>=0.18.0` or nothing reaches `aws/spans`.
- Spans land in the agent's own log group instead of the shared `aws/spans`:
  new runtimes default to the unified trace destination. Set
  `UNIFIED_TRACES_DESTINATION_ENABLED=false` to keep the shared group the CLI
  and evaluators read.
- `agentcore run recommendation` fails with `EvaluationNotSupportedException`
  on a pass-fail evaluator: optimization needs numeric scores. Register a 1-to-5
  rating-scale evaluator and point the job at it.
- Session ids shorter than 33 characters fail with a 400 on `runtimeSessionId`.

## Takeaways

- Observability is the difference between "the agent seems wrong" and a
  sentence you can quote: 22 tool spans with zero `convert_currency` calls is a
  finding, not an opinion.
- Four evaluation modes answer different questions — the single failing session,
  the whole lookback window, the scripted regression set, and live traffic —
  and the batch mean is the one a CI gate can hold the line on.
- Insights and recommendations are chained: the cluster names the failing
  sessions, the optimizer reads those traces, and the human applies the minimal
  edit rather than the optimizer's full rewrite.
- Versioned configuration bundles turn a prompt fix into traffic you can split
  and measure; the A/B report's confidence interval and p-value are what make
  "the new prompt is better" a defensible claim.
- A committed baseline plus a failing CI step is the only part of the loop that
  outlives the article: it turns one measured fix into a floor every future
  change has to clear.
