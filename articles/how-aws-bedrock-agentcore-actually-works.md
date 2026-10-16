---
title: "How AWS Bedrock AgentCore Actually Works"
date: 2026-10-16
draft: false
description: "A step-by-step walkthrough of AWS Bedrock AgentCore: set up the environment, scaffold a project with one command, deploy, invoke, read the trace, and see how one JSON file becomes four CloudFormation resources."
tags: ["aws", "bedrock", "agentcore", "cdk", "ai-agents"]
images: ["/images/how-aws-bedrock-agentcore-actually-works/cover.png"]
cover:
  image: "/images/how-aws-bedrock-agentcore-actually-works/cover.png"
  alt: "Cover art: How Bedrock AgentCore works. One JSON file in, four CloudFormation resources out, measured on a real deploy in us-east-1"
---

AWS Bedrock AgentCore replaces Dockerfiles, instance sizing and hand-rolled IAM with a single JSON file. One command turns that file into a running, observable endpoint. This walkthrough covers the full path from project creation to trace analysis.

![The whole AgentCore CLI lifecycle in six commands](/images/how-aws-bedrock-agentcore-actually-works/F0-command-map.png)

## What AgentCore is and is not

AgentCore is a family of managed runtimes for AI agents: nine managed services covering hosting, memory, access control, tool integration, code execution, browser automation, quality and observability. This article covers two of them: Runtime and Observability.

![AgentCore: 9 managed services, 2 used in this article](/images/how-aws-bedrock-agentcore-actually-works/F1-capability-map.png)

What it is not:

- Not a new agent framework. You still write your agent in Strands, LangChain, the OpenAI SDK or raw Python.
- Not container orchestration. Each session gets its own microVM and the platform handles scaling.
- Not a model router. Your code calls Bedrock the way it would anywhere else.

AgentCore hosts that code and adds an HTTP endpoint, an IAM role and a trace pipeline. Readers who have run ECS or Fargate will notice the difference at once: no Dockerfile, no task definition, no target group.

## Three layers, one direction

You write agent code. You write two JSON files. The CLI generates everything else. AWS runs a CloudFormation stack that you never have to look at.

![Three layers: business code, the contract, the plumbing](/images/how-aws-bedrock-agentcore-actually-works/F2-three-layers.png)

| Layer | What lives there | Who maintains it |
|---|---|---|
| Business code | `app/<AgentName>/` with the agent entrypoint | you |
| The contract | `agentcore.json` and `aws-targets.json` | you, by hand |
| The plumbing | a CDK project under `agentcore/cdk/` | the CLI, on every deploy |

The design follows one principle: declared resources live in JSON; everything the CLI generates is regenerable.

## The environment you need

Requirements:

| Tool | Version used | Notes | Check |
|---|---|---|---|
| Node.js | 24.x | 20+ required by the CLI | `node --version` |
| AgentCore CLI | 0.31.1 | install below | `agentcore --version` |
| AWS CLI | 2.x | any recent build | `aws --version` |
| uv | 0.11.9 | the CLI builds the Python environment for template agents with it | `uv --version` |
| Git | 2.39 | `create` runs `git init` in the new project | `git --version` |
| Python | 3.12 in the app venv | 3.10 to 3.14 supported by CodeZip; the runtime target is the CLI's default, not your interpreter | `python3 -V` |
| AWS account | any | with permissions below | `aws sts get-caller-identity` |
| Region | us-east-1 | the whole series uses it | `aws configure get region` |
| Docker | not needed | this series uses CodeZip builds | n/a |

Install the CLI and set the region:

```bash
npm install -g @aws/agentcore@latest
aws configure set region us-east-1
```

Self-check commands and expected output:

```bash
node --version
# v24.14.0

uv --version
# uv 0.11.9

git --version
# git version 2.39.5

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

![Terminal self-check: tool versions, AWS identity, region and model availability](/images/how-aws-bedrock-agentcore-actually-works/screenshot-1-environment-check.png)

Runtime IAM role. The CLI generates an IAM role for the runtime. The policy carries three permission groups: `bedrock:InvokeModel*`, `logs:*` for the group under `/aws/bedrock-agentcore/runtimes/`, and `xray:PutTraceSegments`. It is a least-privilege template for later.

Known issue: if `agentcore --version` errors but the command exists, an old Python package (`bedrock-agentcore-starter-toolkit`) is shadowing the npm one. `pip uninstall bedrock-agentcore-starter-toolkit` fixes it.

## Step 1 · Scaffold the project

```bash
agentcore create --name hello_agent --project-name helloagent \
  --framework Strands --model-provider Bedrock --memory none --defaults
