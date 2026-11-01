---
title: "Two specialists, one orchestrator, one catalog"
description: "A contract-review orchestrator fans out to two A2A specialists, a billing MCP server runs on pinned EC2 instance types, and the Agent Registry plus RAM make the whole fleet discoverable and shareable. Measured end to end."
date: 2026-11-01
draft: false
tags: ["ai", "agents", "agentcore", "mcp"]
canonical_url: "https://xiongpin.dev/posts/agentcore-a2a-multi-agent-registry/"
cover:
  image: "/images/agentcore-a2a-multi-agent-registry/cover.png"
  alt: "Cover art: one orchestrator box pointing at a legal-and-compliance box and a billing MCP box"
---

Four protocols walk into one project. An orchestrator that speaks AG-UI streams
its answers as server-sent events, two specialists answer A2A tasks — one of
them for 115 seconds past any synchronous read timeout — and a billing tool
server answers MCP calls on EC2 instance types I chose myself. On top of the
fleet sits a catalog: the Agent Registry, shared across accounts through RAM,
whose semantic search finds the record named billing when asked for payment
processing. Every number below was measured in one account, `us-east-1`.

## The use case

Northwind Gear's legal desk reviews supplier contracts. Two jobs keep the
lawyers busy: a clause-by-clause read against the house wording, and a
compliance screen that escalates anything policy-breaking. A contract-review
orchestrator receives the brief and farms each job out to a specialist agent,
because the two teams refuse to share a prompt, a model version, or a release
schedule. Finance, meanwhile, wants one place where every agent and every MCP
server the company runs is registered and findable — including from the shared
services account — without asking engineering for a spreadsheet.

## What AgentCore does here

- Runtime hosts four agents, one per protocol: AG-UI for the orchestrator, A2A
  for the legal and compliance specialists, MCP for the billing tool server.
- A2A protocol carries the specialist traffic: blocking `message/send` for the
  quick review, non-blocking accept plus polling for the long scan, and
  `message/stream` with `tasks/cancel` for barge-in.
- AG-UI protocol is what the caller sees: the orchestrator streams RunStarted,
  text chunks and RunFinished as SSE.
- MCP server hosting runs a FastMCP server as a runtime, so tools/call is a
  managed, authenticated invocation like any other.
- Long-running async: the deep scan accepts at 0.0 seconds and completes at
  115.0 seconds, while a blocking request for the same work dies in the
  client's own read timeout at 184.9 seconds.
- Session isolation: ten sessions on one runtime each get their own microVM;
  ten codewords stored and recalled with zero cross-talk.
- Custom EC2 instance types: a capacity provider pins the billing server to
  `m7g.large` and `c7g.large` instances instead of the serverless default.
- Registry plus RAM: the catalog holds two records, search resolves natural
  language to records, and the registry itself is a RAM-shareable resource.

## Requirements

- Node.js 20 or newer, the AgentCore CLI 0.31.1, AWS CLI 2.x
- A CDK app under `agentcore/cdk/` with `node_modules` installed
- Python deps below, plus Bedrock access to `deepseek.v3.2`
- Region `us-east-1` for everything; a default VPC for the capacity provider
- Session ids of at least 33 characters

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/07-multi-agent-registry

- `app/aia_uc07/orchestrator.py` — the AG-UI endpoint and a deterministic
  router: no model, just intents, so the protocol layer is what gets measured
- `app/aia_uc07/legal_agent.py` and `compliance_agent.py` — the specialists,
  each wrapped in `StrandsA2AExecutor` and served with `serve_a2a` on port 9000
- `app/aia_uc07/billing_mcp.py` — a FastMCP server with three tools and no model
- `app/aia_uc07/a2a_client.py` — discovery (`ListAgentRuntimes`,
  `GetAgentCard`) and SigV4-signed A2A JSON-RPC: send, stream, get, cancel
- `app/aia_uc07/policies/orchestrator-policy.json` — the extra IAM the
  orchestrator needs, attached through `additionalPolicies` in the contract
