# 08 · 官方对齐设计（以 awslabs/agentcore-samples 与官方文档为准）

> 本文是**调研结论 + 重设计建议**，不是最终方案。文末列出需要拍板的决策。
> 所有事实均可复核：本节每条都给了出处（仓库路径 / AWS 文档 URL / 本机 CLI 实测输出）。

调研日期：2026-10-15
调研对象：
- `https://github.com/awslabs/agentcore-samples`（浅克隆到 `/tmp/acsamples`，commit `1094e211`）
- `https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html`
- 本机 CLI 实测：`agentcore --version` → `0.31.1`

---

## 1. 官方仓库的七层结构（以及每层的教学定位）

| 目录 | 内容 | 教学定位 |
|---|---|---|
| `00-getting-started/` | 单个 `main.py` + README，10 分钟跑通第一个 agent（CustomerSupport） | **CLI 路线**的入门：create → dev → deploy → invoke |
| `01-features/` | 8 个分组，覆盖全部能力 | **按能力深挖**；刻意用 boto3，看得到每个 API 调用 |
| `02-use-cases/` | 3 个工作负载分类 | **按业务场景**；README 有 Key Features 与 Vertical 两列 |
| `03-integrations/` | IdP、可观测平台、数据平台、UX、框架、向量库、Nova | 接第三方栈 |
| `04-infrastructure-as-code/` | `cdk/` `cloudformation/` `terraform/` | 部署自动化模板 |
| `05-blueprints/` | 5 个全栈参考应用（含 Dockerfile + 前端 + CDK） | 完整应用，不是教程 |
| `06-workshops/` | 13 个 workshop | **官方标注 deprecated**（Starter Toolkit 时代），但课程顺序仍有参考价值 |

`01-features/` 的 8 个分组（官方原文）：

```
01-harness
02-host-your-agent                       ← runtime：HTTP / MCP / A2A / AG-UI、streaming、session、async、VPC
03-connect-your-agent-to-anything        ← code interpreter / browser / web search / managed KB
04-manage-context-of-your-agent          ← memory
05-authenticate-and-authorize            ← inbound / outbound / M2M / 3LO / OBO；Cognito、Entra、Okta、PingFederate、Auth0
06-observe-evaluate-optimize-your-agent  ← observe / evaluate / optimize
07-centralize-and-govern-your-ai-infrastructure  ← gateway / policy / registry
08-agents-that-transact                  ← payments（x402 + MPP）
```

`02-use-cases/` 的 3 个分类（官方原文，与 AgentCore 文档一致的三种工作负载）：

- `01-conversational-agents`：有用户在场，实时交互，需要 per-user 会话与长期记忆
- `02-workflow-automation-agents`：无人值守，事件触发，服务间身份，记忆最少（状态在事件载荷里）
- `03-coding-assistants`：帮开发者写/跑/修代码，长任务，Code Interpreter 为主要工具

---

## 2. 官方能力清单：13 项，加 web search 就是 14 项

两处官方来源的口径**不完全一致**，这点必须写清楚，不能混用：

| 来源 | 列出的核心服务 | 数量 |
|---|---|---|
| AWS 文档 `what-is-bedrock-agentcore` | Harness, Runtime, Memory, Gateway, Identity, Code Interpreter, Browser, Observability, Payments, Evaluations, Optimization, Policy, Registry | **13**（无 Web Search） |
| samples `01-features/README.md` | runtime, memory, gateway, identity, observability, evaluations, policy, registry, payments, code interpreter, browser, web search, harness | **13**（无 Optimization） |

**并集 = 14**，与本仓库 `docs/05-capability-map.yaml` 的 14 项**一致**。所以我们的 14 项不是编的，但要补一句出处说明：13 项取自 AWS 文档核心服务表，Web Search 取自 samples 的 feature 表（官方定位是「经由 Gateway 的托管 MCP connector」）。

官方定义里几处需要修正我们现有措辞的地方：

- **Policy 的规则语言是 Dogwood**，与 Cedar 兼容。官方原文：`a policy language — Dogwood, which is compatible with Cedar (AWS's open-source policy language)`。我们文档里只写 Cedar，不准确。
- **Harness** 官方定位是「托管 agent loop，一次 API 调用定义并调用 agent」，会话跑在独立 microVM，**带文件系统与 shell**，支持自带容器镜像。它**不是**「另一个 runtime」。
- **Code Interpreter** 官方支持 Python / JavaScript / TypeScript。
- **Payments** 官方支持 x402 与 MPP 两个协议，钱包方为 Coinbase CDP 与 Stripe (Privy)。
- **Runtime** 官方协议面是 HTTP / MCP / A2A / **AG-UI** 四种。

