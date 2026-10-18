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

- 一个可调用的 runtime ARN 与 endpoint URL（`agentcore status` 会打印出来）
- 一次调用的完整 trace：`invoke_agent → execute_event_loop_cycle → execute_tool add_numbers`
- 上述每一条都留在 `evidence/` 里的原生命令存档（30–45 号文件，见 §8.1）

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
| I1 | 部署独立 | `agentcore deploy -y --target default` 即可完成，不读取任何其他用例的 stack 输出 | 干净账号里跑一次这条命令 |
| I2 | 清理独立 | 所有资源带 `UseCase=01` 标签，`agentcore remove all -y` 只销毁本用例 | §8.2 的 tag 查询 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 是本例唯一的资源声明，无跨栈引用 | §8.3 的仓库级校验 `[INDEP]` |
| I4 | 代码独立 | `codeLocation`（`app/aia_uc01/`）不 import 任何其他用例 | §8.3 的仓库级校验 `[INDEP]` |
| I5 | 文档独立 | 本节以上即为全部前置**知识**，没有"必须先跑完某用例" | 通读本文 |
| I6 | **拷贝即独立** | 目录内没有任何路径指向目录之外，整份目录自包含 | §8.3 的仓库级校验 `[COPY]` |

### 2.4 「拷贝即独立」是什么意思

把这一份目录拷到任何地方，不带着仓库剩余部分，它仍然是完整可跑的工程：

```bash
cp -r usecases/01-first-agent /tmp/uc01
cd /tmp/uc01
agentcore deploy -y --target default    # 部署
agentcore status                        # runtime ARN 与 endpoint
agentcore invoke --prompt "..."         # 调一次
agentcore traces list                   # 这次调用留下的 trace
agentcore remove all -y                 # 销毁
agentcore deploy -y --target default    # 销毁后必须再跑一次，让 CLI 状态与云端对齐（见 §10）
```

目录里没有入口脚本：你敲的每一行都是 `agentcore` 或 `aws` 自己的命令。整个用例的合约就是
`agentcore/agentcore.json` 加上 `agentcore/aws-targets.json` 两个 json 文件。

这不是一句承诺，完整仓库里的系列级校验（见 §8.3）会把这个目录**当数据读一遍**，逐项验证：

1. 运行所需的文件（`AGENTS.md` / `README.md` / `agentcore/` 合约 / `app/aia_uc01/` / `tests/test_sanitize.py`）都在目录内；
2. 目录内没有任何文件指向目录之外（父目录跳转、绝对路径、仓库级共享目录、仓库级脚本）；扫路径时排除 `evidence/`、`agentcore/.cli/`、`agentcore/cdk/`；
3. 目录里没有系列禁掉的自写运维脚本（没有 `run.py`、`Makefile`，也没有 `tests/` 下的 doctor / smoke / copy_check / tag 检查）；
4. 合约自包含：`codeLocation` 落在目录内、三个标签齐全、资源名带 `aia_uc01` 命名空间。

第 2、3 条是关键：一个用例要能自证独立，靠的是目录里没有任何东西伸到目录之外，而不是自带一个
脚本去断言它自己。

> 拷贝到自己的账号后，第一件事是改 `agentcore/aws-targets.json` 里的 `account`，
> 并删掉 `agentcore/.cli/deployed-state.json`（它记的是作者那次部署的状态）。
> 凭证账号与 `aws-targets.json` 不一致时，`agentcore` 命令会直接报账号不匹配。

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
| **部署目标** | **拷来之后要先改** `agentcore/aws-targets.json` 的 `account` 为你自己的账号 | `aws sts get-caller-identity --query Account --output text`（与 json 里的 `account` 比对） |
| 区域 | **us-east-1**（本系列统一） | `aws configure get region` |
| AgentCore CLI | Node.js 20+ / `@aws/agentcore`（实测 0.31.1） | `agentcore --version` |
| 命令冲突 | 旧的 Python `agentcore` 会遮蔽 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| Python | **3.10–3.14**（CodeZip 支持范围），本例用 3.11 + `uv` | `python3 -V && uv --version` |
| 模型访问 | `deepseek.v3.2` 在 Bedrock 上可用 | `aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==\`deepseek.v3.2\`]'` |
| Docker | **本用例不需要**（CodeZip） | 不适用 |
| **其他用例** | **不需要。本用例自包含** | 不适用 |
| **仓库其余部分** | **不需要。仓库级校验会读本目录判断这一点（§8.3）** | 不适用 |