- `agentcore/agentcore.json` — four runtimes plus the capacity provider
- `evidence/` — the captured output this article shows

## How it works

The orchestrator is the front door. It speaks AG-UI, so a caller posts one
RunAgentInput and receives SSE events back:

```json
{
  "threadId": "uc07-demo",
  "runId": "r1",
  "messages": [{"id": "m1", "role": "user", "content": "review contract C-118"}],
  "tools": [],
  "context": [],
  "state": {},
  "forwardedProps": {}
}
```

Inside, the router has no model — the point of the use case is the wiring, so
intents map straight to A2A calls. It discovers the specialists at runtime
with `ListAgentRuntimes`, matching on the suffix of each deployed name,
because the deploy stamps the project prefix in front of every runtime
(`aiauc07_aia_uc07_legal`), then fetches each agent card with `GetAgentCard`
before sending. One IAM line makes this legal: the orchestrator's role allows
`bedrock-agentcore:ListAgentRuntimes` and `bedrock-agentcore:GetAgentCard`.

The list and the card are the discovery contract:

```bash
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
```

![Terminal capture: the control plane lists the four aiauc07 runtimes with their ids and READY status, plus a note about two pre-existing runtimes that predate the series](/images/agentcore-a2a-multi-agent-registry/S2-runtimes.png)

```bash
aws bedrock-agentcore get-agent-card --region us-east-1 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc07_aia_uc07_legal-C8yDVkGWBW
```

![Terminal capture: the legal agent card with name aia_uc07_legal, protocolVersion 0.3.0, preferredTransport JSONRPC, streaming true, and one skill named Clause review](/images/agentcore-a2a-multi-agent-registry/S3-agent-card.png)

The A2A wire then forks by shape of work. The review is two blocking
`message/send` calls; each returns a completed task with the specialist's
answer. The deep scan is a five-pass, 75-second job, so it is dispatched with
`blocking: false` — the server answers immediately with a submitted task, and
the orchestrator polls `tasks/get` until the state flips. Barge-in is
`message/stream` for live status updates plus one `tasks/cancel` the moment
the first update arrives; the Strands executor cooperates and the stream
closes in state canceled.

Sessions are cheap isolation. The session id travels in the
`X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header, every distinct id gets
its own microVM, and state lives in a plain in-process dict — so ten
sessions storing and recalling ten codewords is a direct test of the
boundary.

The billing server is MCP: FastMCP, streamable-http, three tools, no model.
It is also the one runtime pinned to customer-managed compute. A capacity
provider declares an ARM64 pool of `m7g.large` and `c7g.large` with a
300-second idle timeout, and the runtime references it at creation. The
combination is what makes custom EC2 instance types a contract property, not
a console setting.

The registry is control-plane only. Records carry descriptors — the MCP
server's descriptor is a minimal document against schema `2025-12-11` — and a
record walks CREATING to DRAFT to PENDING_APPROVAL to APPROVED before search
will return it. Search is semantic: the query payment processing shares no
noun with the record name billing, yet billing is the first hit. RAM then
shares the registry itself, because `agent-registry:Registry` is a
RAM-shareable resource type.

## Deploy it

One contract, one deploy. The stack carries all four runtimes and the
capacity provider:

```bash
agentcore deploy -y --target default
```

![Terminal capture: the deploy validating, synthesizing CloudFormation, deploying and reporting the capacity provider id aiauc07_aia_uc07_pool-RAGFd2QHPH and the runtime outputs, ending with the stack name](/images/agentcore-a2a-multi-agent-registry/S0-deploy.png)

```bash
agentcore status
```

![Terminal capture: status reporting all four runtimes deployed and READY](/images/agentcore-a2a-multi-agent-registry/S1-status.png)

The review is the assertion that matters most — one request, two specialists,
two completed A2A tasks. The orchestrator resolves both ARNs by discovery,
fetches the card, and the legal and compliance specialists each finish their
task:

```bash
aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc07_aia_uc07_orchestrator-35KsYa22sv \
  --qualifier DEFAULT --runtime-session-id uc07-review-46702a95300245bda08060b2f73d4cda \
  --content-type application/json --accept text/event-stream \
  --payload fileb:///tmp/uc07-agui-payload.json /tmp/uc07-agui-out.bin
