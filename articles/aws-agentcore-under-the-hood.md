---
title: "How AWS Bedrock AgentCore Actually Works: One JSON File In, Four CloudFormation Resources Out"
date: 2026-10-15
draft: true
description: "A step-by-step walkthrough of AWS Bedrock AgentCore: set up the environment, scaffold a project with one command, deploy, invoke, read the trace, and see how one JSON file becomes four CloudFormation resources."
tags: ["aws", "bedrock", "agentcore", "cdk", "ai-agents"]
---

Most agent deployment stories end the same way: write a Dockerfile, pick an instance size, hand-roll an IAM role and hope the YAML is right. AWS Bedrock AgentCore takes a different path. The whole deployment contract is one JSON file, and a single command turns it into a running, observable endpoint.

I deployed an agent this way, broke it a few times and traced every step between the JSON file and the live endpoint. This article walks the full path once, step by step and explains what happens under the hood at each step. Every command and every output below comes from a real deployment in us-east-1, not from the docs.

![The whole AgentCore CLI lifecycle in six commands](images/aws-agentcore-under-the-hood/F0-command-map.png)

## What AgentCore is and what it is not

AgentCore is a family of managed runtimes for AI agents. The family covers 14 capabilities, from the runtime that hosts your code to memory, gateway, identity, policy, web search, browser, code interpreter, observability, evaluations, optimization, payments and a registry. This article lights up only two of those 14: the runtime and observability.

![AgentCore: 14 managed capabilities, 2 lit up in this article](images/aws-agentcore-under-the-hood/F1-capability-map.png)

What it is not matters more than what it is:

- It is not a new agent framework. You still write your agent in Strands, LangChain, the OpenAI SDK or raw Python.
- It is not container orchestration. The runtime is serverless: each session gets its own microVM and the platform handles scaling.
- It is not a model router. Your code calls Bedrock the same way it would anywhere else. AgentCore hosts that code and gives it an HTTP endpoint, an IAM role and a trace pipeline.

If you have ever self-managed an agent on ECS or Fargate, the difference is sharp. No Dockerfile, no task definition, no target group, no health check target to configure. The runtime expects two routes from your code and provides everything else.

## Three layers, one direction

You write agent code. You write two JSON files. The CLI generates everything else. AWS runs a CloudFormation stack that you never have to look at.

![Three layers: your code, the contract, the plumbing](images/aws-agentcore-under-the-hood/F2-three-layers.png)

| Layer | What lives there | Who maintains it |
|---|---|---|
| Your code | `src/` with the agent entrypoint | you |
| The contract | `agentcore.json` and `aws-targets.json` | you, by hand |
| The plumbing | a CDK project under `agentcore/cdk/` | the CLI, on every deploy |

One rule explains most of the design: everything you declare lives in JSON, and everything the CLI generates is regenerable. The rest of this article is that one rule, traced end to end.

## The environment you need

Before touching AgentCore, make sure your machine and account match this table. Everything here was verified on 2026-10-14.

| Tool | Version used | Notes | Check |
|---|---|---|---|
| Node.js | 22.x | 20+ required by the CLI | `node --version` |
| AgentCore CLI | 0.31.1 | install below | `agentcore --version` |
| AWS CLI | 2.x | any recent build | `aws --version` |
| Python | 3.11 local | 3.10 to 3.13 supported by CodeZip | `python3 -V` |
| AWS account | any | with permissions below | `aws sts get-caller-identity` |
| Region | us-east-1 | the whole series uses it | `aws configure get region` |
| Docker | not needed | this series uses CodeZip builds | n/a |

Install the CLI and point AWS at the right region:

```bash
npm install -g @aws/agentcore@latest
aws configure set region us-east-1
```

Then run four checks and compare against this output:

```bash
agentcore --version
# 0.31.1

aws sts get-caller-identity --query '[Account,Arn]' --output text
# 123456789012    arn:aws:iam::123456789012:user/yourname

aws configure get region
# us-east-1

aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?modelId==`deepseek.v3.2`].modelId' --output text
# deepseek.v3.2
```

