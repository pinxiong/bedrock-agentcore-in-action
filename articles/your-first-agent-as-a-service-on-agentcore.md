---
title: "Your First Agent as a Service: Deploying a Support Agent on AgentCore"
description: "Bedrock AgentCore tutorial: deploy a support agent on AgentCore Runtime in us-east-1, invoke it, read the execute_tool span in X-Ray, tear it down. Measured: deploy 1m51s, invoke 9.9s, 4 assertions passed, no Dockerfile."
date: 2026-10-18
draft: false
tags: ["ai", "agents", "agentcore", "aws"]
canonical_url: "https://xiongpin.dev/posts/your-first-agent-as-a-service-on-agentcore/"
cover:
  image: "/images/your-first-agent-as-a-service-on-agentcore/cover.png"
  alt: "Cover art: your first agent as a service. One folder in, one command to a READY runtime, one trace showing the tool call, measured in us-east-1"
---

A support team wants its first automation. This article is the walkthrough: one folder, one command to deploy, one invoke to prove it works, one trace to prove you can see it, one command to make it all go away. Every number below was captured while writing this.

![A support agent as a managed runtime: what you own, what AWS hosts, and the two things the runtime talks to](/images/your-first-agent-as-a-service-on-agentcore/F1-support-agent-runtime.png)

## The use case

A three-person support desk answers the same questions all day: refund totals, return windows, policy lines. They want a first automation, and nobody on the team has ever put a service in production. The ask is not intelligence, it is a loop they can trust: write something small, make it callable from anywhere, see what it did afterwards, and be able to delete it the same day.

## What AgentCore does here

Two of the nine AgentCore capabilities carry this use case.

- Runtime: hosts `app/aia_uc01/` as a managed endpoint. The build is CodeZip, so nothing is containerized; each session gets its own microVM; the protocol is plain HTTP over `/ping` and `/invocations`.
- Observability: every invoke emits OpenTelemetry spans into X-Ray, readable through CloudWatch, so the tool call is visible as its own span and not just as text in a log.

The other seven stay off. No Memory, so the agent keeps nothing between turns. No Gateway and no Identity, because the desk has no external systems to reach yet. The deployed runtime is version 1 behind the DEFAULT endpoint; changing the JSON and redeploying produces version 2 of the same endpoint, which is the whole versioning story at this level.

## Requirements

- Node.js 20 or newer (22.22.2 here), the AgentCore CLI 0.31.1, AWS CLI 2.x, uv 0.11.9
- Python 3.10 to 3.14 on the host; the runtime target here is PYTHON_3_13, set in the contract, not your interpreter
- An AWS account with Bedrock model access; region us-east-1 for everything
- Model: deepseek.v3.2, passed to the code through the `MODEL_ID` environment variable

```bash
agentcore --version   # 0.31.1
aws configure get region   # us-east-1
aws sts get-caller-identity --query Account --output text
# 123456789012
```

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/main/usecases/01-first-agent

```text
01-first-agent/
├── run.py                     # every operation; the cross-platform entry point
├── Makefile                   # forwards to run.py, holds no logic
├── agentcore/
│   ├── agentcore.json         # the contract: what gets deployed
│   └── aws-targets.json       # account 123456789012, region us-east-1
├── app/aia_uc01/
│   ├── main.py                # the agent: prompt, tool, sanitizer, entrypoint
│   ├── model/load.py          # MODEL_ID -> BedrockModel
│   ├── model/sanitize.py      # strips chat-template scaffolding from the stream
│   └── pyproject.toml         # dependencies packaged into the zip
└── tests/
    ├── smoke.py               # the four assertions, run against the deployment
    └── doctor.py              # toolchain, credentials and folder self-check
```

The folder is self-contained by assertion: `make check` copies it to a temporary directory and runs the checks again inside the copy.

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

The part worth copying is the filter around the stream. DeepSeek models sometimes write fragments of their own chat-template markers, such as `<|DSML|function_calls`, into the ordinary text channel. The leak is intermittent: in the four local invokes and one cloud invoke captured for this article it never appeared, and in the previous walkthrough of this series it appeared on the first try. The sanitizer holds back a short suffix that could still grow into a marker, resets once per assistant message, and flushes what is left when the message ends:

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

It is cheap insurance with its own offline tests: `make unit` runs six cases against the recorded marker bytes, no AWS involved.

Model selection is one function, because the default matters:

```python
def load_model() -> BedrockModel:
    return BedrockModel(model_id=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID))
```

If `MODEL_ID` is missing, an SDK default can pick a model your region refuses; passing the id explicitly is what keeps the first deploy from failing on geography.

## Deploy it

From the use case folder:

```bash
make doctor
```

```text
toolchain
  PASS  python 3.14.3 (inside the CodeZip 3.10 to 3.14 range)
  PASS  node v22.22.2
  PASS  aws cli aws-cli/2.15.6
  PASS  uv 0.11.9 (builds the app environment)

agentcore cli
  PASS  agentcore 0.31.1

this folder
  PASS  codeLocation 'app/aia_uc01' exists
  ...
  PASS  tests/copy_check.py present

aws environment
  PASS  credentials work, account 123456789012
  PASS  region is us-east-1
  PASS  model deepseek.v3.2 is available in us-east-1

15 passed, 0 warned, 0 failed
next: make deploy
```