```

![Terminal capture: elapsed 95.0 seconds, discovery resolving both specialist ARNs, the legal task and the compliance task each reaching completed](/images/agentcore-a2a-multi-agent-registry/S4-review.png)

Now the long scan, dispatched non-blocking. The accept is instant; the work
runs for 115 seconds — past every synchronous ceiling — and completes with a
full report:

```bash
aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc07_aia_uc07_orchestrator-35KsYa22sv \
  --qualifier DEFAULT --runtime-session-id uc07-deepscan-<uuid> \
  --content-type application/json --accept text/event-stream \
  --payload fileb:///tmp/uc07-agui-payload.json /tmp/uc07-agui-out.bin
```

![Terminal capture: task accepted non-blocking at 0.0 seconds in state submitted, polled through working, completed at 115.0 seconds past the 60s synchronous ceiling, with the five-line escalation report](/images/agentcore-a2a-multi-agent-registry/S5-deep-scan.png)

Ask for the same scan with a blocking send and a short client timeout, and
the failure is the client's, not the server's: three SDK retry windows, then
a read timeout on the endpoint URL.

```bash
aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc07_aia_uc07_compliance-dc8CMTCDwj \
  --qualifier DEFAULT --runtime-session-id uc07-timeout-<uuid> \
  --content-type application/json --accept application/json \
  --cli-read-timeout 60 --payload fileb:///tmp/uc07-a2a-payload.json /tmp/uc07-a2a-out.bin
```

![Terminal capture: elapsed 184.9 seconds with a 60-second read timeout and 93.1 seconds with a 30-second read timeout, each ending in a ReadTimeoutError](/images/agentcore-a2a-multi-agent-registry/S6-sync-timeout.png)

Streaming is where barge-in lives. The cancel lands on the running task and
the stream closes eleven seconds in:

```bash
aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc07_aia_uc07_orchestrator-35KsYa22sv \
  --qualifier DEFAULT --runtime-session-id uc07-bargein-<uuid> \
  --content-type application/json --accept text/event-stream \
  --payload fileb:///tmp/uc07-agui-payload.json /tmp/uc07-agui-out.bin
```

![Terminal capture: stream opened in state submitted, status update in working at 11.9 seconds, tasks/cancel sent, cancel acknowledged and stream closed in state canceled at 12.1 seconds](/images/agentcore-a2a-multi-agent-registry/S7-barge-in.png)

Isolation is a loop, not a claim. Ten sessions, each storing one codeword and
recalling it on the same session id, twenty invocations in 88.3 seconds:

```bash
for i in 1..10; do
  aws bedrock-agentcore invoke-agent-runtime --region us-east-1 \
    --agent-runtime-arn <orchestrator-arn> --qualifier DEFAULT \
    --runtime-session-id uc07-iso-$i-<uuid> \
    --content-type application/json --accept text/event-stream \
    --payload fileb:///tmp/uc07-iso-payload.json /tmp/uc07-iso-out.bin
done
```

![Terminal capture: session 01 recalling kestrel, session 10 recalling violet, ten of ten sessions recalling their own codeword in 88.3 seconds](/images/agentcore-a2a-multi-agent-registry/S8-sessions.png)

The billing server answers tools, not prompts:

```bash
agentcore invoke --runtime aia_uc07_billing_mcp call-tool \
  --tool lookup_invoice --input '{"invoice_id":"INV-2041"}'
```

![Terminal capture: the invoice lookup returning customer Northwind Gear, amount 12800 dollars, status open, in 72.5 seconds on a freshly redeployed runtime](/images/agentcore-a2a-multi-agent-registry/S9-mcp.png)

That same runtime is the one riding the capacity provider. The describe
calls show both halves of the wiring:

```bash
aws bedrock-agentcore-control get-capacity-provider --region us-east-1 \
  --capacity-provider-id aiauc07_aia_uc07_pool-RAGFd2QHPH