```

```text
[done]  Create helloagent/ project directory
[done]  Prepare agentcore/ directory
[done]  Initialize git repository
[done]  Add agent to project
[done]  Set up Python environment

Created:
  helloagent/
    app/hello_agent/  Python agent (Strands)
    agentcore/        Config and CDK project

Project created successfully!

To continue, navigate to your new project:

  cd helloagent
  agentcore
```

The command produces three categories of files:

![Project tree in the editor: agentcore/ config and app/hello_agent/ code](/images/how-aws-bedrock-agentcore-actually-works/screenshot-2-directory-tree.png)

The project root gets `AGENTS.md`, `README.md` and `git init`. `agentcore/` gets the contract (`agentcore.json`), the targets file (`aws-targets.json`), `.env.local` for secrets and the vendored `cdk/` app. `app/hello_agent/` gets the agent: `main.py` (entrypoint), a `model/` package, `pyproject.toml` and helper packages (`mcp_client/`, `skills/`). The contract points `codeLocation` at `app/hello_agent/` and `entrypoint` at `main.py`; the platform zips, deploys and starts what `codeLocation` names.

Inside `agentcore/`, only `agentcore.json` and `aws-targets.json` are yours to edit; the rest is regenerated on every deploy. The CLI detects a project by walking up from the current directory until it finds a folder holding both `agentcore/` and `agentcore/agentcore.json` (missing either reports `No agentcore project found`).

Every resource array except `runtimes` starts empty, and `aws-targets.json` is `[]`. You fill both next.

## Step 2 · Write the contract: two JSON files

The deployment definition, trimmed to the fields that matter:

```json
{
  "$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
  "name": "helloagent",
  "version": 1,
  "managedBy": "CDK",
  "runtimes": [
    {
      "name": "hello_agent",
      "build": "CodeZip",
      "entrypoint": "main.py",
      "codeLocation": "app/hello_agent/",
      "runtimeVersion": "PYTHON_3_14",
      "networkMode": "PUBLIC",
      "protocol": "HTTP",
      "envVars": [{ "name": "MODEL_ID", "value": "deepseek.v3.2" }]
    }
  ],
  "memories": [],
  "knowledgeBases": [],
  "agentCoreGateways": []
}
```

`create` writes this file with every resource array empty; `agentcore add` (`add agent`, `add memory`, `add gateway`) pushes entries in.

Four fields in the runtime block cannot be wrong without a failed deploy: `entrypoint` (the file the platform calls), `codeLocation` (`app/hello_agent/`), `build` (`CodeZip`, meaning no container) and `protocol` (`HTTP`). The rest have defaults. `envVars` is how `MODEL_ID` reaches your code, so switching models is a JSON edit rather than a code change.

Check that `model/load.py` reads the model from the `MODEL_ID` environment variable rather than a hardcoded ID (the generated template sometimes defaults to a Claude model):

```python
import os
from strands.models.bedrock import BedrockModel

def load_model() -> BedrockModel:
    model_id = os.environ.get("MODEL_ID", "deepseek.v3.2")
    return BedrockModel(model_id=model_id)