**Permissions.** Two kinds of identity are involved, and it is worth separating them:

- *You* (the deployer) need enough to create CloudFormation stacks, upload to the CDK bootstrap bucket and manage Bedrock AgentCore resources. On a sandbox account, admin access is the honest shortcut. For a locked-down account, the CLI fails loudly and names the missing action, so you can grant incrementally.
- *The runtime* (your deployed agent) gets an IAM role that the CLI generates for you. In my deployment that role carried exactly three permission groups: `bedrock:InvokeModel*` for model calls, `logs:*` actions for the log group under `/aws/bedrock-agentcore/runtimes/`, and `xray:PutTraceSegments` for traces. That generated policy is a good template for least privilege later.

One trap worth five seconds: if `agentcore --version` errors but the command exists, an old Python package (`bedrock-agentcore-starter-toolkit`) is shadowing the npm one. `pip uninstall bedrock-agentcore-starter-toolkit` fixes it.

> **📸 Screenshot spot 1 · Environment check**
> Run the four checks above and paste your terminal capture here (replace this block with your screenshot).

## Step 1 · Scaffold the project

`agentcore create` builds the project skeleton. I ran it with `--no-agent` here so the scaffold stays minimal; drop the flag to also generate a starter agent:

```bash
mkdir demo && cd demo
agentcore create --name demo_proj --project-name demoproj --no-agent --build CodeZip
```

```text
[done]  Create demoproj/ project directory
```

The interesting part is what lands on disk. One directory holds your future code, and one subdirectory belongs to the CLI:

![Project anatomy: what you write vs what the CLI generates](images/aws-agentcore-under-the-hood/F3-directory-anatomy.png)

Two facts about this layout will save you an hour someday:

- Files with blue squares are yours. Files with gray squares are generated. Never hand-edit a gray file, because the next command overwrites it.
- Project detection is strict: the CLI walks up from your current directory until it finds a folder containing both `agentcore/` and `agentcore/agentcore.json`. Either alone is not a project, and the error (`No agentcore project found`) does not tell you which one is missing. Run commands from the directory that contains `agentcore/`, or the CLI refuses with `Please run this command from your project root directory`.

Peek inside the generated contract and you will see the shape of the design: `agentcore.json` with fifteen resource arrays, all empty; `aws-targets.json` with just `[]`. You are about to fill both in.

> **📸 Screenshot spot 2 · Project scaffold**
> Run `agentcore create` and `ls -R` (or `tree agentcore/`) and paste the terminal capture here.

## Step 2 · Write the contract: two JSON files

Here is the whole deployment definition for my test agent, trimmed to the fields that matter:

```json
{
  "$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
  "name": "aiauc01",
  "version": 1,
  "managedBy": "CDK",
  "runtimes": [
    {
      "name": "aia_uc01",
      "build": "CodeZip",
      "entrypoint": "main.py",
      "codeLocation": "src/",
      "runtimeVersion": "PYTHON_3_13",
      "protocol": "HTTP",
      "envVars": [{ "name": "MODEL_ID", "value": "deepseek.v3.2" }]
    }
  ],
  "memories": [],
  "knowledgeBases": [],
  "agentCoreGateways": []
}
```

`create` writes this file with every resource array empty. The `agentcore add` family (`add agent`, `add memory`, `add gateway`) then pushes entries in. Hand edits are allowed, but the published schema is the authority because the CLI validates every field against it.

The second file decides where the deployment lands:

```json
[
  { "name": "default", "account": "123456789012", "region": "us-east-1" }
]
```

Here is the part that surprised me. `create` writes only an empty array. The account and region are filled in by the first `deploy`, which calls STS, learns who you are and writes the target back into the file. There is no `--region` flag on deploy, status or remove. The file is the only source of truth for where your agent lands.

## Step 3 · Deploy: one command, six steps

Now the moment the whole article is named after. From the project root:

```bash
agentcore deploy -y --target default
```

Real output, first deploy ever on a cold account:

```text
✓ Load deployment target
✓ Validate project
✓ Sync CDK dependencies
✓ Build CDK project
✓ Synthesize CloudFormation
✓ Check bootstrap status
✓ Check stack status
✓ Deploy to AWS
✓ Persist deployment state
✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)
  ApplicationAgentAiaUc01RuntimeIdOutput734A07B7: aiauc01_aia_uc01-LH8zQV86C2
  ApplicationAgentAiaUc01RuntimeArnOutput3227EF65: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-LH8zQV86C2
```

Between the command and the last checkmark, six things happen:

![Deploy: six steps to READY, with measured timings](images/aws-agentcore-under-the-hood/F4-deploy-pipeline.png)

1. **Package the code.** The CLI zips `src/` with platform dependencies into one asset. My hello-world agent produced a 41 MB zip. The local `.venv` is excluded, so the artifact stays clean. No image is built anywhere in the project.
2. **Synthesize.** The CLI runs the vendored CDK app (`node dist/bin/cdk.js`). That app reads both JSON files and emits a CloudFormation template into `cdk.out/`.
3. **Upload the asset.** The zip lands in the S3 bucket that `cdk bootstrap` created once per account and region. Skip that one-time bootstrap and no CDK deployment can store an asset at all.
4. **Create the stack.** CloudFormation provisions four resources: the Runtime itself, an IAM role for it, an IAM policy that grants Bedrock model access, and a CDK metadata resource.
5. **Record the state.** The CLI writes `agentcore/.cli/deployed-state.json` with the runtime ARN and endpoint.
6. **Print the endpoint.**

The synthesis step is where the schema-first design becomes visible. The generated app reads your files by path, with no project knowledge of its own:

```ts
// agentcore/cdk/bin/cdk.ts, verbatim from the generated project
async function main() {
  // Config root is parent of cdk/ directory. The CLI sets process.cwd() to agentcore/cdk/.
  const configRoot = path.resolve(process.cwd(), '..');
  const configIO = new ConfigIO({ baseDir: configRoot });

  const spec = await configIO.readProjectSpec();             // agentcore.json
  const targets = await configIO.readAWSDeploymentTargets(); // aws-targets.json
  ...
}
```

The stack name also comes from the JSON (`AgentCore-<projectName>-<targetName>`, mine was `AgentCore-aiauc01-default`). I grepped the generated project for hard-coded names and found zero hits. The same TypeScript synthesizes a different stack for any JSON you feed it. That is what schema-first means in practice: `cdk/` is a compiler and `agentcore.json` is the program.

Timings, because every tutorial skips them: the first deploy on a cold account took 9 minutes 49 seconds, mostly `npm install` for the CDK project (221 packages), the asset upload and the CloudFormation create. A code-only redeploy took 26 seconds, because the stack already exists and only the asset hash changes.

Verify with `agentcore status`, which should report `Runtime: READY` plus the endpoint URL.

> **📸 Screenshot spot 3 · First deploy**
> Paste your `agentcore deploy` success output here, including the stack name and runtime ARN lines.

## Step 4 · Run the same code locally

Before (or without) deploying, `agentcore dev` starts the same app under Uvicorn on `localhost:8080`, with the same two routes. Model calls still go to Bedrock, so you need credentials but no deployment:

```bash
agentcore dev
# (in another terminal)
curl -s -X POST http://localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What is 128 plus 256? Use the tool."}'
```

The reply comes back as a server-sent-event stream with the tool call visible inside it, and I edited `main.py` while the server ran and watched the reloader pick the change up without a restart.

> **📸 Screenshot spot 4 · Local run**
> Paste your `agentcore dev` session here: the server boot line and the curl reply.

## Step 5 · Invoke the deployed runtime

The deployed runtime answers through the data plane. The CLI wraps it with a friendly command:

```bash
agentcore invoke --prompt "What is 17 plus 25? Use the tool."
```

```text
I'll use the addition tool to calculate the sum of 17 and 25.

17 plus 25 equals 42.

Session: 53451706-bd56-43f3-84ef-1eceaa3c2aee
To resume: agentcore invoke --session-id 53451706-bd56-43f3-84ef-1eceaa3c2aee
Log: .../agentcore/.cli/logs/invoke/invoke-aia_uc01-20261014-153601.log
```