aws bedrock-agentcore-control get-agent-runtime --region us-east-1 \
  --agent-runtime-id aiauc07_aia_uc07_billing_mcp-eAE3MP21yf
```

![Terminal capture: the capacity provider READY on LINUX_ARM64 with m7g.large and c7g.large and a 300-second idle timeout, and the runtime's capacityProviderConfiguration pointing back at the pool ARN](/images/agentcore-a2a-multi-agent-registry/S10-capacity-provider.png)

The stack does not create the catalog. The registry, its records and the RAM
share are control-plane resources the CLI contract does not model, so they
are created with the AWS CLI: the registry first, then one record per
capability. The MCP record's descriptor is the minimal `2025-12-11` document
and the agent record carries the full A2A card:

```bash
aws agent-registry-control create-registry --region us-east-1 \
  --name aia-uc07-catalog \
  --description "Legal and compliance workflow-automation agents: contract review orchestrator, specialists and the billing MCP server" \
  --discovery-configuration authorizerType=AWS_IAM \
  --tags Project=agentcore-in-action,UseCase=07,AutoDelete=true
aws agent-registry-control create-registry-record --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --name billing --display-name "Billing MCP server" \
  --description "Invoice lookup, payment processing and refund policy tools for agents, hosted on AgentCore Runtime as a streamable-http MCP server" \
  --record-type MCP \
  --descriptors '{"mcpServer":{"data":"{\"name\": \"dev.xiongpin/billing\", \"description\": \"Billing and payment processing MCP server: invoice lookup, payment status, refunds\", \"version\": \"1.0.0\"}","dataSchemaVersion":"2025-12-11"}}' \
  --tags Project=agentcore-in-action,UseCase=07,AutoDelete=true
aws agent-registry-control create-registry-record --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --name contract-clause-legal-specialist --display-name "Legal clause specialist (A2A)" \
  --description "A2A agent that reviews contract clauses against the legal reference clause library: liability, termination, payment, confidentiality and subcontracting" \
  --record-type AGENT \
  --descriptors '{"a2aAgentCard":{"data":"{\"capabilities\": {\"streaming\": true}, \"defaultInputModes\": [\"text\"], \"defaultOutputModes\": [\"text\"], \"description\": \"Contract clause specialist: compares clauses against the reference library\", \"name\": \"aia_uc07_legal\", \"preferredTransport\": \"JSONRPC\", \"protocolVersion\": \"0.3.0\", \"skills\": [{\"description\": \"Compare contract clauses against the reference clause library\", \"examples\": [\"Review the liability and termination clauses of this brief\"], \"id\": \"clause-review\", \"name\": \"Clause review\", \"tags\": [\"legal\", \"contract\", \"clause\"]}], \"url\": \"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Faiauc07_aia_uc07_legal-C8yDVkGWBW/invocations\", \"version\": \"1.0.0\"}","dataSchemaVersion":"0.3"}}' \
  --tags Project=agentcore-in-action,UseCase=07,AutoDelete=true
```

![Terminal capture: the registry ARN returned, then the billing record and the legal record each created in status CREATING](/images/agentcore-a2a-multi-agent-registry/S17-catalog-create.png)

A record is not discoverable the moment it exists: it is created DRAFT,
submitted for approval, and only then approved — a direct DRAFT to APPROVED
call is rejected as an invalid status transition. The curation workflow, in
the order the API accepts it:

```bash
aws agent-registry-control submit-registry-record-for-approval --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id 5nMCxyY06tFl
aws agent-registry-control submit-registry-record-for-approval --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id YRLG41zg45lV
aws agent-registry-control update-registry-record-status --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id 5nMCxyY06tFl --status APPROVED \
  --status-reason "Series run: article evidence"
aws agent-registry-control update-registry-record-status --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id YRLG41zg45lV --status APPROVED \
  --status-reason "Series run: article evidence"
