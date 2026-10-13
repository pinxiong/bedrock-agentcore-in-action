# AgentCore in Action: the landscape

A short orientation before you open the first use case. Verified on 2026-10-13.

## What AgentCore is

Amazon Bedrock AgentCore is the set of managed services around an agent, as
opposed to the model inside it. Bedrock gives you the model; AgentCore gives you
everything an agent needs in order to be a service: a runtime, memory, a way to
reach enterprise systems, a way to restrict what it may do, tools, evaluation,
optimization, payments and a catalog.

Fourteen capabilities, all generally available as of October 2026:

| Group | Capabilities |
|---|---|
| Run it | Runtime, Harness |
| Give it state | Memory |
| Give it reach | Gateway, Identity, Browser, Code Interpreter, Web Search, Skills |
| Keep it inside the lines | Policy |
| Know whether it works | Observability, Evaluations, Optimization |
| Operate at scale | Registry, Payments |

## Two decisions that shape everything

**How you build the agent.** There are two peer paths, not a beginner and an
advanced one:

| Path | You write | Choose it when |
|---|---|---|
| Managed harness | a configuration: model, prompt, tools, memory | you want an agent loop without maintaining one |
| Code-based agent | a Python loop with Strands, LangGraph, Google ADK or the OpenAI Agents SDK | you need control over orchestration |

**How you ship it.** Two packaging types:

| | `CodeZip` (default) | `Container` |
|---|---|---|
| Docker needed locally | no | yes, to build the image only |
| Size ceiling | 250 MB | 2 GB |
| Languages | Python 3.10 to 3.13 | many |
| New sessions per second | 25 | 1.6 |
| Artifact lives in | S3 | your ECR |

Every use case in this repository uses `CodeZip`, so no Docker is required.

## You do not need ECS, EKS or Kubernetes

This is the question the series gets asked most, so it is answered in the
repository's front page as well.

| What you would operate yourself | What AgentCore does instead |
|---|---|
| ECS or EKS cluster, node groups, capacity provider | nothing to run |
| Session affinity and sticky routing | session isolation, one microVM per session |
| Autoscaling policy, cold start tuning | managed |
| Image registry, base image patching | language runtime patched for you on the CodeZip path |
| Load balancer, TLS, health checks | managed endpoint and ARN per agent version |
| Local credential files, per-call token refresh | Identity brokers outbound credentials; the agent never holds them |

Runtime is serverless. Each session gets its own isolated microVM. The optional
feature for choosing an EC2 instance type selects the instance behind the
managed runtime; it does not put the instance in your account to operate.

## Where AgentCore stops and your work begins

AgentCore is not an opinion about your architecture. It hosts the agent and
supplies the primitives, and you still own:

- the agent's logic and prompts
- the semantics of your tools and their backends
- the rules in your policies, expressed as Cedar or in natural language
- your evaluation datasets and the definition of "good"
- the decision of when a workflow deserves an agent at all

If a use case in this repository looks like more work than you expected, that is
usually the honest part rather than the part AgentCore should have absorbed.

## Region and naming notes

- The series targets **`us-east-1`**. Registry is available in only five regions
  and Web Search requires `us-east-1`, so a single region keeps every use case
  runnable.
- **Registry moved namespaces.** It is `agent-registry`, with the ARN prefix
  `arn:aws:agent-registry` and the managed policy `AgentRegistryFullAccess`. The
  legacy `bedrock-agentcore` registry namespace shut down on 2026-09-17. Guides
  written before that date will lead you into an error.
- If you ever installed the `bedrock-agentcore-starter-toolkit` Python package,
  its `agentcore` command shadows the npm CLI. `python aia.py doctor`
  checks for this.

## Next steps

1. Run `python aia.py doctor` once.
2. Open [`usecases/01-first-agent/`](../usecases/01-first-agent/) and deploy it.
3. Read [`docs/06-difficulty-ladder.md`](06-difficulty-ladder.md) to see where the
   series is heading, and [`PLAN.md`](../PLAN.md) for how it was designed.