---

## 3. 官方样例的三条硬约定

### 3.1 两类目录形态，对应两种技术路线

| | CLI 项目形态 | 脚本形态 |
|---|---|---|
| 出现在 | `00-getting-started/`、`04-infrastructure-as-code/`、`05-blueprints/` | `01-features/`、`02-use-cases/` |
| 文件 | `agentcore/`（契约 + CDK）+ `app/<AgentName>/` | `agent.py` `deploy.py` `invoke.py` `cleanup.py` `requirements.txt` `README.md` `images/` |
| 为什么 | 一条命令到线上，IaC 由 CLI 生成 | **刻意的**：`features/README.md` 原文说明用 boto3 是为了 `full visibility into every API call and parameter, which is the point of educational content` |

官方给的两条路线是**故意分开**的，不是历史包袱。它们各自的适用面写得很明确：生产迭代用 CLI，教学讲解用 boto3。

boto3 侧有两个客户端，这个区分对我们「看穿 CLI」的写法直接可用：

| 客户端 | service name | 干什么 |
|---|---|---|
| 控制面 | `bedrock-agentcore-control` | 创建/更新/删除 runtime、memory、gateway 等资源 |
| 数据面 | `bedrock-agentcore` | 调用 agent、执行命令、写 memory event |

官方还列了 6 种接口：AgentCore CLI、AgentCore Python SDK、AgentCore MCP Server、AWS SDK(boto3)、AWS CLI、Console。

### 3.2 「每个文件夹自包含，拷走就能独立跑」

`01-features/01-harness/README.md` 原文：

> Scripts are grouped first by complexity (getting started → advanced → use-cases), then by the specific feature or capability being demonstrated. **Each folder is self-contained — copy any folder and it runs independently.**

这与我们 `docs/05-capability-map.yaml` 里的独立性契约 I1–I5 是同一个主张，官方给了背书。我们的 I1–I5 可以保留，并在文档里引这一句。

### 3.3 官方样例文档的骨架

以 `02-use-cases/01-conversational-agents/deep-research-agent/README.md` 为例（标题层级实测）：

```
# <名字>
<一句话说明>
## Overview                    ← 先讲朴素做法为什么不够，再讲机制
<架构图>
| Information | Details |      ← 元信息表：Use case type / Agent type / AgentCore components /
                                   Agentic framework / LLM model / Use case vertical /
                                   Example complexity / SDK used
## When to Use This Pattern    ← 对比表：朴素做法 vs 本样例
## Example Questions
## Use Case Architecture       ← 架构图
## Features
## Tuning the Loop             ← 可调参数
## Prerequisites
### IAM permissions for ...
## Quick Start                 ← 分步命令
### 1. Install dependencies  ### 2. Run locally  ### 3. (Optional) ...
## Cleanup                     ← 必须有的收尾
## IAM Permissions             ← caller / gateway / auto-provisioning 分开写
## Files                       ← 文件表
## How It Works                ← 机制：loop、网关集成、鉴权流
## Related Resources
```

`02-use-cases/README.md` 的表格形态也值得抄：每行一个样例，列为 `Sample | Description | Vertical | Key Features`，**Key Features 列就是能力映射**。

### 3.4 官方入门样例的真实工作流

`00-getting-started/README.md` 的流程是：

```bash
agentcore create --name CustomerSupport \
  --framework Strands --model-provider Bedrock --memory none --defaults
# 5 步 done；得到 app/CustomerSupport/
# 然后把样例给的 main.py 覆盖到 app/CustomerSupport/main.py
# agentcore dev → agentcore deploy → agentcore invoke --stream
```

要点：**CLI 负责脚手架，agent 代码由你写进 `app/<AgentName>/main.py`**，这与我们上一轮改成的布局完全一致。官方样例把 CLI 钉在 `0.30.0`（我们是 `0.31.1`），前置条件是 Node 20+ / uv 0.4+ / AWS CLI 2.x / Git 2.x。

---