```

![Terminal capture: both records moving to PENDING_APPROVAL, then to APPROVED with the status reason attached](/images/agentcore-a2a-multi-agent-registry/S18-catalog-approve.png)

The registry itself is a RAM-shareable resource, so sharing it is one call
with the registry's ARN as the payload:

```bash
aws ram create-resource-share --region us-east-1 \
  --name aia-uc07-registry-xacct \
  --resource-arns arn:aws:agent-registry:us-east-1:123456789012:registry/niFvetsCk7ujKrAO \
  --allow-external-principals \
  --tags key=Project,value=agentcore-in-action key=UseCase,value=07 key=AutoDelete,value=true
```

![Terminal capture: the resource share created ACTIVE with external principals allowed and the three series tags attached](/images/agentcore-a2a-multi-agent-registry/S19-ram-create.png)

The catalog is one registry with two records. Note the namespace — it is
`agent-registry`, not `bedrock-agentcore`:

```bash
aws agent-registry-control list-registries --region us-east-1
```

![Terminal capture: one registry aia-uc07-catalog, id niFvetsCk7ujKrAO, IAM discovery authorization, status READY](/images/agentcore-a2a-multi-agent-registry/S11-registry.png)

Search is the reason the catalog exists. The query never names the record:

```bash
aws agent-registry search-discoverable-registry-records --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --search-query "payment processing"
```

![Terminal capture: the first hit being record 5nMCxyY06tFl named billing, a Billing MCP server of type MCP in status APPROVED](/images/agentcore-a2a-multi-agent-registry/S12-search.png)

And the registry itself rides RAM, which is the whole story of
ram-cross-account:

```bash
aws ram get-resource-shares --region us-east-1 \
  --resource-owner SELF --name aia-uc07-registry-xacct \
  --resource-share-status ACTIVE
aws ram list-resources --region us-east-1 \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/feb617d9-da46-43dd-87cc-671293ebd120
```

![Terminal capture: the resource share aia-uc07-registry-xacct ACTIVE with external principals allowed and the series tags, with the registry listed as its only resource](/images/agentcore-a2a-multi-agent-registry/S13-ram.png)

Observability needs no extra wiring: `agentcore traces list` finds the
invocations and `traces get` downloads one, span included:

```bash
agentcore traces list --runtime aia_uc07_orchestrator --limit 5
agentcore traces get 6ae68aae0be02f262af76e4121aa04e9 --runtime aia_uc07_orchestrator
```

![Terminal capture: the trace list with four ids and one downloaded trace whose span body quotes the isolation test's session id and the orchestrator source line](/images/agentcore-a2a-multi-agent-registry/S14-traces.png)

Teardown is two halves. `remove all -y` empties the contract, then the
deploy reconciles the stack down — and it also empties both
`agentcore/agentcore.json` and `agentcore/aws-targets.json`, which is why
the status prints an empty target:

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status
```

![Terminal capture: schemas reset, the stack torn down, status reporting no resources, and an empty capacity-provider list](/images/agentcore-a2a-multi-agent-registry/S15-teardown.png)

Restore both JSON files from git, deploy again, and the tag query confirms
the account holds nothing but this use case's resources. Three RAM-share
records are ghosts of shares deleted earlier in the session, and the two
aiauc05 records are orphaned tag records whose harness was deleted in
another session — the tagging API returns 404 for the harnesses and 400 for
the shares, because the resource behind each record is gone:

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action
```

![Terminal capture: 22 tagged records, 17 of them live resources from this use case, three deleted RAM shares lingering as tag records, and the two aiauc05 harnesses failing untag with 404 and 400](/images/agentcore-a2a-multi-agent-registry/S16-independence.png)

The tag list is also the inventory of what `remove all` never touches. The
registry and the RAM share are not in the CLI contract, so they are deleted
with the AWS CLI, share first, then the records, then the registry:

```bash
aws ram delete-resource-share --region us-east-1 \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/feb617d9-da46-43dd-87cc-671293ebd120
aws agent-registry-control delete-registry-record --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id 5nMCxyY06tFl
aws agent-registry-control delete-registry-record --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO --record-id YRLG41zg45lV
aws agent-registry-control delete-registry --region us-east-1 \
  --registry-id niFvetsCk7ujKrAO
