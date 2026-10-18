---
title: "Your First Agent as a Service: Deploying a Support Agent on AgentCore"
description: "Bedrock AgentCore tutorial: deploy a support agent with agentcore deploy, invoke it, read the execute_tool span in the trace, tear it down. Measured in us-east-1."
date: 2026-10-18
draft: false
tags: ["ai", "agents", "agentcore", "aws"]
canonical_url: "https://xiongpin.dev/posts/your-first-agent-as-a-service-on-agentcore/"
cover:
  image: "/images/your-first-agent-as-a-service-on-agentcore/cover.png"
  alt: "Cover art: your first agent as a service. One folder in, one command to a READY runtime, one trace showing the tool call, measured in us-east-1"
---

A support team wants its first automation. This article is the walkthrough: one folder, one contract, and the `agentcore` and `aws` commands that deploy it, prove it, and delete it again. Every command below was run while writing this, and every figure is that command's captured output.

![A support agent as a managed runtime: what you own, what AWS hosts, and the two things the runtime talks to](/images/your-first-agent-as-a-service-on-agentcore/F1-support-agent-runtime.png)

## The use case

A three-person support desk answers the same questions all day: refund totals, return windows, policy lines. They want a first automation, and nobody on the team has ever put a service in production. The ask is not intelligence, it is a loop they can trust: write something small, make it callable from anywhere, see what it did afterwards, and be able to delete it the same day.

## What AgentCore does here

Two of the nine AgentCore capabilities carry this use case.

- Runtime: hosts `app/aia_uc01/` as a managed endpoint. The build is CodeZip, so nothing is containerized; each session gets its own microVM; the protocol is plain HTTP over `/ping` and `/invocations`.
- Observability: every invoke emits OpenTelemetry spans into X-Ray, so the tool call is visible as its own span and not just as text in a log.

The other seven stay off. No Memory, so the agent keeps nothing between turns. No Gateway and no Identity, because the desk has no external systems to reach yet. The runtime is version 1 behind the DEFAULT endpoint; changing the JSON and redeploying produces version 2, which is the whole versioning story at this level.

## Requirements

- Node.js 20 or newer (22.22.2 here), the AgentCore CLI 0.31.1, AWS CLI 2.x, jq 1.7.1, uv 0.11.9
- Python 3.10 to 3.14 on the host; the runtime target is PYTHON_3_13, set in the contract
- An AWS account with Bedrock model access; region us-east-1 for everything
- Model: deepseek.v3.2, passed to the code through the `MODEL_ID` environment variable

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/01-first-agent

```text
01-first-agent/
├── agentcore/
│   ├── agentcore.json         # the contract: what gets deployed
│   └── aws-targets.json       # account 123456789012, region us-east-1
├── app/aia_uc01/
│   ├── main.py                # the agent: prompt, tool, sanitizer, entrypoint
│   ├── model/load.py          # MODEL_ID -> BedrockModel
│   ├── model/sanitize.py      # strips chat-template scaffolding from the stream
│   └── pyproject.toml         # dependencies packaged into the zip
└── tests/
    └── test_sanitize.py       # six offline cases for the sanitizer, no AWS
```

Two JSON files are the whole contract; `main.py` is the whole agent. The folder ships no script of its own: every operation below is an `agentcore` or `aws` command.

## How it works

The whole agent surface fits in one screen of `main.py`:

```python
SYSTEM_PROMPT = """You are the first-line assistant for the Northwind Gear
support desk. Answer in one short sentence.
When a question involves arithmetic, call the add_numbers tool instead of
working it out yourself, then state the result in one short sentence.
You have no order database, no ticket history and no account lookup. When a
question needs one of those, say you cannot see it instead of guessing."""

@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b

@app.entrypoint
async def invoke(payload: Any, context: Any):
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    scrub = StreamSanitizer()
    async for event in agent.stream_async(extract_prompt(payload)):
        ...  # every text delta passes through scrub.feed() before it is yielded
```

The prompt is the product. The tool exists so the trace has something to show; an agent that never calls a tool produces a single span and proves little. The entrypoint is an async generator, which is why streaming is the default shape here rather than an add-on.

The part worth copying is the filter around the stream. DeepSeek models sometimes write fragments of their own chat-template markers, such as `<|DSML|function_calls`, into the ordinary text channel. The sanitizer holds back a short suffix that could still grow into a marker, resets once per assistant message, and flushes what is left when the message ends:

```python
if "messageStart" in inner:
    scrub = StreamSanitizer()      # one clean filter per assistant message
    block_index = 0
    yield event
    continue
...
clean = scrub.feed(delta["text"])  # tool-use deltas pass through untouched
if clean:
    yield _text_delta(clean, block_index)
```

Its six cases live in `tests/test_sanitize.py` and run offline, no AWS involved, because a filter you cannot test cheaply is a filter you will delete.

Model selection is one function, because the default matters:

```python
def load_model() -> BedrockModel:
    return BedrockModel(model_id=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID))
```

If `MODEL_ID` is missing, an SDK default can pick a model your region refuses; passing the id explicitly is what keeps the first deploy from failing on geography.

## Deploy it

From the use case folder, one command builds the zip, synthesizes the CloudFormation and creates the stack:

```bash
agentcore deploy -y --target default
```

![Terminal capture: the deploy steps, the runtime id and the runtime ARN it printed](/images/your-first-agent-as-a-service-on-agentcore/S1-deploy.png)