本目录不自带自检脚本，逐条用原生命令确认（都在本目录执行）：

```bash
agentcore --version                                        # 0.31.1
aws configure get region                                   # us-east-1
aws sts get-caller-identity --query Account --output text  # 与 aws-targets.json 的 account 一致
python3 -V && uv --version                                 # 3.10–3.14 / uv 可用
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?modelId==`deepseek.v3.2`]'      # 模型在本区可用
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
| 预估花费 | **≈ $0.01**（跑完 deploy → invoke → traces → remove 全流程）· 上界 **< $1** |
| 最贵的一项 | Bedrock 模型 token。这一轮实测一次调用 955 输入 + 81 输出 token（`evidence/37-trace-spans.txt`），按 `deepseek.v3.2` us-east-1 的 $0.62 / $1.85 每百万 token 计 = **$0.00074**；两个单价与算式见 `evidence/46-model-cost.txt` |
| Runtime 计算 | 按使用计费，空闲不收费。这一轮**没有单独计量**它的金额，所以表里不写数字：可核对的只有上面那笔模型费 |
| 预计耗时 | 30 min。这一轮实测：`deploy` 1 m 31 s（`evidence/31-deploy-log.txt`）、`invoke` 9 954 ms（`evidence/34-invoke-log.txt`）、拆除 1 m 40 s（`evidence/44-teardown-log.txt`） |

⚠️ 常见超支点：**忘记删**。Runtime 本身空闲不收费，但 CloudWatch 日志与 X-Ray trace 会按存储计费，日志组不设保留策略就会一直挂着。跑完记得执行 §10。

```bash
agentcore remove all -y
agentcore deploy -y --target default   # 第二条才是真正删除，见 §10
```

---

## 7. Step-by-step

> 下面所有 `agentcore` 命令都必须在**用例根目录** `usecases/01-first-agent/` 执行。
> 在 `agentcore/` 子目录里执行会直接报 `Please run this command from your project root directory.`
>
> 本目录不自带任何操作脚本：下面每一条都是 `agentcore` 或 `aws` 命令，Windows / macOS / Linux 上完全一致。

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

agentcore --version                                        # 期望 0.31.1
aws configure get region                                   # 期望 us-east-1
aws sts get-caller-identity --query Account --output text  # 期望是**你自己的账号**
python3 -V                                                 # 期望 3.10–3.14（CodeZip 支持范围）
uv --version                                               # 打包依赖时用
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?modelId==`deepseek.v3.2`]'      # 期望非空
```

**如何验证**：`get-caller-identity` 输出的是**你自己的账号 ID**，且和 `agentcore/aws-targets.json`
里的 `account` 一致；模型查询返回非空说明本区有 `deepseek.v3.2`。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `agentcore: command not found` | CLI 没装或不在 PATH | `npm install -g @aws/agentcore@latest` |
| `agentcore --version` 报错 | 旧的 Python 包遮蔽了 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| `aws: command not found` / 凭证错 | AWS CLI 或凭证没配好 | 配好 CLI，确认 `aws sts get-caller-identity` 能出账号 |
| 账号和 `aws-targets.json` 不一致 | 拷来之后没改 | 把 `account` 改成你自己的账号 |
| `python3 -V` 是 3.15+ | 超出 CodeZip 支持范围 | 用 3.10–3.14 |
| 模型查询返回空 | 本区没开通该模型 | 在 Bedrock 控制台申请，或换一个本区可用的 `MODEL_ID` |

---

### 7.2 部署

```bash
cd usecases/01-first-agent     # 或你拷贝出来的那个目录；之后所有命令都在这里
agentcore deploy -y --target default
```

