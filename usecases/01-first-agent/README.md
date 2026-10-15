# UC01 · First Agent（把本地 agent 变成一个受管运行时）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 01 · **Difficulty**: **D1** · **Region**: `us-east-1`
> **Verified on**: 2026-10-14 · **Cost**: ≈ $0.01 跑完全流程（上界 < $1）· **Time**: 30 min（其中首次部署 10 min）
> **Capabilities**: `runtime`（深挖）· `observability`（深挖）· `harness` / `memory` / `identity` / `codezip-vs-container` / `versioning-and-endpoints`（附带）
> **Standalone**: yes。这个目录不依赖任何其他用例，也不需要仓库里的其他文件。把它拷到任何地方，它照样能跑（见 §2.4）。

> 文中的账号 ID 已脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：一个只有系统提示词、外加一个加法工具的 agent，被部署成一个受管运行时，你在命令行调用它，然后在 CloudWatch 里看到这次调用完整的一棵树，包括工具调用那一层。

跑完之后你会得到一个：

- 一个可调用的 runtime ARN 与 endpoint URL（`make status` 会打印出来）
- 一次调用的完整 trace：`invoke_agent → execute_event_loop_cycle → execute_tool add_numbers`
- 一份可重复执行的断言：`make test` 输出 `4 passed, 0 failed`

---

## 2. 独立性与难度定位

### 2.1 为什么是 D1

对照本系列共用的难度刻度尺（四维取最高维：新增能力数 / 新增外部依赖 / 必须理解的机制 / 参考耗时）：

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | 2（`runtime`、`observability`） | ≤ 2 ✅ |
| 新增外部依赖 | 无（只用账号本身与 Bedrock） | 无 ✅ |
| 必须理解的机制 | 部署模型：agent 代码跑到哪里去了、session 是什么 | 部署模型 ✅ |
| 参考耗时 | 30 min | ≤ 30 min ✅ |

**难度上升的实际含义**：这是全系列的零档。你要建立的认知只有一件事：「我的 Python 代码不再是本地进程，而是被 AgentCore 托管起来的东西」，因此它怎么被打包、怎么被调用、怎么被观测，全部要先走通一遍。后面的用例都在这条链路之上加东西。

### 2.2 前置**知识**（不是前置资源）

- 知道 LLM 的 tool use（function calling）大致是怎么回事
- 见过 Bedrock 的模型调用（知道 model id 长什么样）
- 知道 session 这个词在对话系统里指什么

> 没读过前面的用例也能做，本用例就是第一个。
> 上面这些是**概念**，不是必须存在的资源。

### 2.3 独立性声明

本用例满足六条独立性契约。每一条都能在你自己的终端里验证：

| # | 条件 | 本用例如何成立 | 怎么验证 |
|---|---|---|---|
| I1 | 部署独立 | `make deploy` 即可完成，不读取任何其他用例的 stack 输出 | 干净账号里跑一次 `make deploy` |
| I2 | 清理独立 | 所有资源带 `UseCase=01` 标签，`make down` 只销毁本用例 | §8 的 tag 查询 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 是本例唯一的资源声明，无跨栈引用 | `make check` |
| I4 | 代码独立 | `codeLocation`（`app/aia_uc01/`）不 import 任何其他用例 | `make check` |
| I5 | 文档独立 | 本节以上即为全部前置**知识**，没有"必须先跑完某用例" | 通读本文 |
| I6 | **拷贝即独立** | 目录内没有任何路径指向目录之外，整份目录自包含 | `make check`，它会真的复制一份再验证 |

### 2.4 「拷贝即独立」是什么意思

把这一份目录拷到任何地方，不带着仓库剩余部分，它仍然是完整可跑的工程：

```bash
cp -r usecases/01-first-agent /tmp/uc01
cd /tmp/uc01
python3 run.py doctor       # 自检：工具链、凭证、这个目录
python3 run.py deploy       # 部署
python3 run.py test         # 断言
python3 run.py down         # 销毁
```

目录里的入口是 `run.py`（纯标准库，macOS / Linux / Windows 表现一致）；旁边的 `Makefile` 只是转发，`make doctor` 等价于 `python3 run.py doctor`。`python3 run.py --list` 会列出全部 15 个目标。

这不是一句承诺，`python3 run.py check`（等价 `make check`）会**真的复制一份**到临时目录，逐项验证：