## 4. 本机 CLI 0.31.1 的真实命令面（实测，用来核对我们的 `cli:` 字段）

`agentcore create --help` 关键一条：

```
--defaults   Create a harness project with default settings (this is the default)
```

即**默认创建的是 harness 项目**。`--framework` 可选值为：
`Strands, LangChain_LangGraph, GoogleADK, OpenAIAgents, VercelAI, BedrockManagedAgents`；
`--protocol`：`HTTP, MCP, A2A, AGUI`；`--build`：`CodeZip, Container`。

`agentcore add` 的子命令（完整）：

```
agent  harness  memory  dataset  credential  evaluator  online-eval  online-insights
gateway  gateway-target  knowledge-base  policy-engine  policy  config-bundle
runtime-endpoint  payment-manager  payment-connector  capacity-provider  tool  skill
```

`agentcore run` 的子命令：`eval`、`batch-evaluation`、`insights`(preview)、`recommendation`、`ingest`、`ab-test`。

顶层还有：`export harness`（把 harness 导出成 `app/<agentName>/` 下的 Strands agent）、`exec`、`package`、`pause/resume/promote/stop`、`config-bundle`、`dataset`、`traces`、`logs`、`evals`、`status`、`validate`、`import`、`remove`。

### 4.1 由此发现我们计划里的两处错误

| 位置 | 我们写的 | 实际 |
|---|---|---|
| `docs/05-capability-map.yaml` uc05 `cli:` | `agentcore create --harness` | **无此参数**。harness 的正确入口是 `agentcore add harness`，或 `agentcore create`（默认就是 harness 项目），导出用 `agentcore export harness` |
| samples 根 README 示例 | `agentcore add identity` | **无此子命令**。入站鉴权走 `agentcore add agent ... --authorizer-type CUSTOM_JWT`，出站凭证走 `agentcore add credential`。（注：这条是**官方 samples 根 README 自己过时**，不是我们编的，我们不要跟） |

---

## 5. 我们与官方的偏差清单

| # | 项 | 我们现状 | 官方 | 建议 |
|---|---|---|---|---|
| 1 | agent 代码位置 | 已改为 `app/<AgentName>/` | 同 | **已对齐**（commit `5967d66`） |
| 2 | 能力清单口径 | 14 项，未标出处 | 文档 13 项 + samples 13 项，并集 14 | 保留 14，补出处说明（本文第 2 节） |
| 3 | 能力分组命名 | 自造 UC 名（First Agent / Memory / …） | 8 个官方分组名 | 每个用例头部增加 `official group` 与 `category` 标注，UC 名保留 |
| 4 | 技术路线 | 只有 CLI | CLI 与 boto3 **两条并存** | 主形态 CLI，另加 boto3 对照脚本（见 6.2） |
| 5 | 每例文件约定 | `agentcore/` + `app/` + `tests/` + README + article | CLI 项目形态一致；脚本形态另有 4 脚本约定 | 保留，补 `deploy/invoke/cleanup/status` 说明（可用 `aia.py` 承载） |
| 6 | 文档骨架 | 环境 → Step1-5 → 原理 → 故障 → takeaways → 截图位 | 官方 README 骨架（见 3.3） | A0 骨架保留；**补**元信息表、Files 表、Cleanup、Related official samples |
| 7 | 用例分类 | 难度阶梯 D1·D5 | 3 个工作负载分类 | 难度阶梯保留（这是我们的差异点），**叠加**官方分类标注 |
| 8 | Policy 措辞 | 「Cedar 策略」 | Dogwood，与 Cedar 兼容 | 改措辞 |
| 9 | 命令准确性 | uc05 有 1 处不存在的命令 | 实测清单见第 4 节 | 全量核对 `cli:` 字段并加校验 |
| 10 | 独立性主张 | 自造契约 I1·I5 | 官方原文「each folder is self-contained」 | 保留契约，引官方原句背书 |

---

## 6. 重设计建议

### 6.1 系列结构：难度阶梯 + 官方坐标

保留「7 用例 + 1 番外、难度 D1·D5」的主线（官方没有难度阶梯，这是我们的差异点），但**每个用例增加四个官方坐标字段**，写进 `docs/05-capability-map.yaml` 与每例 README 头部：

