# AgentCore in Action

**Seven independent use cases. Ordered by difficulty. All 14 Amazon Bedrock AgentCore capabilities.**

Every use case in this repository stands on its own: its own agent, its own IaC stack,
its own cleanup. You can deploy UC05 without ever deploying UC01. Read them in order and
they form a difficulty ladder from "deploy an agent" to "isolate a fleet of agents"; jump
into any one and you still get a project that runs from zero.

> **Verified on 2026-10-13** · Everything targets **`us-east-1`** · AgentCore evolves
> fast, so check each capability's "GA since" column before assuming behaviour.

---

## How this differs from a pile of samples

The obvious way to cover a big service is to write one sample per feature. That produces
nine disconnected islands with no answer to "where do I start?". The other obvious way is
a single project you grow stage by stage, tagged with git. That produces a fake
independence: `git checkout stage-04` still carries everything stages 01 to 03 installed.

This repo takes the third option: **independent use cases, arranged as a ladder.**

| Pile of samples (rejected) | Chained stages (rejected) | Independent ladder (this repo) |
|---|---|---|
| 9 directories, no order | 1 project, `git checkout stage-04` | 7 directories, difficulty D1 to D5 |
| No answer to "start where?" | Independence is only a tag | Independence is a directory and a stack |
| Can't tell what's hard | Stage 4 needs stages 1 to 3 deployed | Any subset, any order, any time |
| Duplication is accidental | Duplication is inherited | Duplication is deliberate and documented |

---

## The independence contract

A use case in this repo is called independent only if all six of these hold. Each is
checkable, and the last two run in CI.

| | Condition | How you can verify it |
|---|---|---|
| **I1** | Deploys alone | `python aia.py up 05` succeeds in a clean account where UC01 to UC04 were never deployed |
| **I2** | Cleans up alone | `python aia.py down 05` zeroes its cost and touches no other use case |
| **I3** | Own IaC stack | No cross-stack references, no shared state, no reading another use case's outputs |
| **I4** | Own source tree | the directory each use case deploys (`codeLocation`, i.e. `usecases/NN-*/app/aia_ucNN/`) never imports another use case |
| **I5** | Own documentation | The README starts from zero and lists only *knowledge* prerequisites, never "you must deploy UC0X first" |
| **I6** | **Survives a copy** | no path inside `usecases/05-*` leaves the folder, and the folder ships no operational script |