The same prompt against the raw data plane (boto3 `invoke_agent_runtime`) returns the SSE stream, and the tool call is not hidden inside it:

```text
data: {"event": {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "tooluse_V8T0pNRzrKLCyUR7wmvlVd", "name": "add_numbers"}}, "contentBlockIndex": 1}}}
data: {"event": {"contentBlockDelta": {"delta": {"toolUse": {"input": "{\"a\": 11, \"b\": 31}"}}, "contentBlockIndex": 1}}}
data: {"event": {"messageStop": {"stopReason": "tool_use"}}}
data: {"event": {"messageStart": {"role": "assistant"}}}
data: {"event": {"contentBlockDelta": {"delta": {"text": "11 plus 31 equals 42."}, "contentBlockIndex": 0}}}
data: {"event": {"messageStop": {"stopReason": "end_turn"}}}
data: {"event": {"metadata": {"usage": {"inputTokens": 471, "outputTokens": 9, "totalTokens": 480}, "metrics": {"latencyMs": 820}}}}
```

![One HTTP surface, two hosts: agentcore dev and agentcore deploy](images/aws-agentcore-under-the-hood/F5-one-surface.png)

"One surface" means the two routes your code has to implement: `GET /ping` for health checks and `POST /invocations` for work. "Two hosts" means the two environments that serve those same routes. Locally, `agentcore dev` runs your app under Uvicorn on `localhost:8080`. In the cloud, a managed microVM serves them behind `https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<runtime-arn>/invocations`. Routing, scaling and TLS sit on the platform side, so your code never learns which host it is on. And `agentcore invoke` is not a third interface: it is a CLI client for the hosted `/invocations` endpoint, the same way boto3 is.

Tool calls ride on native Bedrock `toolUse` protocol blocks, both locally and in the cloud. Nothing in AgentCore invents a new tool protocol for you to learn.

What did that cost? DeepSeek V3.2 in us-east-1 costs $0.62 per million input tokens and $1.85 per million output. A two-cycle invoke used 846 input and 82 output tokens: about $0.0007 of model calls plus roughly $0.0002 of runtime compute. The infrastructure bill for a tutorial-grade agent rounds to zero.

> **📸 Screenshot spot 5 · Cloud invoke**
> Paste your `agentcore invoke` reply here (the one that prints the session ID).

## Under the hood I: the HTTP contract

Strip away the tooling. The runtime makes exactly two requests to your code: `GET /ping` for health checks and `POST /invocations` for work. `BedrockAgentCoreApp` is a thin adapter that maps those routes onto an async generator you write:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool

app = BedrockAgentCoreApp()

@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b

@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(extract_prompt(payload)):
        yield event
```

(The real file also filters every text delta through a stream sanitizer, which the failure section explains). Three things in this snippet are worth noticing:

- The entrypoint is an async generator. Every yielded dict becomes one server-sent event in the response stream, so streaming is the default shape of the platform, not an add-on.
- `context.session_id` is how you shard state. Each session runs in its own microVM and the platform handles scaling. Your only job is keying state by session.
- The model is a parameter. `MODEL_ID` arrives as an environment variable declared in `agentcore.json`, and a 40-line module turns it into a Strands `BedrockModel`. Changing models means changing one JSON value.

## Under the hood II: what observability records

A deployed invoke produces this span tree in X-Ray. The output is real, including the token counts:

```bash
agentcore traces list          # lists recent traces (2-3 min after the invoke)
agentcore traces get <trace-id>
```

![The X-Ray span tree of one tool-using invoke](images/aws-agentcore-under-the-hood/F6-span-tree.png)

```text
invoke_agent Strands Agents              gen_ai.agent.tools=["add_numbers"]  tokens=934
├── execute_event_loop_cycle  (cycle 1)
│   ├── execute_tool add_numbers         gen_ai.tool.status=success  span_kind=TOOL
│   └── chat  deepseek.v3.2 (LLM, 451 tokens)
│       └── BedrockRuntime ConverseStream   finish_reason=tool_use
└── execute_event_loop_cycle  (cycle 2)
    └── chat  deepseek.v3.2 (LLM, 483 tokens)
        └── BedrockRuntime ConverseStream   finish_reason=end_turn