> 国内网络拉不到 PyPI 官方源时，在命令前加镜像变量（否则会在打包依赖时长时间卡住）：
> ```bash
> UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple" \
> UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple" \
> agentcore deploy -y --target default
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
agentcore status
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
| `CDK synth failed: node dist/bin/cdk.js: Subprocess exited with error 1` | 上一次部署遗留的 `cdk.out` 状态陈旧（实测复现过三次，重跑即可通过） | `rm -rf agentcore/cdk/cdk.out` 后重跑 `agentcore deploy -y --target default` |
| 卡在 `Sync CDK dependencies` / `Build CDK project` 超过 15 min | 拉不到 npm / PyPI 源 | npm 走镜像；PyPI 加 `UV_DEFAULT_INDEX` 环境变量 |
| `Please run this command from your project root directory` | 在 `agentcore/` 里执行了 | 回到本目录再执行 |
| `error: unknown option '--region'` | CLI 没有 `--region`，区域只认 `agentcore/aws-targets.json` | 删掉该参数，改 `aws-targets.json` |
| 部署被拒，提示账号或凭证不对 | `aws-targets.json` 还是拷贝来源的账号 | 改成你自己的账号后重试 |

---

### 7.3 线上调用

```bash
agentcore invoke --prompt "What is 17 plus 25? Use the tool."
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
| `Runtime is not READY` | 刚部署完还在 rollout | 等 30–60 s 后 `agentcore status` 再看 |
| 回复里混进 `<｜DSML｜function_calls` | 你的 `app/aia_uc01/` 里没有输出过滤层 | 见 §9 与 `app/aia_uc01/model/sanitize.py` |
| 超时 | 冷启动 | 重试一次，冷启动通常 10–20 s |

---

### 7.4 看 trace

```bash
agentcore traces list
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

### 7.5 看断言（现在是证据，不是脚本）

这一节以前是 `make test`（跑 `tests/smoke.py`）。系列现在不这么做：断言不再是目录里的脚本，
而是**上一节那些命令的存档**。四条断言对应 `evidence/` 里的四份文件，核对方式见 §8.1，实测结果
（2026-10-18 这一轮）如下：

```text
1. runtime 存在且 READY                 evidence/32-status.txt        Deployed - Runtime: READY
2. 调用走工具、答案正确、回复干净        evidence/33-invoke.txt        "The refund total you should quote is $42."
3. 同一次调用留下 execute_tool span     evidence/37-trace-spans.txt   execute_tool add_numbers  INTERNAL  1 ms
4. 没有别的用例的资源                   evidence/38-independence.txt  三行，全是 UseCase=01
```

**如何验证**：四条都能在 `evidence/` 里被读到，且第 3 条的 span 表里必须有 `execute_tool` 那一行。
跑一遍只花一次模型钱，因为断言 2、3 共用同一次调用。

---

### 7.6 本地跑（不碰 AWS）

本地模式用一个真模型、假的 runtime，用来快速改 prompt，不产生部署。

```bash
agentcore dev -l               # 监听 http://localhost:8080/invocations
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

两类证明都不需要本目录里的任何脚本：证据是原生命令的存档，放在 `evidence/`（30–45 号文件
来自 2026-10-18 这一轮）。

```bash
agentcore status                 # runtime 存在且 READY
agentcore invoke --prompt "..."  # 调用一次：走工具、答案正确、回复干净
agentcore traces list            # 那次调用留下的 trace
agentcore traces get <trace id>  # 下载 trace，再用 jq 读出 span 树
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action
```

### 8.1 能力断言

四条断言，每条对应 `evidence/` 里的一份存档：

1. runtime 存在且 READY ⇒ `agentcore status`（`evidence/32-status.txt`）
2. 调用一次，模型**必须**走 `add_numbers`，答案正确，且回复里没有模型脚手架标记 ⇒
   `agentcore invoke`（`evidence/33-invoke.txt`，耗时见 `evidence/34-invoke-log.txt`）
3. 同一次调用留下含 `execute_tool` span 的 trace ⇒ `agentcore traces list`
   （`evidence/35-traces-list.txt`）+ `agentcore traces get`（`evidence/36-trace-get.txt`）
   + jq 读出的 span 表（`evidence/37-trace-spans.txt`）
4. 没有创建任何属于其他用例的资源（独立性，见 §8.2）

> 断言 2、3 共用**同一次**调用，所以跑一遍只花一次模型钱。

### 8.2 独立性断言

**目录层面**（本地）：仓库级校验直接读取本目录，不执行其中任何脚本，检查有没有指向目录外的
路径、有没有被系列禁掉的运维脚本、IaC 契约是否自洽且带标签。

**tag 层面**（AWS 上的实际资源）：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
# 期望：只剩 UseCase=01 的三行 —— evidence/38-independence.txt

aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=02,03,04,05,06,07 \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,uc:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
# 期望：只出现别人自己的部署，且这一轮跑完前后行数不变 —— evidence/45-independence-others.txt
```

第一条是主力证据：它**不加任何 UseCase 过滤**，把账号里所有带 `Project=agentcore-in-action`
的资源都列出来，所以只要有别的用例的资源被这一轮碰过，它就会出现在同一张列表里。2026-10-18
那次跑完，表里只有三行，全是 `UseCase=01`（`evidence/38-independence.txt`）；销毁之后同一条
命令返回零行（`evidence/43-independence-after.txt`）。

第二条只是换个角度再看一遍，写法有个坑：**一个 `Key=UseCase` 带多个值是 OR，把
`Key=UseCase` 重复六次是 AND**。一个资源不可能同时是 `UseCase=02` 和 `UseCase=03`，所以重复
写法永远返回空——它看着像通过，其实什么都没证明（`evidence/45-independence-others.txt`
记了这次实测：AND 写法零行，OR 写法有行）。

### 8.3 完整仓库里的额外一层

如果你手上是完整仓库，仓库根还有一层系列级校验（能力覆盖 / evidence/ 里有没有对应存档 /
目录自包含 / 难度单调 / 跨栈引用 / 命令是否存在），它是仓库级工具，通过读取本目录来判断：

```text
verifying docs/05-capability-map.yaml
structure: independent-usecases

[EVID] every declared deep capability is proven by a capture under evidence/

[COPY] every use case folder stands alone when it is copied out

[INDEP] (a) difficulty ladder, (b) own iac stack, (c) own source tree

[CMD] every `agentcore ...` written in a cli: field exists in the installed CLI

  PASS  uc01: all 2 deep capabilities are proven (observability <- 10-traces-list.txt, runtime <- 05-dev-local-invoke-1.txt)
  PASS  uc01: the folder stands alone (19 files read)
  PASS  difficulty sequence is non-decreasing: [1, 2, 3, 3, 4, 4, 5]
  PASS  uc01: agentcore/ is self-contained
  PASS  uc01: app/aia_uc01/ does not import another use case
  PASS  uc01: every command in cli: exists (agentcore create --framework Strands --model-provider Bedrock --build CodeZip)