aws agent-registry-control list-registries --region us-east-1
aws ram get-resource-shares --region us-east-1 --resource-owner SELF \
  --name aia-uc07-registry-xacct --resource-share-status ACTIVE
```

![Terminal capture: the share deleted with returnValue true, the two records deleted silently, the registry DELETING, then both lists coming back empty](/images/agentcore-a2a-multi-agent-registry/S20-registry-teardown.png)

What survives is deliberate: the CDK bootstrap stack and its asset bucket
are account-level and reused across the whole series, and the runtime log
groups keep the traces above. Everything else from this use case is gone —
but only because those four deletions ran. Skip them, and the registry and
its share stay in the account, invisible to `agentcore remove all`, until
you delete them.

## What it produced

![Diagram: the caller reaches the orchestrator over AG-UI, which fans out over A2A to the legal and compliance specialists and over MCP to the billing server on its capacity provider, with the registry and its RAM share drawn as dashed catalog arrows, not traffic](/images/agentcore-a2a-multi-agent-registry/F1-multi-agent-registry.png)

The review request produced two completed A2A tasks in one 95.0-second
invocation. The deep scan accepted at 0.0 seconds and completed at 115.0
seconds, while the same work asked for blocking died at 184.9 seconds of
client read timeout — the async pattern is not a nicety, it is the only way
past the ceiling. Barge-in canceled a working stream at 12.1 seconds. Ten
sessions recalled ten distinct codewords. The MCP server answered tools/call
in 72.5 seconds cold on its own `m7g.large` and `c7g.large` pool. The
registry listed on the first call, search resolved payment processing to
billing, the RAM share sat ACTIVE, and every invocation left a trace whose
span quotes the exact session id the isolation test used.

## Troubleshooting

- `ListAgentRuntimes` returns names with the project prefix:
  `aiauc07_aia_uc07_legal`, not `aia_uc07_legal`. Match by suffix, never by
  equality.
- `GetAgentCard` wraps the card in an `agentCard` key; unwrap it before
  reading skills.
- The control-plane IAM prefix is `bedrock-agentcore:`, not
  `bedrock-agentcore-control:`. The wrong prefix fails silently through IAM
  propagation for minutes at a time.
- `t3.medium` is rejected by CreateCapacityProvider in us-east-1, and the
  CodeZip artifact built on this Mac is Linux aarch64, so the pool must be
  `LINUX_ARM64` with Graviton types. Capacity providers are immutable after
  creation — change means delete and recreate, and you cannot attach one to
  an existing runtime.
- `agentcore invoke` cannot parse an AG-UI SSE response; use
  `aws bedrock-agentcore invoke-agent-runtime --accept text/event-stream`.
- The registry MCP descriptor validates hard against `2025-12-11`: a
  tools block in `additionalData` and a description over about a hundred
  characters both fail. Ship the minimal name-description-version document.
- RAM tags are `key=K,value=V`, and a deleted resource can linger as a tag
  ghost that returns 404 on untag.

## Takeaways

- Protocols compose. The caller sees one AG-UI stream while the orchestrator
  runs A2A underneath, and none of the three protocols leaks into another.
- Non-blocking is a protocol feature, not a retry policy: accepted at 0.0
  seconds, completed at 115.0 seconds, versus a dead client at 184.9 seconds
  of read timeout for the identical work.
- Barge-in is only real if the executor cooperates; the canceled state
  arriving on the very next stream event is the proof, not the cancel call.
- One microVM per session id is a load-bearing property — it is what makes a
  plain dict a correct session store, and it is exactly what the codeword
  loop exercises.
- Pin instance types when the workload has a compute shape, and pin them at
  creation: the capacity provider and its attachment are both immutable.
- A catalog earns its keep the day search matters more than naming: the
  record is called billing, the question says payment processing, and the
  semantic index is what connects them — across accounts, through RAM.