```

Validate the contract before deploying:

```bash
agentcore validate
# Valid
```

The second file decides where the deployment lands:

```json
[
  { "name": "default", "account": "123456789012", "region": "us-east-1" }
]
```

`create` writes only an empty array. The first `deploy` fills it in: it calls STS, learns who you are and writes the target back into the file. There is no `--region` flag on deploy, status or remove, so the file is the only source of truth for where your agent lands.

## Step 3 · Deploy: one command, six steps

From the project root:

```bash
agentcore deploy -y --target default
```

![agentcore deploy progress and the stack outputs, including the runtime ID and ARN](/images/how-aws-bedrock-agentcore-actually-works/screenshot-3-first-deploy.png)

Between the command and the last checkmark, six things happen:

![Deploy: six steps to READY, with measured timings](/images/how-aws-bedrock-agentcore-actually-works/F4-deploy-pipeline.png)

1. Package the code. The CLI zips whatever `codeLocation` names, with platform dependencies, into one asset. A hello-world agent produces a 41 MB zip; the local `.venv` is excluded. No image is built anywhere in the project.
2. Synthesize. The vendored CDK app (`node dist/bin/cdk.js`) reads both JSON files and emits a CloudFormation template into `cdk.out/`.
3. Upload the asset. The zip lands in the S3 bucket that `cdk bootstrap` created once per account and region. Without that one-time bootstrap, no CDK deployment can store an asset.
4. Create the stack. CloudFormation provisions four resources: the runtime, an IAM role for it, a Bedrock model-access policy and a CDK metadata resource.
5. Record the state. The CLI writes `agentcore/.cli/deployed-state.json` with the runtime ARN and endpoint.
6. Print the endpoint.

The synthesis step is where schema-first becomes visible. The generated app reads your files by path and carries no project knowledge of its own:

```ts
// agentcore/cdk/bin/cdk.ts, verbatim from the generated project
async function main() {
  const configRoot = path.resolve(process.cwd(), '..');
  const configIO = new ConfigIO({ baseDir: configRoot });

  const spec = await configIO.readProjectSpec();             // agentcore.json
  const targets = await configIO.readAWSDeploymentTargets(); // aws-targets.json
  ...
}
```

The generated CDK app reads `agentcore.json` and `aws-targets.json` by path and carries no project-specific logic; it is a compiler driven entirely by the two files.

Measured timings: this deploy took 3 minutes 29 seconds. The CLI's step log says where it went: building the CDK project 25 s, synthesizing CloudFormation 1 m 3 s, creating the stack 1 m 51 s. The first deploy ever in this account took 9 minutes 49 seconds; the one-time `cdk bootstrap` and the CDK project's first `npm install` account for the difference. A code-only redeploy took 1 minute 26 seconds, because the stack already exists and only the asset hash changes. Verify with `agentcore status`, which reports `Runtime: READY` plus the endpoint URL.

## Step 4 · Run the same code locally

`agentcore dev -l` runs the same app locally on `localhost:8080`. Model calls still go to Bedrock, so credentials are needed but no deployment is. Edits to `main.py` trigger hot reload without a restart.

![agentcore dev -l boot banner: Uvicorn on localhost:8080 with the reloader watching app/hello_agent/](/images/how-aws-bedrock-agentcore-actually-works/screenshot-4-local-run.png)

## Step 5 · Invoke the deployed runtime

The deployed runtime answers through the data plane. The CLI wraps it:

```bash
agentcore invoke --prompt "What is 17 plus 25? Use the tool."
```

![agentcore invoke against the deployed runtime: the reply, the session ID and the invoke log path](/images/how-aws-bedrock-agentcore-actually-works/screenshot-5-cloud-invoke.png)

The answer is correct and the tool ran, but the reply carries model scaffolding around it: the `I'll use the addition tool` preamble and a `<|DSML|>function_calls` marker precede the final text. That is model behavior, not a platform bug; the troubleshooting section explains the fix.

![One HTTP surface, two hosts: agentcore dev and agentcore deploy](/images/how-aws-bedrock-agentcore-actually-works/F5-one-surface.png)

`agentcore dev` and the deployed runtime are two hosts for the same app: the local server on `localhost:8080`, and a managed microVM behind `https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<runtime-arn>/invocations`. Both expose the same two routes (`/ping`, `/invocations`); routing, scaling and TLS stay on the platform side, so the code is unaware which host it runs on. `agentcore invoke` is a CLI client for the hosted `/invocations`.

Cost per invoke: DeepSeek V3.2 in us-east-1 charges $0.62 per million input tokens and $1.85 per million output. A two-cycle invoke used 846 input and 82 output tokens: about $0.0007 of model calls plus $0.0002 of runtime compute. For a tutorial-grade agent, the infrastructure bill rounds to zero.

## Under the hood I: the HTTP contract

The runtime makes two requests to your code: `GET /ping` for health checks and `POST /invocations` for work. `BedrockAgentCoreApp` is a thin adapter mapping those routes onto an async generator:

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

Three design details (a production entrypoint also filters text deltas through a stream sanitizer; this demo runs without one, so the leak is visible in the invoke screenshot, see Troubleshooting):

- The entrypoint is an async generator. Every yielded dict becomes one server-sent event, so streaming is the platform's default shape, not an add-on.
- `context.session_id` is the only state key you manage. Each session runs in its own microVM; the platform handles scaling.