```bash
# The independence test, for any use case
python aia.py up 05 && python aia.py status 05 && python aia.py down 05

# The strongest form: list everything the project owns and read the UseCase
# column. Anything this run touched shows up in the same table.
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,uc:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
# Expected: only UseCase=05 rows.

# To narrow it: one filter, several values. `--tag-filters` is AND across
# filters and OR within one filter's Values, so `Key=UseCase,Values=01
# Key=UseCase,Values=02` asks for one resource that is two use cases at once.
# It matches nothing and returns empty, which reads exactly like a pass.
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=01,02,03,04,06,07
# Expected: ResourceTagMappingList is empty
```

Every resource carries a `UseCase=NN` tag so that last assertion is possible.
**Independence is asserted, not claimed.**

### Copy any folder, and it still runs

Each use case folder is a complete project on its own. Everything it needs to run
is inside it, so the repository around it is convenience, not a dependency:

```bash
cp -r usecases/01-first-agent /tmp/uc01
cd /tmp/uc01
agentcore deploy -y --target default      # deploy it
agentcore status                          # what is deployed
agentcore invoke --prompt "..."           # call it
agentcore remove all -y                   # empty the contract ...
agentcore deploy -y --target default      # ... and this reconciles the stack down
```

There is no `run.py` and no `Makefile` in a use case folder: the series teaches
the AgentCore CLI, so every command the reader runs is `agentcore ...` or
`aws ...`, and a wrapper would be one more thing to learn and one more thing that
can drift (`docs/09-article-spec.md` section 8). A capability is proven by the
captured output of a native command, saved under `usecases/NN-*/evidence/`, not
by an assertion script.

That claim is checked, not just written: the repository-level check reads every
use case folder and fails when a path inside it leaves the folder, when its
contract is not tagged, or when it ships an operational script. Before this
existed, "copy any folder and it runs independently" was a sentence in this
README. Now a use case that breaks it fails CI.

### What independence costs, stated plainly

Independent use cases must each carry a runnable baseline agent, which means some
duplication. Every use case README has a section called *What you repeated* that lists
exactly what it re-embeds, so you always know whether you are looking at a
self-contained example or a shared service. The baseline is generated from
`shared/templates/baseline-agent/` by `python aia.py new`, so the duplicate
is authored once. Every folder also carries its own `AGENTS.md`, and that is the
price of I6. What this repo deliberately does **not** do is factor
the baseline into a shared library that use cases import: that would recouple I3 and I4
and take us straight back to chained stages.

---

## The difficulty ladder

Difficulty is a declared number from 1 to 5, not a feeling. The rubric is public in
[`docs/06-difficulty-ladder.md`](docs/06-difficulty-ladder.md), and CI fails if the
sequence stops being non-decreasing.

| Level | What you must understand to finish | New capabilities | External dependencies | Roughly |
|:--:|---|---|---|---|
| **D1** | Where the agent runs, and what a session is | 1 to 2 | none beyond Bedrock | 30 min |
| **D2** | What the agent remembers, and per whom | 1 to 2 | one stateful AWS resource | 1 h |
| **D3** | What it is allowed to do, and who vouches for it | 2 to 3 | an identity system or third-party API | 2 to 2.5 h |
| **D4** | Whether it is doing the job well | 3 to 5 | several services plus async or streaming | 3 to 4 h |
| **D5** | How it coexists with other agents | 5 or more | multiple agents plus org-level governance | 4 h |

---

## The seven use cases (+ 1 branch)

| # | Use case | Level | What it adds | Capabilities | Time | Cost |
|---|---|:--:|---|---|---|---|
| 01 | [First Agent](usecases/01-first-agent/) | **D1** | a deployable agent | Runtime, Observability, CodeZip | 30 min | < $1 |
| 02 | [Memory](usecases/02-memory/) | **D2** | it remembers | Memory | 1 h | < $2 |
| 03 | [Gateway + Identity](usecases/03-gateway-identity/) | **D3** | reaches enterprise systems | Gateway, Identity, VPC/PrivateLink | 2.5 h | < $5 |
| 04 | [Policy](usecases/04-policy/) | **D3** | hard boundaries | Policy, inline_function (HITL) | 2 h | < $3 |
| 05 | [Research Agent](usecases/05-research-agent/) | **D4** | web, browser, compute | Harness, Web Search, Browser, Code Interpreter, Skills | 3 h | < $8 |
| 06 | [Quality Loop](usecases/06-quality-loop/) | **D4** | a measurable quality loop | Observability (deep), Evaluations, Optimization | 4 h | < $15 |
| 07 | [Multi-Agent + Registry](usecases/07-multi-agent-registry/) | **D5** | more agents, and a catalog | Runtime advanced (A2A, MCP hosting, streaming, AG-UI, EC2 types), Registry | 4 h | < $12 |
| Bonus | [Payments](bonus/payments/) | D3 | a wallet | Payments | 2 h | ~$2 |

Working through all of it is roughly 19 hours and about $50. The ladder order matters
because it is the intended reading order, not because each step needs the previous one
installed.

---

## The 14 capabilities

| # | Capability | What it does | GA since | Deep dive in |
|---|---|---|---|---|
| 1 | [Harness](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html) | Managed agent loop behind two API calls | 2026-06 | UC05 |
| 2 | [Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html) | Serverless agent/tool runtime with session isolation | 2025-10 | UC01, UC07 |
| 3 | [Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html) | Short-term + long-term memory strategies | 2025-10 | UC02 |
| 4 | [Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html) | APIs, Lambda and MCP servers to MCP tools | 2025-10 | UC03 |
| 5 | [Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html) | Inbound auth and outbound credential brokering | 2025-10 | UC03 |
| 6 | [Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html) | Intercepts tool calls; Cedar / natural language | 2026-03 | UC04 |
| 7 | [Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html) | Sandboxed Python / JS / TS execution | 2025-10 | UC05 |
| 8 | [Browser](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html) | Managed cloud browser (CDP, Playwright) | 2025-10 | UC05 |
| 9 | [Web Search](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html) | Managed web index, MCP compatible | 2026-06 | UC05 |
| 10 | [Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) | CloudWatch GenAI Observability, OTel-compatible | 2025-10 | UC01, UC06 |
| 11 | [Evaluations](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html) | 13 built-in evaluators + custom LLM-as-judge | 2026-03 | UC06 |
| 12 | [Optimization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/optimization.html) | Trace-driven recommendations, batch eval, A/B tests | 2026-06 | UC06 |
| 13 | [Payments](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/payments.html) | x402 / MPP micropayments with spending limits | 2026-08 | Bonus |
| 14 | [Registry](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html) | Governed catalog for agents, tools, skills | 2026-08 | UC07 |

### Coverage

`●` deep dive　`○` used

| Capability | 01 | 02 | 03 | 04 | 05 | 06 | 07 | Bonus |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Harness | ○ | | | | ● | ○ | ○ | |
| Runtime | ● | ○ | ○ | ○ | | ○ | ● | ○ |
| Memory | ○ | ● | | | ○ | | ○ | |
| Gateway | | | ● | ○ | ○ | ○ | | ○ |
| Identity | ○ | ○ | ● | | | | | ○ |
| Policy | | | | ● | | | | ○ |
| Code Interpreter | | | | | ● | | ○ | |
| Browser | | | | | ● | | | |
| Web Search | | | | | ● | | | |
| Observability | ● | ○ | ○ | ○ | ○ | ● | ○ | ○ |
| Evaluations | | ○ | | | ○ | ● | | |
| Optimization | | | | | | ● | | |
| Payments | | | | | | | | ● |
| Registry | | | | | | | ● | |
| **Difficulty** | D1 | D2 | D3 | D3 | D4 | D4 | D5 | D3 |

All 14 capabilities are deep-dived at least once, and the difficulty sequence is
non-decreasing. Coverage is enforced, not claimed:
[`shared/scripts/verify-coverage.py`](shared/scripts/verify-coverage.py) reads
[`docs/05-capability-map.yaml`](docs/05-capability-map.yaml) and fails CI if a use case
declares a capability that no capture under `evidence/` proves, if the difficulty
sequence regresses, or if a use case reaches into another one's stack or source tree.

---

## You do not need ECS

A fair question, because most agent-hosting guides start with a cluster. AgentCore
Runtime is serverless: each session runs in its own isolated microVM, and you manage no
cluster, no nodes, no autoscaling group, no load balancer.

```bash
agentcore create --framework Strands --model-provider Bedrock --build CodeZip
agentcore deploy
```

`CodeZip` is the default build type and **requires no Docker**. It packages your code as
a zip, uploads it to S3, and AgentCore runs it. Pick `Container` only when you need
packages over 250 MB, non-Python runtimes, or your own image pipeline, and even then the
image runs inside AgentCore rather than on a cluster you operate. The only local
requirement for that path is a Docker daemon to *build* the image.

The "ECS" mention in early drafts of this plan was a counterfactual: the list of things
you would have to build yourself if AgentCore did not exist, not a deployment target.
Full comparison in [`docs/00-overview.md`](docs/00-overview.md).

---

## Quick start

```bash
git clone https://github.com/<you>/bedrock-agentcore-in-action.git
cd bedrock-agentcore-in-action
pip install pyyaml                     # or: uv pip install pyyaml
python aia.py doctor                   # checks CLI, Node, Python, region, model access, command shadowing