```yaml
official:
  group: 07-centralize-and-govern-your-ai-infrastructure   # 8 分组之一
  category: workflow-automation-agents                      # 3 工作负载分类之一
  vertical: Retail / E-commerce                             # 官方 use-cases 表就有一列
  samples:                                                  # 可对照的官方样例，读者能跳过去
    - 01-features/07-centralize-and-govern-your-ai-infrastructure/02-policy
    - 02-use-cases/02-workflow-automation-agents/event-driven-claims-agent
```

按当前 7 个用例，映射草案（待确认）：

| UC | 我们的标题 | 官方分组 | 工作负载分类 | 覆盖的官方能力 |
|---|---|---|---|---|
| A0 | under the hood | 02-host-your-agent | — | runtime, observability |
| UC01 | First Agent | 02-host-your-agent | conversational | runtime, observability |
| UC02 | Memory | 04-manage-context-of-your-agent | conversational | memory |
| UC03 | Gateway + Identity | 07-centralize · 05-authenticate | conversational | gateway, identity |
| UC04 | Policy | 07-centralize-and-govern | workflow-automation | policy |
| UC05 | Research Agent | 01-harness · 03-connect | conversational | harness, web search, browser, code interpreter |
| UC06 | Quality Loop | 06-observe-evaluate-optimize | — | observability, evaluations, optimization |
| UC07 | Multi-Agent + Registry | 07-centralize · 02-host | workflow-automation | runtime, registry, A2A/MCP |
| 番外 | Payments | 08-agents-that-transact | workflow-automation | payments |

覆盖检查：官方 8 分组里，我们**唯一没有专章**的是 `05-authenticate-and-authorize` 的深水区（3LO / M2M / OBO / 多 IdP），现在只作为 UC03 的一部分。这是需要决定的地方之一。

### 6.2 每个用例的骨架：CLI 为主，boto3 对照

```
usecases/NN-<slug>/
├── README.md              # 可照抄的操作文档
├── article.md             # 发表稿（英）
├── agentcore/             # CLI 契约 + 生成的 CDK（唯一真相源）
├── app/aia_ucNN/          # agent 代码，codeLocation 指向这里
├── tests/                 # 本例的能力断言
├── run.py                 # ★ 新增：目录内入口（doctor / deploy / test / down）
├── Makefile               #   只转发给 run.py，不持逻辑
├── AGENTS.md              #   本目录的 AI 助手上下文
├── raw/                   # ★ 新增：boto3 对照脚本（控制面 / 数据面各一）
│   ├── control_plane.py   #   用 boto3 读一遍 CLI 刚创建的资源（看穿 CLI）
│   └── data_plane.py      #   直接 invoke_agent_runtime，看到 SSE 原文
└── tests/                 #   smoke.py / doctor.py / copy_check.py / 独立性 helper
```

目录内不出现任何指向目录之外的路径（I6）；`tests/copy_check.py` 会真的复制一份来验证。

`raw/` 是我们相对官方的**增强**：官方 features 只用 boto3（看不到 CLI），官方 getting-started 只用 CLI（看不到 API）。我们两样都给，读者既拿到可部署产物，也拿到「CLI 到底调了什么」。

### 6.3 文章骨架：A0 定稿骨架 + 官方三块

保留 A0 已定稿的顺序（环境清单前置 → Step1·N 每步命令与实测输出 → 原理深挖 → 故障 → takeaways → 截图位清单），**吸收官方骨架里我们缺的四块**：

1. **元信息表**（官方 Information 表）：use case type / agent type / AgentCore components / framework / model / vertical / complexity / SDK used；
2. **Files 表**：每个文件一行，说明作用（官方 README 都有）；
3. **Cleanup 章节**：明确的清理命令与验证方式（我们目前只在 PLAN 里有，文章里没有）；
4. **Related official samples**：列出对应的官方样例路径与文档链接。

### 6.4 能力表 v2 要改的具体字段

- `docs/05-capability-map.yaml`：`capabilities` 每项补 `official_source`（docs / samples）；`uc05.cli` 由 `agentcore create --harness` 改为 `agentcore add harness`；`meta` 里补「14 = 文档 13 + samples 的 web-search」说明；
- `policy` 的能力名与描述改为 Dogwood（与 Cedar 兼容）；
- 新增字段 `official.group` / `official.category` / `official.vertical` / `official.samples`（见 6.1）；
- `shared/scripts/verify-coverage.py`：新增一类校验，`cli:` 里出现的每条 `agentcore ...` 子命令必须存在于本机 CLI（用 `agentcore <cmd> --help` 探测），防止再写不存在的命令。

