---
title: "How AWS Bedrock AgentCore Actually Works: One JSON File In, Four CloudFormation Resources Out"
date: 2026-10-15
draft: true
description: "I deployed a Bedrock AgentCore agent, broke it a few times, and traced every step from the JSON file to the live endpoint. Here is what actually happens between agentcore deploy and a READY runtime."
tags: ["aws", "bedrock", "agentcore", "cdk", "ai-agents"]
---

Most agent deployment stories end the same way: write a Dockerfile, pick an instance size, hand-roll an IAM role and hope the YAML is right. AWS Bedrock AgentCore takes a different path. The whole deployment contract is one JSON file. A single command turns it into a running, observable endpoint.

I deployed an agent this way, broke it a few times and traced every step between the JSON file and the live endpoint. This article explains what actually happens in between: what the CLI generates, what CDK compiles, what CloudFormation creates and what your code has to promise in return. Everything below comes from a real deployment in us-east-1, not from the docs.

## The mental model: three layers

You write agent code. You write two JSON files. The CLI generates everything else. AWS runs a CloudFormation stack that you never have to look at.

| Layer | What lives there | Who maintains it |
|---|---|---|
| Your code | `src/` with the agent entrypoint | you |
| The contract | `agentcore.json` and `aws-targets.json` | you, by hand |
| The plumbing | a CDK project under `agentcore/cdk/` | the CLI, on every deploy |

One rule explains most of the design. Everything you declare lives in JSON. Everything the CLI generates is regenerable. In short, the rest of this article is that one rule, traced end to end.

## The contract: two JSON files

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

`agentcore create` writes this file with every resource array empty. The `agentcore add` family (add agent, add memory, add gateway) then pushes entries in. Hand edits are allowed, but the published schema is the authority because the CLI validates every field against it.

The second file decides where the deployment lands:

```json
[
  { "name": "default", "account": "123456789012", "region": "us-east-1" }
]
```

Here is the part that surprised me. `create` writes only an empty array. The account and region are filled in by the first `deploy`, which calls STS, learns who you are and writes the target back into the file. There is no `--region` flag on deploy, status or remove. The file is the only source of truth for where your agent lands.

One more discovery about project detection. The CLI walks up from your current directory until it finds a folder that contains both `agentcore/` and `agentcore/agentcore.json`. Either one alone is not a project, which is why the error (`No agentcore project found`) does not tell you which one is missing. Run commands from the directory that contains `agentcore/`, or the CLI refuses with `Please run this command from your project root directory`.

## What deploy actually does

Six steps happen between `agentcore deploy` and a READY runtime:

1. **Package the code.** The CLI zips `src/` with platform dependencies into one asset. My hello-world agent produced a 41 MB zip. The local `.venv` is excluded, so the artifact stays clean. In contrast to a Dockerfile workflow, no image is built anywhere in the project.
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

The stack name also comes from the JSON:

```ts
function toStackName(projectName: string, targetName: string): string {
  return `AgentCore-${sanitize(projectName)}-${sanitize(targetName)}`;
}
```

My stack was `AgentCore-aiauc01-default`. I grepped the generated project for hard-coded names and found zero hits. The same TypeScript synthesizes a different stack for any JSON you feed it. That is what schema-first means in practice: `cdk/` is a compiler and `agentcore.json` is the program.

Timings, because every tutorial skips them. A first deploy on a cold account took 9 minutes 49 seconds, mostly `npm install` for the CDK project (221 packages), the asset upload and the CloudFormation create. A code-only redeploy took 26 seconds, because the stack already exists and only the asset hash changes.

## The code side: an HTTP contract, not magic

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

The real file also filters every text delta through a stream sanitizer, which the last section of this article explains. Three things in this snippet are worth noticing:

- The entrypoint is an async generator. Every yielded dict becomes one server-sent event in the response stream, so streaming is the default shape of the platform, not an add-on.
- `context.session_id` is how you shard state. The runtime is serverless: each session runs in its own microVM and the platform handles scaling. Your only job is keying state by session.
- The model is a parameter. `MODEL_ID` arrives as an environment variable declared in `agentcore.json`, and a 40-line module turns it into a Strands `BedrockModel`. Changing models means changing one JSON value.

## Local and cloud: one surface

`agentcore dev` starts the same app under Uvicorn on `localhost:8080` with the same two routes. Model calls still go to Bedrock, so you need credentials but no deployment. I edited `main.py` while the server ran and watched the reloader pick the change up without a restart. The exact same prompt then worked against the deployed runtime through the data plane, because the contract does not change between the two:

