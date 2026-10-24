---
title: "Stopping an Agent From Overreaching: Policy in Enforce Mode"
description: "AgentCore Policy, measured: a CNY 3000 refund logged DENY three times and executed anyway in LOG_ONLY, blocked at the gateway in 47 ms in ENFORCE, and blocked again with no agent in the loop, while CNY 200 passed untouched."
date: 2026-10-24
draft: false
tags: ["ai", "agents", "agentcore", "security"]
canonical_url: "https://xiongpin.dev/posts/agentcore-policy-enforce-mode/"
cover:
  image: "/images/agentcore-policy-enforce-mode/cover.png"
  alt: "Cover art: one gateway, two Cedar policies, a CNY 3000 call stopped at the gate while CNY 200 passes through"
---

A refund assistant whose only rule is a sentence in its prompt will issue a CNY 3000 refund the moment a customer insists: the sentence is a suggestion, not a gate. This article replaces the sentence with a Cedar policy on an AgentCore Gateway and proves it three ways: the same CNY 3000 call runs anyway while the policy engine writes DENY beside it, one mode switch kills it at the gateway with a 47-millisecond decision, and it stays dead when called directly, no agent in the loop. CNY 200 passes every gate untouched, no code changed between verdicts. Every number was measured in one account, `us-east-1`.

## The use case

A customer asks Meridian Supply's refund assistant to refund order SO-2214 for CNY 3000, and the business rule says refunds stop at CNY 500. The prompt asks it to confirm the amount, and it does: the customer confirms CNY 3000, the assistant calls processRefund, the refund is issued. The baseline measured exactly that: CNY 200 returned `RF-2772878660`, CNY 3000 returned `RF-2772903637`. Nothing malfunctioned — the rule did not exist anywhere the system could check it. This use case moves the ceiling out of the prompt and onto the path every tool call already takes: the gateway.

## What AgentCore does here

Three of the nine capabilities carry this use case.

- Policy: one engine, two Cedar policies, each generated from one natural-language sentence. The engine attaches to the gateway; the attach mode decides whether a DENY is a log line or a wall.
- Gateway: an MCP endpoint in front of one Lambda target. Every tools/call is authorized before the backend runs, so the agent cannot argue its way past the rule.
- Observability, lightly: each evaluation lands in a CloudWatch decision log and counts into DenyDecisions and AllowDecisions metrics.

The other six stay off: no Memory, no Knowledge Bases, no Evaluations, no Code Interpreter, no Browser, and no Identity beyond the execution roles the CLI writes.

## Requirements

- Node.js 20 or newer, the AgentCore CLI 0.31.1, AWS CLI 2.x, uv 0.11.9
- Python 3.13 for the backend function and the runtime target
- An AWS account with Bedrock model access; `MODEL_ID` set to `deepseek.v3.2`
- IAM permissions for Lambda and the AgentCore policy-engine APIs
- Region `us-east-1` for everything

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/04-policy

- `agentcore/agentcore.json` — the contract: runtime, gateway, engine, two policies
- `agentcore/gateway/refund-tools.json` — the two tool schemas
- `app/aia_uc04/main.py` — the agent: prompt, MCP client, streaming entrypoint; no line knows the ceiling
- `app/aia_uc04/mcp_client/client.py` — the HTTP client for `GATEWAY_MCP_URL`
- `infra/refund_api.py` — the backend: one Lambda, both tools

The embedded `agentcore/cdk/` baseline is a deliberate copy: the directory stands alone.

## How it works

Each policy is one sentence at the CLI, which becomes a Cedar statement in the contract:

```cedar
permit (principal, action == AgentCore::Action::"refund___processRefund",
  resource == AgentCore::Gateway::"...") when { context.input.amount <= 500 };
```

The ceiling never mentions CNY 3000. It permits calls at or under 500 and stops; any request no policy matches falls through to default deny, which is what the deny reason says verbatim: No policy applies to the request. That is why a second policy exists: approvalAlways permits approveRefund whenever orderId is a non-empty string, so the recording tool survives the same fall-through that stops the refund.

The mode is one field of the gateway's engine attachment:

```json
"policyEngineConfiguration": {
  "policyEngineName": "refundPolicyEngine",
  "mode": "LOG_ONLY"
}
```

LOG_ONLY evaluates and records; ENFORCE evaluates and blocks. Flipping that field and deploying is the entire ceremony. Decisions cost 44 to 56 milliseconds. The backend stays worth guarding: the gateway addresses the tool as `refund___processRefund`, the Lambda echoes a refund id, so a success is visibly the real backend.

## Deploy it

The backend first, so the gateway has something to guard:

```bash
aws iam create-role --role-name aia-uc04-lambda \
  --assume-role-policy-document '{"Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --region us-east-1
aws iam attach-role-policy --role-name aia-uc04-lambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region us-east-1
zip -j /tmp/aia-uc04-refund.zip infra/refund_api.py
aws lambda create-function --function-name aia-uc04-refund \
  --runtime python3.13 --handler refund_api.lambda_handler \
  --zip-file fileb:///tmp/aia-uc04-refund.zip \
  --role arn:aws:iam::123456789012:role/aia-uc04-lambda --region us-east-1
```

![Terminal capture: the role created with its Arn, the policy attached, create-function answering State Pending, and the direct invoke echo](/images/agentcore-policy-enforce-mode/D1-backend-setup.png)

The backend works before any policy exists. Then the gateway, deliberately minimal: one target, two tools, no authorizer.

```bash
agentcore add gateway --name refund-gateway --protocol-type MCP --authorizer-type NONE
agentcore add gateway-target --name refund --gateway refund-gateway \
  --type lambda-function-arn --lambda-arn arn:aws:lambda:us-east-1:123456789012:function:aia-uc04-refund \
  --tool-schema-file agentcore/gateway/refund-tools.json
```

![Terminal capture: each add answers one line, Added gateway refund-gateway and Added gateway target refund](/images/agentcore-policy-enforce-mode/D2-gateway-adds.png)

Deploy:

```bash
agentcore deploy -y --target default
```

![Terminal capture: the first deploy, 3 minutes 8 seconds, one stack with runtime, gateway and target](/images/agentcore-policy-enforce-mode/S1-deploy.png)

3 minutes 8 seconds, one stack: AgentCore-aiauc04-default, runtime and gateway.

```bash
agentcore status
```

![Terminal capture: one runtime READY, one gateway with one target](/images/agentcore-policy-enforce-mode/S2-status.png)

Runtime READY, gateway deployed, one target. The gateway URL goes into `GATEWAY_MCP_URL`; one more deploy wires the agent to it. The baseline, no policy attached anywhere:

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."
```

![Terminal capture: CNY 200 with no policy, refund RF-2772878660 issued](/images/agentcore-policy-enforce-mode/S3-baseline-200.png)

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
```

![Terminal capture: CNY 3000 with no policy, refund RF-2772903637 issued](/images/agentcore-policy-enforce-mode/S4-baseline-3000.png)

Both returned refund ids: the rule was a sentence that held nothing.

Now the policy: three adds, engine online first, the ceiling on the next deploy:

```bash
agentcore add policy-engine --name refundPolicyEngine \
  --description "Refund ceiling for the refund gateway" \
  --attach-to-gateways refund-gateway --attach-mode LOG_ONLY --json
agentcore add policy --name refundCeiling --engine refundPolicyEngine \
  --description "Refunds are permitted up to CNY 500; anything above falls through to default deny" \
  -g "permit a processRefund tool call only when its amount argument is less than or equal to 500" \
  --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json
agentcore add policy --name approvalAlways --engine refundPolicyEngine \
  --description "Recording an approval is allowed whenever the order id is present" \
  -g "permit an approveRefund tool call only when its orderId argument is a non-empty string" \
  --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json
```

![Terminal capture: the engine and both policies added from natural language](/images/agentcore-policy-enforce-mode/S5-policy-add.png)

The same CNY 3000 request, under LOG_ONLY:

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
```

![Terminal capture: CNY 3000 under LOG_ONLY, refund RF-2774152577 issued anyway](/images/agentcore-policy-enforce-mode/S6-logonly-3000.png)

Executed — `RF-2774152577` — while the engine wrote DENY beside it. The decision log is one query away:

```bash
aws logs filter-log-events --region us-east-1 \
  --log-group-name /aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/aiauc04-refund-gateway-vxib2yw9yr \
  --filter-pattern "Policy evaluation" \
  --start-time 1792773900000 --end-time 1792774740000 \
  --output json --query 'events[].message' \
  | jq -r '.[] | fromjson | [(.event_timestamp/1000 | strftime("%H:%M:%S")), .body.log, .body.id, .body.policy.decision, ((.body.policy.determiningPolicies // []) | if length == 0 then "-" else join(",") end), "\(.body.policy.latencyMs)ms"] | join(" | ")'