6 passed, 0 warned, 0 failed
```

`[COPY]` 那一行就是 §8.2 的目录层面：它不执行本目录里的任何东西，只把目录当数据读一遍，所以
本用例既不需要自带校验脚本，也不需要和其他用例共享任何代码。
---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| `agentcore deploy` 报 `CDK synth failed: node dist/bin/cdk.js: Subprocess exited with error 1`，连着几次都一样 | CLI 只转述退出码，不把 cdk 的 stderr 打出来。2026-10-18 这次七分钟内连挂五次，中间还夹着一次 8.5 s 的部分成功，目录一个字没改 —— 这形状是干扰（多半是同一个 `agentcore/cdk` 上另有 deploy 在重写 dist），不是模板写错 | 进 `agentcore/cdk` 跑 `npx cdk synth` 看真正的报错，并确认没有第二个 `agentcore deploy` 在跑同一份目录；不要靠重试蒙过去，见 `evidence/48-deploy-synth-failures.txt` |
| 打包依赖时卡住十几分钟 | 国内拉不到 PyPI 官方源 | 见 §7.2 的 `UV_DEFAULT_INDEX` 变量 |
| `agentcore status` 报 `unknown option '--region'` | CLI 没有全局 `--region`；区域来自 `agentcore/aws-targets.json` | 删掉参数，改 json |
| 在 `agentcore/` 里执行命令报 `run this command from your project root directory` | 项目根是这个目录本身 | 上退一级 |
| 回复里出现 `<｜DSML｜function_calls` | 模型在 text 通道里额外吐了脚手架 | 见下条 |
| 回复里出现 `<thinking>...</thinking>` | 同上，换成 Nova 系模型时的表现 | 见下条 |
| 部署成功但控制台 trace 是空的 | Transaction search 索引要几分钟 | 等，或先用 `agentcore traces list` |
| 资源名报错含连字符 | AgentCore 资源名不允许 `-` | 用下划线，例如 `aia_uc01` |
| 仓库级校验报某文件「points outside the folder」 | 这个目录被人改过，混进了指向外部的路径 | 按报出的行号改回目录内相对路径 |
| tag 查询「按其他用例过滤」永远返回空 | `--tag-filters` 里重复 `Key=UseCase` 是 AND，一个资源不可能同时是两个用例 | 改成一个 `Key=UseCase` 带多个值（OR），见 §8.2 |
| `agentcore deploy` 报 `This command requires an interactive terminal` | 命令被重定向到文件或跑在 CI 里 | 加 `-y`；非交互 shell 里它是必填的 |

**关于模型输出里的脚手架标记（本用例踩到的真坑）**

实测发现：DeepSeek v3.2 会在 text 通道里额外吐出 `<｜DSML｜function_calls`，Nova 三个型号会吐出完整的 `<thinking>...</thinking>`，**绕开 Strands 用 boto3 直连 `converse_stream` 也一样**，所以这不是框架的问题，是模型/服务端行为。

本用例在 `app/aia_uc01/model/sanitize.py` 里做了一层流式安全的过滤：按 `messageStart` 为每个 assistant message 重建过滤器（一次调用其实有多个 assistant message，工具调用前后各一个），剥掉配对的 `<thinking>...</thinking>`，并从 `<｜DSML｜` 处截断。因为标记不是原子 token、流式时会跨分片到达（实测被拆成 `<` / `｜DSML｜` / `function_c` / `alls` 四片），过滤器会 hold back 可能是标记前缀的尾巴。

单元测试在 `tests/test_sanitize.py`，用真实分片形态做断言：

```bash
app/aia_uc01/.venv/bin/python tests/test_sanitize.py   # 离线，不碰 AWS
```

> 配额、区域、凭证、`agentcore` 命令冲突等跨用例的通用故障，完整仓库里另有一份汇总
> （`docs/99-troubleshooting.md`）。单独拷走本目录时不需要它。

---

## 10. Cleanup

**销毁本用例**：

```bash
agentcore remove all -y
agentcore deploy -y --target default
```

两条都要跑，第二条看着别扭：`agentcore remove all -y` 只是把资源从 `agentcore/agentcore.json`
里摘掉，**真正的删除靠随后的一次 `deploy` 把 stack 收敛到空**。在非交互 shell 里（CI、管道、
重定向到文件）`-y` 是必须的，否则会报 `This command requires an interactive terminal`。

手动核对清单（不被 CLI 纳管的残留）：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/runtimes/aiauc01_*`（CLI 不删，建议手动设保留策略或删除）
- [ ] CloudFormation stack `AgentCore-aiauc01-default` 是否真的消失
- [ ] X-Ray trace（有保留期，会自然过期）
- [ ] 本地 `agentcore/cdk/cdk.out`、`.cli/logs`（已在 `.gitignore` 中，`rm -rf agentcore/cdk/cdk.out` 可清）
- [ ] `agentcore/agentcore.json` 与 `agentcore/aws-targets.json` 都被 `remove all -y` 清空过，要再部署请先从 git 恢复这两个文件（否则 `agentcore status` 会报 `No resources match the given filters`）
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
| 输出过滤层的离线测试 `tests/test_sanitize.py` | 1 个文件 | 同上；每个用例必须能独立演进自己的输出处理，而 pytest 单元测的是本目录自己的 Python，不算运维脚本 |
| 证据存档 `evidence/`（原生命令输出的原始记录） | 每轮一份 | 共享即会破坏 I6：能力证明必须是本用例这一轮真实跑出来的 |
| 会话缓存 / 提示词提取等样板 | 约 30 行 | 同上 |

> 这些骨架由系列的用例生成器从一个基线模板**复制**进来，只写一次，然后各自演进。
> 生成器和模板本身不参与运行，所以删掉它们也不影响本目录（仓库级校验会证明这一点，见 §8.3）。
> 操作入口一节已经不在表里：系列不再让目录自带 `run.py` / `Makefile`，运维动作全是 `agentcore`
> 与 `aws` 命令，这样拷走的目录既不需要 make，也不会有两个入口互相腐烂。

---

## 12. Going further

- 延伸实验：
  1. 把 `NullConversationManager` 换成 `SlidingWindowConversationManager`，观察同一 session 第二次调用时输入 token 是否变大，这就是 UC02 要解决的问题。
  2. 再 `agentcore deploy -y --target default` 一次，让 runtime 升到 v3，然后用 `agentcore traces list` 对比两次版本的行为差异（对应附带的 `versioning-and-endpoints`）。
  3. 把 `codeLocation` 从 `app/aia_uc01/` 改成一份含 `Dockerfile` 的目录，切到 Container 构建，对比打包体积与冷启动（对应 `codezip-vs-container`）。> 改完先确认目录仍然自包含：`codeLocation` 必须在目录内，这是 I6 的硬性要求，仓库级校验会读本目录检查这一点。
- 官方文档：<https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html>
- 难度阶梯上的位置：本用例是第 1 档。下一档是 UC02 Memory（把「agent 记不住事」这件事解决掉）
- 文章版：`article.md`