```python
import boto3, json

agentcore = boto3.client("bedrock-agentcore")
resp = agentcore.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-EXAMPLE",
    payload=json.dumps({"prompt": "What is 17 plus 25? Use the tool."}).encode(),
    contentType="application/json",
)
print(resp["response"].read().decode())
```

The response is a server-sent-event stream, and the tool call is not hidden inside it:

```
contentBlockStart:  toolUse  name=add_numbers  input={"a": 17, "b": 25}
messageStop:        stopReason=tool_use      # the loop stops to run the tool
contentBlockDelta:  "17 plus 25 equals 42."  # the second message, after the tool result
```

Tool calls ride on native Bedrock `toolUse` protocol blocks, both locally and in the cloud. Nothing in AgentCore invents a new tool protocol for you to learn.

## The trace: what observability actually records

A deployed invoke produces this span tree in X-Ray. The output is real, including the token counts:

```
invoke_agent  Strands Agents                gen_ai.agent.tools=["add_numbers"], 934 tokens
├── execute_event_loop_cycle                cycle 1
│   ├── execute_tool  add_numbers           genai.span_kind=TOOL, status=success
│   └── chat  deepseek.v3.2                 BedrockRuntime ConverseStream, finish_reason=tool_use
└── execute_event_loop_cycle                cycle 2
    └── chat  deepseek.v3.2                 finish_reason=end_turn
```

The structure teaches you how the agent loop works even if you never read the framework source: one cycle per model round trip, the tool call as its own span inside the cycle, and a second cycle that consumes the tool result.

Two honest caveats come from measuring this. First, spans are asynchronous: transaction search took about ten minutes before anything was queryable, so a test that invokes and immediately greps CloudWatch will fail. Second, the local `agentcore dev` traces (OTLP files under `agentcore/.cli/traces/`) record tool calls in logs but not as spans. Only the deployed runtime emits the `execute_tool` span, which is why a smoke test that asserts on a tool span must run against the deployment.

## What broke and what it taught

Four failures are worth passing on:

- **Stale `cdk.out` fails the next deploy.** The CLI deletes `cdk.out` before each synth. Leftover state from a previous run made one synth die with `Subprocess exited with error 1`. Manually running `cdk synth` worked, which is how I knew the project itself was fine. `rm -rf agentcore/cdk/cdk.out` fixed it. Treat `cdk.out` like any build artifact: deletable at any time.
- **Renaming is destroying.** The `name` field becomes the CloudFormation logical ID. If you change it, CloudFormation does not rename anything; it deletes the old runtime and creates a new one.
- **The model leaks scaffolding into the text channel.** `deepseek.v3.2` emitted fragments of its internal chat-template markers as ordinary text, and the Nova models emitted `<thinking>` blocks. I proved this was model behavior rather than a framework bug by calling Bedrock's `converse_stream` directly with Strands removed from the picture. All four models I tried leaked something. The fix lives in the entrypoint: a stream-safe filter that holds back marker prefixes and resets once per assistant message, because one tool-using turn is several messages and a cut in one must not silence the next.
- **The region is not a flag.** Every guess at `--region` fails with `unknown option`. The targets file decides, and it fills itself in on first deploy.

## What it costs

DeepSeek V3.2 in us-east-1 costs $0.62 per million input tokens and $1.85 per million output. The two-cycle invoke in the trace above used 846 input and 82 output tokens: about $0.0007 of model calls plus roughly $0.0002 of runtime compute. The infrastructure bill for a tutorial-grade agent rounds to zero, while the engineering cost is all in reading the trace.

## Takeaways

1. **The JSON file is the interface.** Everything else (the CDK project, the template, the stack) is regenerable plumbing driven by it.
2. **CDK appears here as a vendored compiler.** You never write constructs and you never edit the generated project. Change the schema and the same code compiles a different stack.
3. **Local and deployed share one HTTP contract.** `/ping` and `/invocations` behave identically, so the code that passed locally deploys without a shim, because there is no second interface to drift away from the first.
4. **Observability is real but asynchronous.** The tool call gets its own span in the cloud. Spans need minutes to become queryable, so write your tests accordingly.

One sentence to take away: in AgentCore your infrastructure is not code you maintain. It is code that compiles.

## The setup behind the numbers

All measurements come from one real deployment: AgentCore CLI 0.31.1, Strands Agents 1.60.0, `bedrock-agentcore` 1.24.1, Python 3.13, the `deepseek.v3.2` model in us-east-1, CodeZip builds (no containers), and one hello-world agent with a single `add_numbers` tool. Deploy timings are wall-clock times on a cold account. Token counts are read from the trace spans rather than estimated.