```

![Terminal capture: the decision log, both modes, the deciding policy named on every ALLOW](/images/agentcore-policy-enforce-mode/S7-decision-log.png)

Four LOG_ONLY evaluations: three DENY, the 3000 refund among them; one ALLOW naming refundCeiling-hrk1reemhq, the CNY 200 call that also passed, `RF-2774224546`. One of the denials was approveRefund: only refundCeiling was live under LOG_ONLY. approvalAlways went live with the ENFORCE switch — without it, default deny would take the recording tool down too. The switch: mode to ENFORCE in agentcore.json, deploy once more, 1 minute 24 seconds, and repeat the pair.

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
```

![Terminal capture: CNY 3000 under ENFORCE, the approval records, the refund does not run](/images/agentcore-policy-enforce-mode/S8-enforce-3000.png)

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."
```

![Terminal capture: CNY 200 under ENFORCE, refund RF-2774662593 issued](/images/agentcore-policy-enforce-mode/S9-enforce-200.png)

The 3000 agent recorded the approval — approvalAlways allowed it — then reported honestly that the policy engine blocked the refund. The 200 came back `RF-2774662593`. No code changed between these runs; the ceiling moved, not the tool.

With no agent in the loop, the gateway answers identically:

```bash
curl -s -X POST "$GATEWAY_URL" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"refund___processRefund","arguments":{"orderId":"SO-2214","amount":3000}}}'
```

![Terminal capture: direct MCP calls, 3000 denied with error -32002, 200 refunded](/images/agentcore-policy-enforce-mode/S10-direct-mcp.png)

CNY 3000 died with JSON-RPC error -32002, Tool Execution Denied; the identical call at CNY 200 returned `RF-2774812797`. The policy sits on the path, not the agent. The counts, from CloudWatch — the queries file ships in the repo's use case folder and selects DenyDecisions and AllowDecisions on the PolicyEngine and Mode dimensions:

```bash
aws cloudwatch get-metric-data --region us-east-1 \
  --start-time 2026-10-23T16:40:00Z --end-time 2026-10-23T16:59:00Z \
  --metric-data-queries file://policy-decision-queries.json --output text \
  --query 'MetricDataResults[].[Id, Values]'
```

![Terminal capture: the four metric results, LOG_ONLY 3 deny 1 allow, ENFORCE 1 deny 3 allow](/images/agentcore-policy-enforce-mode/S11-metrics.png)

Same engine, same policies: LOG_ONLY recorded 3 denials and blocked nothing; ENFORCE recorded 1 denial and blocked it.

Teardown is two stages; only both leave the account clean. Agentcore's: `agentcore remove all -y` resets the contract — the resource arrays in `agentcore/agentcore.json` empty — then `agentcore deploy -y --target default` reconciles the stack to nothing and rewrites `agentcore/aws-targets.json`; restore both from git. Yours: the Lambda, its role, and the decision log group sit outside the stack, so aws deletes them. After both, `agentcore status` reports no resources. The CDK bootstrap survives on purpose: account-level, one-time, reused across this series.

## What it produced

![Diagram: the policy engine attached to the gateway, every tools/call authorized before the Lambda runs](/images/agentcore-policy-enforce-mode/F1-policy-architecture.png)

Six refunds were issued across the session, one stopped: `RF-2772903637` and `RF-2774152577` prove the ceiling was first absent, then ignored; `RF-2774662593` and `RF-2774812797` prove CNY 200 kept passing after ENFORCE, through the agent and around it. The 3000 call died both ways: a denied tool call the agent had to report, and error -32002 on the direct wire. Every ALLOW in the log names the policy that made it. A tag listing showed six resources, all UseCase=04, nothing else.

## Troubleshooting

- The first deploy died in CDK synth, subprocess exit 1: uv could not reach the PyPI wheel source. Point `UV_DEFAULT_INDEX` at a mirror and deploy again; the second attempt is the figure above.
- The first baseline invoke returned ValidationException, Access to Anthropic models is not allowed: model/load.py fell back to a Claude default because `MODEL_ID` was unset. Set it to `deepseek.v3.2` and redeploy.
- An early forbid-only draft of refundCeiling was rejected at deploy as Overly Restrictive — its removal sits in the evidence; an unconditional permit is rejected as Overly Permissive. Conditional permit plus default deny is the accepted shape.

## Takeaways

- A prompt rule is a suggestion the model reads; a Cedar policy on the gateway is a gate the call cannot walk around, because it decides before the backend exists.
- Default deny is the load-bearing half: the ceiling permits at or under 500, the fall-through forbids everything else. Write permits, let the default refuse.
- LOG_ONLY is staging with receipts: three denials recorded, nothing blocked, one field to flip when the numbers look right.
- Permit every tool the flow needs, or ENFORCE takes down the whole conversation, not just the refund.
- The audit trail is free: every ALLOW names its policy, in the log and in the metrics.
