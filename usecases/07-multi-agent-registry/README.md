# UC07 · Multi-Agent and Registry

Series: AgentCore in Action · Use case: 07 · Difficulty: D5 · Region: `us-east-1`

A contract review orchestrator (AG-UI protocol) calls two specialist agents
over A2A — a legal clause specialist and a compliance specialist — and the
organization publishes its agents and MCP servers to a central Agent
Registry. Everything in this folder deploys alone, from zero, with
`agentcore` and `aws` commands only.

## What you get at the end

- Four AgentCore runtimes in one project: `aia_uc07_orchestrator` (AGUI),
  `aia_uc07_legal` (A2A), `aia_uc07_compliance` (A2A), `aia_uc07_billing_mcp`
  (MCP).
- An A2A exchange you can watch: blocking review, a 75-second deep scan run
  as an async task past the synchronous read ceiling, and a mid-stream
  cancel (barge-in).
- Ten concurrent sessions that cannot see each other's state.
- A registry (`agent-registry` namespace) with two records; semantic search
  for "payment processing" finds the record named `billing`.
- The registry inside an AWS RAM resource share (the cross-account
  mechanism), and a capacity provider pinning the billing MCP server's
  compute to chosen EC2 instance types (`m7g.large`, `c7g.large`).

## Layout

- `app/aia_uc07/orchestrator.py` — AG-UI endpoint; deterministic router over
  the specialists (review / deep scan / barge-in / codeword)
- `app/aia_uc07/legal_agent.py` — clause specialist, served with `serve_a2a`
- `app/aia_uc07/compliance_agent.py` — risk screens and the 75s `deep_scan`
- `app/aia_uc07/billing_mcp.py` — FastMCP server: invoices, payments, refunds
- `app/aia_uc07/a2a_client.py` — discovery (ListAgentRuntimes, GetAgentCard)
  and SigV4-signed A2A JSON-RPC (send, stream, get, cancel)
- `app/aia_uc07/policies/orchestrator-policy.json` — the extra IAM the
  orchestrator's role needs, attached via `additionalPolicies`
- `agentcore/agentcore.json` — the four runtimes; `aws-targets.json` — the
  account/region target
- `tests/test_task_text.py` — unit test for the A2A client
- `evidence/` — captured output of every claim in the article

## Deploy

```bash
agentcore validate
agentcore deploy -y --target default
agentcore status
```

## Verify (native commands only)

The orchestrator speaks AG-UI: `agentcore invoke` prints its SSE stream raw, so
use the data-plane CLI with `--accept text/event-stream` instead. The payload
is one AG-UI RunAgentInput document:

```json
{
  "threadId": "uc07-demo", "runId": "r1",
  "messages": [{"id": "m1", "role": "user", "content": "review contract C-118"}],
  "tools": [], "context": [], "state": {}, "forwardedProps": {}
}
```

```bash
# A2A discovery
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
aws bedrock-agentcore get-agent-card --region us-east-1 --agent-runtime-arn <legal-arn>

# Orchestrator reaches both specialists over A2A (payload from above)
aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
  --agent-runtime-arn <orchestrator-arn> --qualifier DEFAULT \
  --runtime-session-id <33+ chars> \
  --content-type application/json --accept text/event-stream \
  --payload fileb:///tmp/uc07-agui-payload.json /tmp/uc07-agui-out.bin

# The same shape drives "deep scan C-118" (async, ~115s) and "barge in C-118".

# MCP server hosting
agentcore invoke --runtime aia_uc07_billing_mcp call-tool \
  --tool lookup_invoice --input '{"invoice_id":"INV-2041"}'

# Registry
aws agent-registry-control list-registries --region us-east-1
aws agent-registry search-discoverable-registry-records --region us-east-1 \
  --registry-id <id> --search-query "payment processing"
```

## Registry setup (aws CLI only)

The registry and the RAM share are control-plane resources the AgentCore CLI
does not model, so they are created with `aws` directly:

```bash
aws agent-registry-control create-registry --region us-east-1 \
  --name aia-uc07-catalog --description "Legal and compliance agents"

# one record per capability; the MCP descriptor is the minimal 2025-12-11 shape
aws agent-registry-control create-registry-record --region us-east-1 \
  --cli-input-json file:///tmp/record-billing.json
aws agent-registry-control submit-registry-record-for-approval --region us-east-1 \
  --registry-id <id> --record-id <record-id>
aws agent-registry-control update-registry-record-status --region us-east-1 \
  --cli-input-json file:///tmp/record-approve.json

aws ram create-resource-share --region us-east-1 \
  --name aia-uc07-registry-xacct \
  --resource-arns <registry-arn> \
  --tags key=Project,value=agentcore-in-action key=UseCase,value=07 key=AutoDelete,value=true
```

`/tmp/record-billing.json` holds `recordType: MCP` and one descriptor:
`{"mcpServer": {"data": "{\"name\":\"dev.xiongpin/billing\",\"description\":\"Billing and payment processing MCP server: invoice lookup, payment status, refunds\",\"version\":\"1.0.0\"}", "dataSchemaVersion": "2025-12-11"}}`.
Update calls use `optionalValue` wrappers, see `evidence/13-record-billing.txt`.

## Teardown

```bash
agentcore remove all -y
agentcore deploy -y --target default   # reconciles the stack down
agentcore status                       # nothing listed

# the registry lives outside the CLI contract; delete it directly
aws ram delete-resource-share --region us-east-1 --resource-share-arn <share-arn>
aws agent-registry-control delete-registry-record --region us-east-1 \
  --registry-id <id> --record-id <record-id>
aws agent-registry-control delete-registry --region us-east-1 --registry-id <id>
```

`remove all -y` empties `agentcore/agentcore.json` and
`agentcore/aws-targets.json`; restore both from git before deploying again.
The CDK bootstrap stack and its asset bucket survive on purpose: every later
deployment in the account reuses them.

## Independence

No import outside this folder, no cross-stack reference, no dependency on
uc01–uc06 ever having been deployed. Every resource is tagged
`Project=agentcore-in-action`, `UseCase=07`, `AutoDelete=true`. Prove with:

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,uc:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
```