1. 运行所需的文件（`run.py` / `Makefile` / `AGENTS.md` / `agentcore/` 合约 / `app/aia_uc01/` / `tests/`）都在目录内；
2. 两个入口不漂移：目标名一致，每条 make 配方都转发给 `run.py`；
3. 目录内没有任何文件指向目录之外（父目录跳转、绝对路径、仓库级共享目录、仓库级脚本）；
4. 合约自包含：`codeLocation` 落在目录内、三个标签齐全、资源名带 `aia_uc01` 命名空间；
5. 复制之后文件清单一致，且副本能在自己的目录里跑通 `run.py help`、`make help` 与它自己的 `check`。

第 5 条是关键：前四条是在推理这棵树，第 5 条是造出第二棵树再看它。

> 拷贝到自己的账号后，第一件事是改 `agentcore/aws-targets.json` 里的 `account`，
> 并删掉 `agentcore/.cli/deployed-state.json`（它记的是作者那次部署的状态）。
> `python3 run.py doctor` 会在凭证账号与 `aws-targets.json` 不一致时提醒你。

### 2.5 官方坐标（对齐 awslabs/agentcore-samples）

本用例的能力在官方样例仓库里的位置，方便你对照另一种写法：

| 坐标 | 值 |
|---|---|
| 官方分组 | `02-host-your-agent` |
| 工作负载分类 | `conversational-agents`（官方按"有没有用户在环"分三类） |
| 业务垂直 | Retail / E-commerce |
| 可对照的官方样例 | `00-getting-started`（最小部署闭环）· `01-features/02-host-your-agent/01-runtime/01-hosting-agents/01-http-protocol/01-strands-bedrock`（同一条 HTTP 协议路线）· `02-use-cases/01-conversational-agents/customer-support-assistant-vpc`（VPC 形态的客服助手） |

差异点在于：官方按**能力**组织样例，本系列按**难度**组织用例，并额外要求每个用例自证独立（I1 到 I6）。官方坐标只用来定位，不改变本例的独立性。

---

## 3. 为什么需要这一层

一个 agent 在笔记本上跑通，和生产上"有个人在用"之间，隔着一整套东西：代码要打包成一个能运行的单元、要有一份别人调得动的地址、要有身份去调模型、要有日志能事后复盘。朴素做法是把 agent 包一层 FastAPI 丢到一台常开的机器上，然后你会依次遇到：谁来管这台机器、扩容怎么扩、会话怎么隔离、日志去哪了。

这个用例不解决这些问题，它解决的是**先走通一条最短的闭环**：代码从本地到受管运行时，并且这一次调用能被看见。

这一步还埋了一个本系列后面反复出现的取舍：**agent 的历史放在哪里**。本用例刻意不保留任何历史（`NullConversationManager`），把「记住」整件事留给 UC02 的 Memory。这样 UC01 的 trace 里只有模型与工具，没有记忆噪音。

---

## 4. Architecture

| 组件 | 职责 | AgentCore 托管？ |
|---|---|---|
| Agent 代码（`app/aia_uc01/main.py`） | Strands agent：系统提示词 + `add_numbers` 工具 | 否，你写的 |
| Runtime | 跑 agent 的 serverless 计算单元，每 session 一个独立 microVM | **是** |
| 模型接入 | 通过 `BedrockModel` 调 Bedrock 上的 `deepseek.v3.2` | 部分（Bedrock 托管模型） |
| 执行角色 | Runtime 用来调 Bedrock、写日志、上报 trace 的 IAM 角色 | **是**（CLI 生成） |
| 观测 | OTLP → X-Ray / CloudWatch（span、日志、指标） | **是** |

**数据流**：

```
你的命令行
  └─ agentcore invoke ──► Runtime endpoint（受管）
                            └─ microVM（你的 session 专用）
                                 ├─ Bedrock ConverseStream（deepseek.v3.2）
                                 ├─ add_numbers 工具（本地函数）
                                 └─ OTLP span ──► CloudWatch / X-Ray
```

调模型和调工具发生在受管 microVM 里；可见性来自同一进程导出的 span。

**为什么这样设计**：Runtime 是 serverless 的，**不涉及 ECS / EKS / Kubernetes**，也不需要你写 Dockerfile（本系列统一用 `CodeZip`，CLI 会把 `app/aia_uc01/` 打成一个 zip 资产）。你要负责的只有 `app/aia_uc01/` 里的 Python 与 `agentcore/agentcore.json` 里的声明。

---