The stack this contract produces is four resources: an AWS::BedrockAgentCore::Runtime, the AWS::IAM::Role it runs as, that role's AWS::IAM::Policy, and AWS::CDK::Metadata (recorded in `evidence/23-stack-resources.txt`). The deploy log splits the total: 4.1 s synthesizing CloudFormation, 1 m 17 s creating the stack, 1 m 31 s end to end. Then status, and one real invoke:

```bash
agentcore status
```

![Terminal capture: Runtime READY and the invoke URL the CLI hands back](/images/your-first-agent-as-a-service-on-agentcore/S2-status.png)

```bash
agentcore invoke --prompt "A customer returns two items priced 21 each. What refund total should I quote? Use the tool."
```

![Terminal capture: the deployed invoke answering the refund question with 42](/images/your-first-agent-as-a-service-on-agentcore/S3-invoke.png)

What the deploy produced is provable from the CLI alone; the four things an assertion script used to check are four things this output shows.

- `agentcore status` printed `Deployed - Runtime: READY` and the runtime ARN, so the runtime exists in us-east-1 and can serve traffic.
- `agentcore invoke` answered a tool-using prompt with the right arithmetic and no model scaffolding in the reply.
- The invoke left a trace, listed below, whose span tree contains an `execute_tool` span.
- `aws resourcegroupstaggingapi get-resources` returned three rows, all tagged `UseCase=01`: no other use case's resources are in the account.

```bash
agentcore traces list
```

![Terminal capture: the trace from that session, listed about three minutes after the invoke](/images/your-first-agent-as-a-service-on-agentcore/S4-traces-list.png)

```bash
agentcore traces get 6ad45817558974710d8c3b6d35f5a089
```

![Terminal capture: the trace downloaded to a JSON file under agentcore/.cli/traces](/images/your-first-agent-as-a-service-on-agentcore/S5-trace-get.png)

```bash
jq -r '[.[] ."@message" | select(type == "object" and .name != null)] as $spans
  | ($spans | map({(.spanId): .name}) | add) as $parent
  | $spans | sort_by(.startTimeUnixNano) | .[] | (.attributes // {}) as $a
  | [.name, .kind, (((.durationNano // 0) / 1000000 | floor | tostring) + " ms"),
     (if $a["gen_ai.usage.input_tokens"] then ($a["gen_ai.usage.input_tokens"] | tostring) + " in / " + ($a["gen_ai.usage.output_tokens"] | tostring) + " out" else "-" end),
     ($parent[.parentSpanId // ""] // "root")] | @tsv' \
  agentcore/.cli/traces/aia_uc01-6ad45817558974710d8c3b6d35f5a089.json | column -t -s $'\t'
```

![Terminal capture: nine spans out of the downloaded trace, including execute_tool add_numbers](/images/your-first-agent-as-a-service-on-agentcore/S6-trace-spans.png)

```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action \
  --region us-east-1 --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' --output text
```

![Terminal capture: three tagged resources, every one of them UseCase=01](/images/your-first-agent-as-a-service-on-agentcore/S7-independence.png)

Teardown is two commands, and the second one does the deleting. `agentcore remove all` empties the local contract; the deploy that follows reconciles the stack to nothing:

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status
```

![Terminal capture: the schema reset, the stack teardown, and status finding nothing left](/images/your-first-agent-as-a-service-on-agentcore/S8-teardown.png)

![The six commands of the loop and what each one cost on this run](/images/your-first-agent-as-a-service-on-agentcore/F2-deploy-loop.png)

Six commands, and the loop closes where it started: nothing deployed, nothing tagged, one trace kept.

## What it produced

The invoke is unremarkable on purpose: one sentence, the right arithmetic, nothing else. The interesting artifact is the span tree, and it reads like the agent loop drawn by the runtime itself:

![The span tree drawn from the X-Ray trace: one span per step of the loop](/images/your-first-agent-as-a-service-on-agentcore/F3-span-tree.png)

The `execute_tool` span is the point. It is what separates "the model said 42" from "the tool computed 42 and the model reported it", and it only exists on the deployed runtime; traces from a local `agentcore dev` session record the tool call in logs but not as a span.

Cost, measured on this run: the traced invoke used 955 input and 81 output tokens, which at deepseek.v3.2 prices in us-east-1, 0.62 and 1.85 USD per million tokens, is 0.00074 USD of model calls. The runtime bills per use, so an idle deployed agent costs nothing, and the teardown leaves nothing tagged behind.

## Troubleshooting

- `agentcore remove all` without `-y` dies in a non-interactive shell with "This command requires an interactive terminal". Any piped or CI run hits this. The fix is the `-y` flag, and it is not optional in a script.
- `agentcore remove all -y` resets every schema in `agentcore.json` and empties `aws-targets.json`, so the next deploy has no target and `agentcore status` answers `No resources match the given filters`. Restore both files from git before you deploy again.

## Takeaways

- The contract is two JSON files; everything else on the AWS side is generated, so the deploy is reproducible and the teardown is real.
- CodeZip means no Dockerfile: the platform zips `codeLocation`, and the runtime version and endpoint come from the same contract.
- An agent is not observable until a tool call has its own span; `agentcore traces get` plus `jq` is the whole proof, no test harness required.
- A stream sanitizer belongs in the entrypoint from day one, because scaffolding leaks are intermittent and a test-only filter rots.
- The full loop, measured: deploy 1 m 31 s, invoke 9 954 ms, teardown 1 m 40 s, and `remove all -y` to `deploy -y` in that order.