The fifteen checks come in those four groups: four for the toolchain, one for the CLI, seven for the folder itself and three for the AWS environment.

`make dev` runs the same code locally on port 8080 with a real model and no deployment; the local invoke answered through the tool in about two seconds. Deploy is one command:

```bash
make deploy
```

```text
  Deploy to AWS ..................... 1 m 27 s

Total duration: 1 m 51 s

Deployed to 'default' (stack: AgentCore-aiauc01-default)

Outputs:
  ApplicationAgentAiaUc01RuntimeArnOutput3227EF65:
    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld
```

![Terminal capture: the deploy step timings from the CLI log and the stack outputs naming the runtime ARN](/images/your-first-agent-as-a-service-on-agentcore/S1-deploy.png)

![The loop in six commands, each with the output it produced on this run](/images/your-first-agent-as-a-service-on-agentcore/F2-deploy-loop.png)

Synthesizing CloudFormation took 15.4 s; the remaining 1 m 27 s was stack creation. The stack this contract produces is four resources: an AWS::BedrockAgentCore::Runtime, the AWS::IAM::Role it runs as, that role's AWS::IAM::Policy, and AWS::CDK::Metadata. That is the whole footprint; the resource types are recorded in `evidence/23-stack-resources.txt`. Status and one real invoke:

```bash
make status
make invoke
```

```text
  aia_uc01: Deployed - Runtime: READY
    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld

The refund total you should quote is $42.

Session: a99e785c-18e2-4b18-abef-368271019e7e
```

![Terminal capture: Runtime READY, then the deployed invoke answering the refund question with 42](/images/your-first-agent-as-a-service-on-agentcore/S2-status-invoke.png)

The four assertions run against the deployment, not against mocks:

```bash
make test
```

```text
runtime
       aiauc01_aia_uc01 v1 · arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld
  PASS assert_runtime_1: the runtime exists in the target region and reports status READY
       session 771b1dec-1664-4e54-9e69-409233cfbd5d · 16 events · tools ['add_numbers']
       reply 'The refund total should be $42.'
  PASS assert_runtime_2: invoking it answers a tool-using prompt and the reply has no model scaffolding

observability
       trace 1-6ad4087a-7220c9ed52be46e901c25cc9 · span 'execute_tool add_numbers'
  PASS assert_observability_1: that same invoke left an X-Ray trace whose span tree contains an execute_tool span

  PASS independence: no other use case's resources present

4 passed, 0 failed
```

![Terminal capture: the smoke test passing its four assertions, including the execute_tool span](/images/your-first-agent-as-a-service-on-agentcore/S4-verify.png)

Teardown is one make target that runs two commands, and the second one does the deleting. `make status` is what confirms it:

```bash
make down
make status
```

```text
All schemas reset to empty state
✓ Tear down stack
✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)

Total duration: 1 m 28 s

  aia_uc01: Local only
```

`down` rewrites `agentcore.json` and empties `aws-targets.json`; restore both from git before deploying again.

## What it produced

The invoke is unremarkable on purpose: one sentence, the right arithmetic, nothing else. The interesting artifact is the trace, and the tree reads like the agent loop drawn by the runtime itself:

```text
invoke_agent Strands Agents        2.50 s   tools=["add_numbers"]
  execute_event_loop_cycle  cycle 1
    chat  deepseek.v3.2            0.68 s   431 in / 60 out
  execute_event_loop_cycle  cycle 2
    chat  deepseek.v3.2            1.82 s   514 in / 11 out
    execute_tool add_numbers       success
```

![Terminal capture of the trace: two model round trips, token counts, and the tool span](/images/your-first-agent-as-a-service-on-agentcore/S3-trace.png)

![The same span tree drawn from the X-Ray trace: one span per step of the loop](/images/your-first-agent-as-a-service-on-agentcore/F3-span-tree.png)

The `execute_tool` span is the point. It is what separates "the model said 42" from "the tool computed 42 and the model reported it", and it only exists on the deployed runtime; local `agentcore dev` traces record the tool call in logs but not as a span.

Cost, measured on this run: the traced invoke used 945 input and 71 output tokens, which at deepseek.v3.2 prices in us-east-1, 0.62 and 1.85 USD per million tokens, is 0.00072 USD of model calls. Six billable invokes happened while writing this article. The runtime bills per use, so a deployed agent left idle costs nothing, and the teardown leaves nothing tagged to this use case behind.

## Troubleshooting

- `make down` died on its first line in a non-interactive shell with "This command requires an interactive terminal". Any piped or CI run hits this. The fix is the `-y` flag on `agentcore remove all`, which is what `run.py` now passes.
- `agentcore remove all` empties `agentcore.json` and also wipes `aws-targets.json`, so the next deploy has no target and answers `No resources match the given filters`. Restore both files from git after a teardown if you plan to deploy again.

## Takeaways

- The contract is two JSON files; everything else on the AWS side is generated, so the deploy is reproducible and the teardown is real.
- CodeZip means no Dockerfile: the platform zips `codeLocation`, and the runtime version and endpoint come from the same contract.
- An agent is not observable until a tool call has its own span; write that assertion before you need it.
- A stream sanitizer belongs in the entrypoint from day one, because scaffolding leaks are intermittent and a test-only filter rots.
- The full loop, measured: doctor in seconds, deploy 1 m 51 s, invoke 9 911 ms, down 1 m 28 s.