---

## 7. 已拍板（2026-10-15）

| 决策 | 选择 | 落地情况 |
|---|---|---|
| **D1 技术路线** | **CLI 为主 + `raw/` boto3 对照** | 每个用例新增 `raw/`（控制面 + 数据面脚本），只用于教学、不参与部署；`aia.py` 生成时自动写入 `raw/README.md`；A0 正文已引用 boto3 数据面返回的 SSE 原文 |
| **D2 身份鉴权** | **并入 UC03，不单独成篇** | UC03 深挖 inbound JWT + 一种 3LO，M2M / OBO / 多 IdP 降为例内高级节；官方 `05-authenticate-and-authorize` 分组不在系列里单独占一篇 |
| **D3 篇章结构** | **保留难度阶梯，叠加官方坐标** | `docs/05-capability-map.yaml` 每个用例新增 `official.group / category / vertical / samples`；README 模板新增 §2.4 官方坐标 |
| **D4 A0 回填** | **四块全补** | A0 的英文稿与中文稿已补：元信息表、Cleanup、Files、Related official samples；中文稿小节编号已重排为十三节 + 两个附录 |

由此产生的机制改动（全部已提交）：

| 文件 | 改动 |
|---|---|
| `shared/scripts/verify-coverage.py` | 新增 `[CMD]` 校验：`cli:` 里的命令、子命令与 flag 必须在本机 CLI 里存在。判定用 `Usage:` 行，不用退出码（commander 带 `--help` 时一律返回 0，未知命令会回落打印父级帮助） |
| `shared/templates/article.template.md` | 重写为十二节，内置官方四块 |
| `shared/templates/usecase-doc.template.md` | 新增 §2.4 官方坐标，以及「主路线 CLI / 对照路线 boto3」的说明 |
| `aia.py` | 生成 `raw/README.md`；打印的能力表片段加入 `official:` 与 `cli:` 字段 |
| `docs/07-how-to-add-a-usecase.md` | 同步上述要求，并写明 CI 会拦下不存在的命令 |
| `PLAN.md` | 能力清单补出处（文档 13 项 + samples 13 项 = 并集 14）；仓库结构补 `raw/`；§8.3 文章骨架改为十二节 |

**未采纳的选项（留档）**：纯 CLI 路线；纯 boto3 路线；鉴权单独成篇；重排为官方 8 分组一一对应；A0 保持不动。

### 7.1 这一轮修正的两处事实错误

| 位置 | 错误 | 事实 |
|---|---|---|
| `docs/05-capability-map.yaml` uc05 `cli:` | `agentcore create --harness` | CLI 0.31.1 的 `create` 没有 `--harness` 参数。`--defaults` 的含义是「创建 harness 项目」，即 harness 是默认项目类型；显式入口是 `agentcore add harness`，导出是 `agentcore export harness` |
| 我们的文档若照抄官方 samples 根 README | `agentcore add identity` | `agentcore add` 没有 `identity` 子命令。入站鉴权是 `agentcore add agent --authorizer-type CUSTOM_JWT`，出站凭证是 `agentcore add credential`。这条是官方 samples 根 README 自己过时，不要跟 |

两处都已由新增的 `[CMD]` 校验兜住：把 `agentcore create --harness` 塞回去，`verify-coverage.py` 会报
`FAIL uc05: agentcore create has no --harness`（已实测）。

---

## 附：本次调研的可复核命令

```bash
# 目录树（不下载文件内容）
git clone --depth 1 --filter=blob:none --no-checkout \
  https://github.com/awslabs/agentcore-samples.git /tmp/acsamples
git ls-tree --name-only HEAD:01-features

# 读取任意官方样例
cd /tmp/acsamples && git show HEAD:00-getting-started/README.md

# 核对本机 CLI 命令面
agentcore --help ; agentcore create --help ; agentcore add --help
agentcore add harness --help ; agentcore run --help
```

官方文档：
- What is AgentCore（核心服务表 13 项）：`https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html`
- 接口一览：`https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/develop-agents.html`
- samples 仓库：`https://github.com/awslabs/agentcore-samples`