## 5. Prerequisites

| 项 | 要求 | 自检命令 |
|---|---|---|
| AWS 账号 | 可创建 Bedrock AgentCore 资源 | `aws sts get-caller-identity` |
| **部署目标** | **拷来之后要先改** `agentcore/aws-targets.json` 的 `account` 为你自己的账号 | `make doctor`（账号不一致会提醒） |
| 区域 | **us-east-1**（本系列统一） | `aws configure get region` |
| AgentCore CLI | Node.js 20+ / `@aws/agentcore`（实测 0.31.1） | `agentcore --version` |
| 命令冲突 | 旧的 Python `agentcore` 会遮蔽 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| Python | **3.10–3.14**（CodeZip 支持范围），本例用 3.11 + `uv` | `python3 -V && uv --version` |
| 模型访问 | `deepseek.v3.2` 在 Bedrock 上可用 | `aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==\`deepseek.v3.2\`]'` |
| Docker | **本用例不需要**（CodeZip） | 不适用 |
| **其他用例** | **不需要。本用例自包含** | 不适用 |
| **仓库其余部分** | **不需要。`make check` 会验证这一点** | `make check` |

一键自检（在本目录执行，这条命令也是自我完备的）：

```bash
make doctor
```

### 5.1 最小权限（生产用法）