## Under the hood II: what observability records

A deployed invoke produces this span tree in X-Ray. The output is real, including the token counts:

```bash
agentcore traces list          # lists recent traces (2-3 min after the invoke)
agentcore traces get <trace-id>
```

![agentcore traces list and traces get: the trace for the invoke above tops the list](/images/how-aws-bedrock-agentcore-actually-works/screenshot-6-observability.png)

```text
invoke_agent Strands Agents              gen_ai.agent.tools=["add_numbers"]  tokens=902
├── execute_event_loop_cycle  (cycle 1)
│   ├── execute_tool add_numbers         gen_ai.tool.status=success  span_kind=TOOL
│   └── chat  deepseek.v3.2 (LLM, 435 tokens)
│       └── chat deepseek.v3.2 (Bedrock)   finish_reason=tool_use
└── execute_event_loop_cycle  (cycle 2)
    └── chat  deepseek.v3.2 (LLM, 467 tokens)
        └── chat deepseek.v3.2 (Bedrock)   finish_reason=end_turn
```

The structure teaches the agent loop without reading framework source: one cycle per model round trip, the tool call as its own span inside the cycle, and a second cycle that consumes the result.

Two caveats from measurement:

- Spans are asynchronous. Transaction search takes about ten minutes before anything is queryable, so a test that invokes and greps CloudWatch immediately will fail.
- Local `agentcore dev` traces record tool calls in logs but not as spans. Only the deployed runtime emits the `execute_tool` span. A smoke test that asserts on a tool span must run against the deployment.

## Cleanup

Two commands bring the whole thing down, run from the project root:

```bash
agentcore remove all -y     # empties every resource array in agentcore.json
agentcore deploy -y         # converges the stack to an empty one
agentcore status            # nothing deployed should be listed
```

`remove all` edits the JSON; it does not touch AWS on its own. The `deploy` that follows deletes the runtime, its IAM role and the stack. Two things survive on purpose: the CDK bootstrap stack (`CDKToolkit`) and its asset bucket, reused by every future deployment in that account, and the CloudWatch log group under `/aws/bedrock-agentcore/runtimes/` holding the traces. Delete those by hand if finished with the account. AgentCore bills per use, not per hour, so a deployed project left idle costs nothing.

## Troubleshooting

- Stale `cdk.out` fails the next deploy. The CLI deletes `cdk.out` before each synth, so leftover state from a previous run can kill it with `Subprocess exited with error 1`. Running `cdk synth` by hand still works, confirming the project itself is fine. `rm -rf agentcore/cdk/cdk.out` fixes it.
- Renaming is destroying. The `name` field becomes the CloudFormation logical ID. Changing it does not rename the runtime; it deletes the old one and creates a new one.
- Models leak scaffolding into the text channel. `deepseek.v3.2` emits fragments of internal chat-template markers as ordinary text (visible in the invoke screenshot); Nova models emit `<thinking>` blocks. Calling Bedrock's `converse_stream` with Strands removed proves this is model behavior, not a framework bug. The fix is a stream-safe filter in the entrypoint that holds back marker prefixes and resets once per assistant message; the official `01-features/06-observe` sample ships a reference implementation.
- The region is not a flag. Every `--region` guess fails with `unknown option`. The targets file decides.
- Model fallback to Claude triggers geographic restriction. If `MODEL_ID` is not properly loaded from the envVars, the Strands SDK defaults to a Claude model. Readers in regions where Anthropic models are unavailable see `Access to Anthropic models is not allowed from unsupported countries`. Verify `MODEL_ID` is in `agentcore.json` envVars and that `model/load.py` passes it to the `BedrockModel` constructor explicitly, not relying on the SDK default.

## Takeaways

1. The JSON file is the interface. Everything downstream (the CDK project, the template, the stack) is regenerable plumbing driven by it.
2. CDK appears as a vendored compiler. No constructs to write, no generated project to edit. Change the schema and the same code compiles a different stack.
3. Local and deployed share one HTTP contract. `/ping` and `/invocations` behave identically, so code that passed locally deploys without a shim.
4. Observability is real but asynchronous. The tool call gets its own span in the cloud and spans take minutes to become queryable. Write tests accordingly.

In AgentCore, your infrastructure is not code you maintain. It is code that compiles.