```

The structure teaches you how the agent loop works even if you never read the framework source: one cycle per model round trip, the tool call as its own span inside the cycle, and a second cycle that consumes the tool result.

Two honest caveats come from measuring this. First, spans are asynchronous: transaction search took about ten minutes before anything was queryable, so a test that invokes and immediately greps CloudWatch will fail. Second, the local `agentcore dev` traces (OTLP files under `agentcore/.cli/traces/`) record tool calls in logs but not as spans. Only the deployed runtime emits the `execute_tool` span, which is why a smoke test that asserts on a tool span must run against the deployment.

> **📸 Screenshot spot 6 · Observability**
> Paste the CloudWatch GenAI observability console (or your `agentcore traces get` output) showing the `execute_tool` span here.

## What broke and what it taught

Four failures are worth passing on:

- **Stale `cdk.out` fails the next deploy.** The CLI deletes `cdk.out` before each synth. Leftover state from a previous run made one synth die with `Subprocess exited with error 1`. Manually running `cdk synth` worked, which is how I knew the project itself was fine. `rm -rf agentcore/cdk/cdk.out` fixed it. Treat `cdk.out` like any build artifact: deletable at any time.
- **Renaming is destroying.** The `name` field becomes the CloudFormation logical ID. If you change it, CloudFormation does not rename anything; it deletes the old runtime and creates a new one.
- **The model leaks scaffolding into the text channel.** `deepseek.v3.2` emitted fragments of its internal chat-template markers as ordinary text, and the Nova models emitted `<thinking>` blocks. I proved this was model behavior rather than a framework bug by calling Bedrock's `converse_stream` directly with Strands removed from the picture. All four models I tried leaked something. The fix lives in the entrypoint: a stream-safe filter that holds back marker prefixes and resets once per assistant message, because one tool-using turn is several messages and a cut in one must not silence the next.
- **The region is not a flag.** Every guess at `--region` fails with `unknown option`. The targets file decides, and it fills itself in on first deploy.

## Takeaways

1. **The JSON file is the interface.** Everything else (the CDK project, the template, the stack) is regenerable plumbing driven by it.
2. **CDK appears here as a vendored compiler.** You never write constructs and you never edit the generated project. Change the schema and the same code compiles a different stack.
3. **Local and deployed share one HTTP contract.** `/ping` and `/invocations` behave identically, so the code that passed locally deploys without a shim, because there is no second interface to drift away from the first.
4. **Observability is real but asynchronous.** The tool call gets its own span in the cloud. Spans need minutes to become queryable, so write your tests accordingly.

One sentence to take away: in AgentCore your infrastructure is not code you maintain. It is code that compiles.

## The setup behind the numbers

All measurements come from one real deployment on 2026-10-14: AgentCore CLI 0.31.1, Node 22, local Python 3.11 (runtime target `PYTHON_3_13`), Strands Agents 1.60.0, `bedrock-agentcore` 1.24.1, the `deepseek.v3.2` model in us-east-1, CodeZip builds (no containers), and one hello-world agent with a single `add_numbers` tool. Deploy timings are wall-clock times on a cold account. Token counts are read from the trace spans rather than estimated.

## Screenshot checklist (for publishing)

This article reserves six spots for your own terminal captures. Fill them in after running the steps, then delete this section before publishing:

| Spot | After which step | What to capture |
|---|---|---|
| 1 | environment checks | the four check commands and their output |
| 2 | Step 1 | `agentcore create` output plus the project tree |
| 3 | Step 3 | deploy success lines with stack name and ARN |
| 4 | Step 4 | `agentcore dev` boot line and the curl reply |
| 5 | Step 5 | `agentcore invoke` reply with session ID |
| 6 | Under the hood II | the trace showing the `execute_tool` span |