python aia.py check 01                 # does that folder stand on its own?
python aia.py up 01 && python aia.py status 01 && python aia.py down 01
```

Then pick any other use case. Order is suggested, not required. Once you are
inside a use case folder, every command is an `agentcore` or `aws` command:
`agentcore status`, `agentcore invoke --prompt "..."`, `agentcore traces list`.

## Repository layout

```
usecases/       7 self-contained use cases, each with app, agentcore, evidence, tests, README and article
bonus/payments/ the standalone payments branch
docs/           series-wide guides, the machine-readable capability map, the difficulty rubric
shared/         scripts and templates, including the use case generator and the baseline agent
PLAN.md         how the series was designed
```

Each `usecases/NN-*/` folder is a project root, not a package inside a project: it
holds its own `AGENTS.md`, `agentcore/` contract, `app/` and `evidence/`, and nothing
in it points at a path outside itself.

## Conventions

- **Region**: `us-east-1` everywhere.
- **Build type**: `CodeZip` (no Docker). Container is discussed, not required.
- **Tags**: every resource carries `Project=agentcore-in-action`, `UseCase=0X`, `AutoDelete=true`.
- **Boundaries**: no cross-use-case imports, no cross-stack references, and no path
  inside a use case points outside it.
- **Framework**: Python 3.11 with Strands Agents; UC03 and UC07 also ship a LangGraph variant.
- **No secrets in the repo**: `.env.example` holds placeholders only; `gitleaks` runs in CI.
- **Two levels of tooling**: `python aia.py <cmd>` is the repository-level dispatcher for
  work that spans use cases; everything a reader does inside one use case is an
  `agentcore` or `aws` command. There is no in-folder entry-point script, because a
  wrapper is one more thing to learn and one more thing that can drift.
- **Native commands only**: the article and the README show `agentcore ...` and
  `aws ...`. No `make <target>`, no `python3 run.py <target>`.
- **Evidence**: a capability is claimed only when `usecases/NN-*/evidence/` holds the
  capture of the native command that proves it.

## Adding a use case

```bash
python aia.py new 08-your-idea --difficulty 5
```

This scaffolds a working baseline (the agent under `app/`, the `agentcore/` contract,
`AGENTS.md` and an empty `evidence/`), a README from the twelve-section template, and
then tells you what to fill in. See
[`docs/07-how-to-add-a-usecase.md`](docs/07-how-to-add-a-usecase.md). New use cases must
declare their capabilities and difficulty in `docs/05-capability-map.yaml` and pass the
CI checks, one of which is `python aia.py check 08`.

## License

MIT-0. See [LICENSE](LICENSE).