Runtime 的执行角色由 CLI 生成，实测权限如下。生产上按这个收窄，不要贴 `*`：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:CountTokens", "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:aws:bedrock:*:<你的账号>:inference-profile/*",
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogStreams", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:<你的账号>:log-group:/aws/bedrock-agentcore/runtimes/*"
    },
    {
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
      "Resource": "*"
    }
  ]
}
```

---

## 6. Cost & time

| 项 | 本用例 |
|---|---|
| 预估花费 | **≈ $0.01**（跑完 deploy → invoke → test → remove 全流程）· 上界 **< $1** |
| 最贵的一项 | Bedrock 模型 token。实测一次调用 846 输入 + 82 输出 token，按 `deepseek.v3.2` us-east-1 的 $0.62 / $1.85 每百万 token 计 ≈ **$0.0007** |
| Runtime 计算 | 一次调用约 7 秒活跃计算（$0.0895/vCPU-h + $0.00945/GB-h），量级 **$0.0002**。无请求时不收计算费 |
| 预计耗时 | 30 min。首次 `deploy` 实测 9 min 49 s（含装 CDK 依赖），之后每次 26 s |

⚠️ 常见超支点：**忘记删**。Runtime 本身空闲不收费，但 CloudWatch 日志与 X-Ray trace 会按存储计费，日志组不设保留策略就会一直挂着。跑完记得执行 §10。

```bash
make down                   # 在本目录执行，只销毁本用例
```

---

## 7. Step-by-step

> 下面所有 `agentcore` 命令都必须在**用例根目录** `usecases/01-first-agent/` 执行。
> 在 `agentcore/` 子目录里执行会直接报 `Please run this command from your project root directory.`
>
> 命令一律写成 `make <目标>`，它等价于 `python3 run.py <目标>`；没有 `make` 的环境（例如 Windows）用后者，两者行为完全一致。

### 7.0 这套目录是怎么来的（官方布局）

本用例**完全沿用 CLI 官方布局**，没有自造目录。项目由官方完整形态生成：

```bash
agentcore create --name aia_uc01 --project-name aiauc01 \
  --framework Strands --model-provider Bedrock --memory none --defaults
```

`create` 一次写三样东西：项目根的 `AGENTS.md` / `README.md` 并执行 `git init`；`agentcore/`（契约 + 生成的 CDK 工程）；`app/aia_uc01/`（Strands starter agent，含 `main.py`、`model/load.py`、`mcp_client/`、`skills/`、`pyproject.toml`，并用 uv 建好 `.venv`）。

`agentcore.json` 的 `codeLocation` 指向 `app/aia_uc01/`，**这个目录就是被打包、部署、`agentcore dev` 启动的东西**，`entrypoint: main.py` 相对它解析。你要改的只有三处：`agentcore/agentcore.json`、`agentcore/aws-targets.json` 和 `app/aia_uc01/` 里的 Python。starter 自带的 `main.py` 已经是对的形状（`BedrockAgentCoreApp` + `@app.entrypoint` 异步生成器 + 一个 `@tool` 例子），本用例把它替换成下面 §4 里那份带输出过滤层的实现。

> 已经有一份 agent 代码不想搬？官方另给了一条 BYO 入口：
> `agentcore add agent --type byo --code-location <目录> --entrypoint <文件>`，
> 把 `codeLocation` 指到任何已有目录即可。本系列不用这条，读者按官方默认路径走。

### 7.1 自检环境

```bash
cd usecases/01-first-agent     # 或你拷贝出来的那个目录
make doctor
```

**预期输出**

```text
doctor · use case 01 · /path/to/01-first-agent

toolchain
  PASS  python 3.11.9 (inside the CodeZip 3.10 to 3.14 range)
  PASS  node v22.22.2
  PASS  aws cli aws-cli/2.15.6
  PASS  uv 0.11.9 (builds the app environment)

agentcore cli
  PASS  agentcore 0.31.1

this folder
  PASS  codeLocation 'app/aia_uc01' exists
  PASS  app environment present at app/aia_uc01/.venv
  PASS  run.py present
  PASS  Makefile present
  PASS  AGENTS.md present
  PASS  tests/smoke.py present
  PASS  tests/copy_check.py present

aws environment
  PASS  credentials work, account 123456789012
  PASS  region is us-east-1
  PASS  model deepseek.v3.2 is available in us-east-1

15 passed, 0 warned, 0 failed
next: make deploy
```

**如何验证**：最后必须是 `0 failed`；`credentials work` 后面是**你自己的账号 ID**；`this folder` 一段的七行全 PASS 说明目录自包含。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `FAIL  agentcore not found` | CLI 没装或不在 PATH | `npm install -g @aws/agentcore@latest` |
| `agentcore exists but --version fails` | 旧的 Python 包遮蔽了 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| `FAIL  codeLocation 'app/aia_uc01' is missing` | 目录不完整 | 重新拷贝，或检查 `agentcore/agentcore.json` |
| `FAIL  Makefile is missing` | 你拷贝的是不完全的一份 | 重新拷贝整个目录 |
| `FAIL  python 3.15.x` | 超出 CodeZip 支持范围 | 用 3.11 或 3.13 |
| `WARN  credentials are for account ...` | `aws-targets.json` 还是作者的账号 | 改成你自己的账号 |

---

### 7.2 部署

```bash
cd usecases/01-first-agent     # 或你拷贝出来的那个目录；之后所有命令都在这里
make deploy                    # 等于 agentcore deploy -y --target default
```

> 国内网络拉不到 PyPI 官方源时，在命令前加镜像变量（否则会在打包依赖时长时间卡住）：
> ```bash
> UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple" \
> UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple" \
> make deploy
> ```

**预期输出**

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

**如何验证**

```bash
make status
```

```text
AgentCore Status (target: default, us-east-1)

Agents
  aia_uc01: Deployed - Runtime: READY (arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-LH8zQV86C2)
  URL: https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws%3A...%2Finvocations
```

看到 `Runtime: READY` 即可。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `CDK synth failed: node dist/bin/cdk.js: Subprocess exited with error 1` | 上一次部署遗留的 `cdk.out` 状态陈旧（实测复现过两次） | `make clean` 后重跑 `make deploy` |
| 卡在 `Sync CDK dependencies` / `Build CDK project` 超过 15 min | 拉不到 npm / PyPI 源 | npm 走镜像；PyPI 加 `UV_DEFAULT_INDEX` 环境变量 |
| `Please run this command from your project root directory` | 在 `agentcore/` 里执行了 | 回到本目录再执行 |
| `error: unknown option '--region'` | CLI 没有 `--region`，区域只认 `agentcore/aws-targets.json` | 删掉该参数，改 `aws-targets.json` |
| 部署被拒，提示账号或凭证不对 | `aws-targets.json` 还是拷贝来源的账号 | 改成你自己的账号后重试 |

---

### 7.3 线上调用

```bash
make invoke PROMPT="What is 17 plus 25? Use the tool."
```

**预期输出**

```text
I'll use the addition tool to calculate the sum of 17 and 25.

17 plus 25 equals 42.

Session: 53451706-bd56-43f3-84ef-1eceaa3c2aee
To resume: agentcore invoke --session-id 53451706-bd56-43f3-84ef-1eceaa3c2aee
Log: .../agentcore/.cli/logs/invoke/invoke-aia_uc01-20261014-153601.log
```

**如何验证**：两个条件同时满足：回复里出现 `42`，且**没有**任何 `<｜DSML｜...` 或 `<thinking>` 之类的标记。

命令行只给你拼好的文本。想看底层到底发生了什么（工具真的被调了吗？），直接读 SSE：

```bash
curl -s -X POST http://localhost:8080/invocations -H 'Content-Type: application/json' \
  -d '{"prompt":"What is 11 plus 31? Use the tool."}'
```

（这是本地 dev server 的用法，见 §7.6。）线上一次调用的原始事件流长这样：

```text
data: {"event": {"contentBlockDelta": {"delta": {"text": "I'll calculate 11 plus 31 using the tool for you.\n\n"}, "contentBlockIndex": 0}}}
data: {"event": {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "tooluse_V8T0pNRzrKLCyUR7wmvlVd", "name": "add_numbers"}}, "contentBlockIndex": 1}}}
data: {"event": {"contentBlockDelta": {"delta": {"toolUse": {"input": "{\"a\": 11, \"b\": 31}"}}, "contentBlockIndex": 1}}}
data: {"event": {"messageStop": {"stopReason": "tool_use"}}}
data: {"event": {"messageStart": {"role": "assistant"}}}
data: {"event": {"contentBlockDelta": {"delta": {"text": "11 plus 31 equals 42."}, "contentBlockIndex": 0}}}
data: {"event": {"messageStop": {"stopReason": "end_turn"}}}
data: {"event": {"metadata": {"usage": {"inputTokens": 471, "outputTokens": 9, "totalTokens": 480}, "metrics": {"latencyMs": 820}}}}
```

关键点：工具调用走的是 Bedrock **原生 `toolUse` 协议块**，不是模型自己编的文本；`stopReason: tool_use` 之后模型带着工具结果**又跑了一轮**（所以有两条 `metadata`，两次计费）。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `Runtime is not READY` | 刚部署完还在 rollout | 等 30–60 s 后 `make status` 再看 |
| 回复里混进 `<｜DSML｜function_calls` | 你的 `app/aia_uc01/` 里没有输出过滤层 | 见 §9 与 `app/aia_uc01/model/sanitize.py` |
| 超时 | 冷启动 | 重试一次，冷启动通常 10–20 s |

---

### 7.4 看 trace

```bash
make traces
```

**预期输出**

```text
Traces for aia_uc01 (target: default)

Trace ID                     Timestamp          Session ID
6acf31f23c3645fd06e78ad839b6 2026-10-14         fcb13797-2338-4f0f-9a55-d9957f44e5
59e8                         07:40:43Z          e5f3
6acf320...                   ...                ...

Console: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#/gen-ai-observability/...
Note: Traces may take 2-3 minutes to appear in CloudWatch
```

**如何验证**：把 trace 下载下来，看 span 树里有没有工具那一层。

```bash
agentcore traces get 6acf31f23c3645fd06e78ad839b659e8
```

```text
Trace saved to:
.../01-first-agent/agentcore/.cli/traces/aia_uc01-6acf31f23c3645fd06e78ad839b659e8.json
Console: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#/gen-ai-observability/...
```

把 JSON 里的 span 树摊平，实测线上是：

```text
invoke_agent Strands Agents              gen_ai.agent.tools=["add_numbers"]  tokens=934
├── execute_event_loop_cycle  (cycle 1)
│   ├── execute_tool add_numbers         gen_ai.tool.status=success  span_kind=TOOL
│   │                                    gen_ai.tool.call.id=tooluse_XcG6rmdIgGQ6yYOiQKTDzo
│   └── chat  deepseek.v3.2 (LLM, 451 tokens)
│       └── BedrockRuntime ConverseStream   finish_reason=tool_use
└── execute_event_loop_cycle  (cycle 2)
    └── chat  deepseek.v3.2 (LLM, 483 tokens)
        └── BedrockRuntime ConverseStream   finish_reason=end_turn
```

这是本用例的核心证据：**工具调用是 trace 里的一等公民，不是只能从最终文本里猜**。

> 注意一个差异：`agentcore dev`（本地）产出的 trace **没有**独立 tool span，`toolUse` 只出现在日志记录里；线上才有 `execute_tool` span。§7.6 会再用本地模式看效果，两者不要混。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| 列表是空的 | Transaction search 还在索引（提示 2–3 min，首次可能更久） | 等几分钟再执行 |
| `traces get` 报权限错 | 缺 `xray:BatchGetTraces` / CloudWatch 读权限 | 补权限或直接在控制台看 |
| 只有 HTTP span，没有 `invoke_agent` | 请求根本没到 agent（例如打错了端口） | 确认 URL / endpoint 正确 |

---

### 7.5 跑断言

```bash
make test                      # 等于 python3 tests/smoke.py --usecase 01
```

**预期输出**

```text
runtime
       aiauc01_aia_uc01 v2 · arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-LH8zQV86C2
  PASS assert_runtime_1: the runtime exists in the target region and reports status READY
       session fcb13797-2338-4f0f-9a55-d9957f44e5f3 · 14 events · tools ['add_numbers']
       reply "I'll use the addition tool to calculate 21 + 21.\n\n21 plus 21 equals 42."
  PASS assert_runtime_2: invoking it answers a tool-using prompt and the reply has no model scaffolding

observability
       trace 1-6acf31f2-3c3645fd06e78ad839b659e8 · span 'execute_tool add_numbers'
  PASS assert_observability_1: that same invoke left an X-Ray trace whose span tree contains an execute_tool span

  PASS independence: no other use case's resources present

4 passed, 0 failed
```

**如何验证**：最后一行必须是 `4 passed, 0 failed`，退出码为 0。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `no runtime named aiauc01_*` | 还没部署，或部署到了别的区 | 先跑 §7.2 |
| `the agent answered without calling add_numbers` | 模型没选工具（偶发） | 重跑一次；连续复现再查系统提示词 |
| `no X-Ray trace containing an execute_tool span ... within 150s` | 索引延迟或 Transaction search 未开 | 等几分钟重跑；确认该区已启用 transaction search |
| `no usable AWS credentials` | 凭证过期 | 重新登录后再跑 |
| `no virtualenv at app/aia_uc01/.venv` | 拷贝出来之后没建过环境 | `make sync` |

---

### 7.6 本地跑（不碰 AWS）

本地模式用一个真模型、假的 runtime，用来快速改 prompt，不产生部署。

```bash
make dev                       # 监听 http://localhost:8080/invocations
```

另开一个终端：

```bash
curl -s -X POST http://localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What is 128 plus 256? Use the tool."}'
```

**如何验证**：返回的 SSE 里能看到 `toolUse: add_numbers`，以及第二轮的 `384`。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `Please run this command from your project root` | 在 `agentcore/` 里执行 | 回到本目录 |
| 端口被占 | 上一个 dev server 没退 | `lsof -tnP -iTCP:8080 -sTCP:LISTEN \| xargs kill` |
| 改动没生效 | 热重载没触发 | 重启 dev server |

---

## 8. Verify

两类断言，都在本目录执行（`make X` 与 `python3 run.py X` 等价）：

```bash
make test      # 能力断言：对着已部署的 runtime 跑（§7.5）
make check     # 独立性断言：这个目录能不能被单独拷走
make verify    # 上面两条依次跑
```

### 8.1 能力断言（`make test`）

核心断言：

1. runtime 存在且 READY ⇒ 对应能力 `runtime`
2. 调用一次，模型**必须**走 `add_numbers`，答案正确，且回复里没有模型脚手架标记
3. 同一次调用在 X-Ray 里留下一棵含 `execute_tool` span 的树 ⇒ 对应能力 `observability`
4. 没有创建任何属于其他用例的资源（独立性）

> 断言 2、3 共用**同一次**调用，所以跑一遍 `make test` 只花一次模型钱。

### 8.2 独立性断言（`make check`）

**期望输出**

```text
copy_check: .../01-first-agent
use case 01 · nested run: False

[1] every file this use case needs is in the folder
  PASS  all 13 required files present
  PASS  no leftover directories from an older layout
  PASS  app/aia_uc01/uv.lock present, so the dependency graph is pinned

[2] the in-folder entry points agree
  PASS  both entry points expose the same 15 targets
  PASS  every make recipe forwards to run.py, so only one implementation exists

[3] nothing points outside the folder
  PASS  the folder: 36 files scanned, none points outside the folder

[4] the IaC contract is self-contained and tagged
  PASS  project tags present: Project=agentcore-in-action, UseCase=01, AutoDelete=true
  PASS  codeLocation 'app/aia_uc01' resolves inside this folder
  PASS  deployment target: us-east-1 (target default)
  PASS  names are namespaced to this use case: aiauc01 / aia_uc01

[5] the folder survives a real copy
  PASS  copied to /var/folders/.../aia-copy-xxxx/01-first-agent
  PASS  the copy carries all 36 files, and nothing extra
  PASS  the copy: 36 files scanned, none points outside the folder
  PASS  `run.py help` runs inside the copy
  PASS  `make help` runs inside the copy and forwards to run.py
  PASS  the copy passes its own copy_check

16 passed, 0 failed
```

**如何验证**：最后一行必须是 `0 failed`。第 5 段是关键：它真的把这棵目录复制到临时目录，再对副本重跑一遍全部检查。

第 2 段值得单独说一句：目录里有**两个**入口，`run.py`（真身，macOS / Linux / Windows 都能跑）和 `Makefile`（只是转发）。两个入口各写一套实现是这类骨架最常见的腐烂方式，所以这里用断言把它们钉在一起：目标名必须一致，每条 make 配方必须转发给 `run.py`。

**tag 层面的独立性**（`make check` 查的是本地声明，这一条查的是 AWS 上的实际资源）：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=02,03,04,05,06,07
# 期望：ResourceTagMappingList 为空，证明本用例没有顺手创建别人的资源
```

### 8.3 完整仓库里的额外一层

如果你手上是完整仓库，仓库根还有一条 `aia verify 01`，会在 `make test` 之上再跑一层的系列级校验（能力覆盖 / 目录自包含 / 难度单调 / 跨栈引用 / 命令是否存在）：

```text
[EVID] every declared deep capability is asserted in smoke.py

[COPY] every use case folder stands alone when it is copied out

[INDEP] (a) difficulty ladder, (b) own iac stack, (c) own source tree

[CMD] every `agentcore ...` written in a cli: field exists in the installed CLI

  PASS  uc01: all 2 deep capabilities are asserted
  PASS  uc01: the folder stands alone (16 passed, 0 failed)
  PASS  difficulty sequence is non-decreasing: [1, 2, 3, 3, 4, 4, 5]
  PASS  uc01: agentcore/ is self-contained
  PASS  uc01: app/aia_uc01/ does not import another use case
  PASS  uc01: every command in cli: exists (agentcore create --framework Strands --model-provider Bedrock --build CodeZip)

6 passed, 0 warned, 0 failed
```

`[COPY]` 那一行就是 §8.2：仓库级校验并不重新实现拷贝检查，它只是**调用**本用例自带的
`tests/copy_check.py`。所以每个用例既能在自己的目录里自证，也不需要和其他用例共享任何代码。

---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| `CDK synth failed: ... Subprocess exited with error 1`，手动 `cdk synth` 却只是长时间挂住 | `agentcore/cdk/cdk.out` 是上一次部署的陈旧状态 | `make clean`，重跑 `make deploy` |
| 打包依赖时卡住十几分钟 | 国内拉不到 PyPI 官方源 | 见 §7.2 的 `UV_DEFAULT_INDEX` 变量 |
| `agentcore status` 报 `unknown option '--region'` | CLI 没有全局 `--region`；区域来自 `agentcore/aws-targets.json` | 删掉参数，改 json |
| 在 `agentcore/` 里执行命令报 `run this command from your project root directory` | 项目根是这个目录本身 | 上退一级 |
| 回复里出现 `<｜DSML｜function_calls` | 模型在 text 通道里额外吐了脚手架 | 见下条 |
| 回复里出现 `<thinking>...</thinking>` | 同上，换成 Nova 系模型时的表现 | 见下条 |
| 部署成功但控制台 trace 是空的 | Transaction search 索引要几分钟 | 等，或先用 `make traces` |
| 资源名报错含连字符 | AgentCore 资源名不允许 `-` | 用下划线，例如 `aia_uc01` |
| `make check` 报某文件「points outside the folder」 | 这个目录被人改过，混进了指向外部的路径 | 按报出的行号改回目录内相对路径 |

**关于模型输出里的脚手架标记（本用例踩到的真坑）**

实测发现：DeepSeek v3.2 会在 text 通道里额外吐出 `<｜DSML｜function_calls`，Nova 三个型号会吐出完整的 `<thinking>...</thinking>`，**绕开 Strands 用 boto3 直连 `converse_stream` 也一样**，所以这不是框架的问题，是模型/服务端行为。

本用例在 `app/aia_uc01/model/sanitize.py` 里做了一层流式安全的过滤：按 `messageStart` 为每个 assistant message 重建过滤器（一次调用其实有多个 assistant message，工具调用前后各一个），剥掉配对的 `<thinking>...</thinking>`，并从 `<｜DSML｜` 处截断。因为标记不是原子 token、流式时会跨分片到达（实测被拆成 `<` / `｜DSML｜` / `function_c` / `alls` 四片），过滤器会 hold back 可能是标记前缀的尾巴。

单元测试在 `tests/test_sanitize.py`，用真实分片形态做断言：

```bash
make unit                     # 等于 app/aia_uc01/.venv/bin/python tests/test_sanitize.py
```

> 配额、区域、凭证、`agentcore` 命令冲突等跨用例的通用故障，完整仓库里另有一份汇总
> （`docs/99-troubleshooting.md`）。单独拷走本目录时不需要它。

---

## 10. Cleanup

**销毁本用例**：

```bash
make down
```

`make down` 展开成两条命令 `agentcore remove all` 再 `agentcore deploy -y --target default`。第二条看着别扭：`agentcore remove all` 只是把资源从 `agentcore/agentcore.json` 里摘掉，**真正的删除靠随后的一次 `deploy` 把 stack 收敛到空**。

手动核对清单（不被 CLI 纳管的残留）：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/runtimes/aiauc01_*`（CLI 不删，建议手动设保留策略或删除）
- [ ] CloudFormation stack `AgentCore-aiauc01-default` 是否真的消失
- [ ] X-Ray trace（有保留期，会自然过期）
- [ ] 本地 `agentcore/cdk/cdk.out`、`.cli/logs`（已在 `.gitignore` 中，`make clean` 可清）
- [ ] `agentcore/agentcore.json` 被 `remove all` 改写过，要再部署请先恢复它
- [ ] 本用例没有 S3 桶、没有 Secrets Manager 条目

**确认清空，且没有波及别的用例**：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=01
# 期望：ResourceTagMappingList 为空，且任何其他 UseCase 的资源数量不变
```

---

## 11. What you repeated（为独立而内嵌的基线）

本用例是自包含的，因此内嵌了以下本可以共享的东西。如实列出，避免你误以为这是一个微服务仓库的最佳实践。

| 内嵌内容 | 规模 | 为什么不能共享 |
|---|---|---|
| 最小 agent 骨架 `app/aia_uc01/main.py` + `app/aia_uc01/model/` | 4 个文件 | 共享即会破坏 I4（代码独立） |
| 输出过滤层 `app/aia_uc01/model/sanitize.py` | 1 个文件 | 同上；每个用例必须能独立演进自己的输出处理 |
| IaC 声明 `agentcore/agentcore.json` + `aws-targets.json` + `agentcore/cdk/` | 3 个文件 + 生成的 CDK 工程 | 共享即会破坏 I3（栈独立） |
| 冒烟测试骨架 `tests/smoke.py` + `resourcegroupstaggingapi_check.py` | 2 个文件 | 共享即会破坏 I4；独立性断言必须每个用例自带 |
| 自包含操作入口 `run.py` + `Makefile` + `tests/doctor.py` + `tests/copy_check.py` + `AGENTS.md` | 5 个文件 | 共享即会破坏 I6（拷贝即独立）：入口一旦在目录外，目录就不能单独拷走 |
| 会话缓存 / 提示词提取等样板 | 约 30 行 | 同上 |

> 这些骨架由系列的用例生成器从一个基线模板**复制**进来，只写一次，然后各自演进。
> 生成器和模板本身不参与运行，所以删掉它们也不影响本目录（`make check` 会证明这一点）。

---

## 12. Going further

- 延伸实验：
  1. 把 `NullConversationManager` 换成 `SlidingWindowConversationManager`，观察同一 session 第二次调用时输入 token 是否变大，这就是 UC02 要解决的问题。
  2. 再 `make deploy` 一次，让 runtime 升到 v3，然后用 `make traces` 对比两次版本的行为差异（对应附带的 `versioning-and-endpoints`）。
  3. 把 `codeLocation` 从 `app/aia_uc01/` 改成一份含 `Dockerfile` 的目录，切到 Container 构建，对比打包体积与冷启动（对应 `codezip-vs-container`）。改完先跑 `make check`：`codeLocation` 仍然必须在目录内，这是 I6 的硬性要求。
- 官方文档：<https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html>
- 难度阶梯上的位置：本用例是第 1 档。下一档是 UC02 Memory（把「agent 记不住事」这件事解决掉）
- 文章版：`article.md`
