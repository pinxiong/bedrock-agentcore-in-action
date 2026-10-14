# UC01 · First Agent（把本地 agent 变成一个受管运行时）

> **Series**: [AgentCore in Action](../../README.md) · **Use case**: 01 · **Difficulty**: **D1** · **Region**: `us-east-1`
> **Verified on**: 2026-10-14 · **Cost**: ≈ $0.01 跑完全流程（上界 < $1）· **Time**: 30 min（其中首次部署 10 min）
> **Capabilities**: `runtime`（深挖）· `observability`（深挖）· `harness` / `memory` / `identity` / `codezip-vs-container` / `versioning-and-endpoints`（附带）
> **Standalone**: yes. This use case does not require any other use case to be deployed.

---

## 1. 本用例结束时你会看到什么

一句话：一个只有系统提示词、外加一个加法工具的 agent，被部署成一个受管运行时，你在命令行调用它，然后在 CloudWatch 里看到这次调用完整的一棵树，包括工具调用那一层。

跑完之后你会得到一个：

- 一个可调用的 runtime ARN 与 endpoint URL（`agentcore status` 会打印出来）
- 一次调用的完整 trace：`invoke_agent → execute_event_loop_cycle → execute_tool add_numbers`
- 一份可重复执行的断言：`python aia.py test 01` 输出 `4 passed, 0 failed`

---

## 2. 独立性与难度定位

### 2.1 为什么是 D1

对照 [难度刻度尺](../../docs/06-difficulty-ladder.md)：

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | 2（`runtime`、`observability`） | ≤ 2 ✅ |
| 新增外部依赖 | 无（只用账号本身与 Bedrock） | 无 ✅ |
| 必须理解的机制 | 部署模型：agent 代码跑到哪里去了、session 是什么 | 部署模型 ✅ |
| 参考耗时 | 30 min | ≤ 30 min ✅ |

**难度上升的实际含义**：这是全系列的零档。你要建立的认知只有一件事——「我的 Python 代码不再是本地进程，而是被 AgentCore 托管起来的东西」，因此它怎么被打包、怎么被调用、怎么被观测，全部要先走通一遍。后面的用例都在这条链路之上加东西。

### 2.2 前置**知识**（不是前置资源）

- 知道 LLM 的 tool use（function calling）大致是怎么回事
- 见过 Bedrock 的模型调用（知道 model id 长什么样）
- 知道 session 这个词在对话系统里指什么

> 没读过前面的用例也能做，本用例就是第一个。
> 上面这些是**概念**，不是必须存在的资源。

### 2.3 独立性声明

本用例满足五条独立性契约（见 [README](../../README.md#the-independence-contract)）：

| # | 条件 | 本用例如何成立 |
|---|---|---|
| I1 | 部署独立 | `python aia.py up 01`（仓库根执行）即可完成，不读取任何其他用例的 stack 输出 |
| I2 | 清理独立 | 所有资源带 `UseCase=01` 标签，`python aia.py down 01` 只销毁本用例 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 是本例唯一的资源声明，各例独立合成栈，无跨栈引用 |
| I4 | 代码独立 | `src/` 不 import 任何其他用例 |
| I5 | 文档独立 | 本节以上即为全部前置 |

---

## 3. 为什么需要这一层

一个 agent 在笔记本上跑通，和生产上"有个人在用"之间，隔着一整套东西：代码要打包成一个能运行的单元、要有一份别人调得动的地址、要有身份去调模型、要有日志能事后复盘。朴素做法是把 agent 包一层 FastAPI 丢到一台常开的机器上——然后你会依次遇到：谁来管这台机器、扩容怎么扩、会话怎么隔离、日志去哪了。

这个用例不解决这些问题，它解决的是**先走通一条最短的闭环**：代码从本地到受管运行时，并且这一次调用能被看见。

这一步还埋了一个本系列后面反复出现的取舍：**agent 的历史放在哪里**。本用例刻意不保留任何历史（`NullConversationManager`），把「记住」整件事留给 UC02 的 Memory。这样 UC01 的 trace 里只有模型与工具，没有记忆噪音。

---

## 4. Architecture

| 组件 | 职责 | AgentCore 托管？ |
|---|---|---|
| Agent 代码（`src/main.py`） | Strands agent：系统提示词 + `add_numbers` 工具 | 否，你写的 |
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

**为什么这样设计**：Runtime 是 serverless 的，**不涉及 ECS / EKS / Kubernetes**，也不需要你写 Dockerfile（本系列统一用 `CodeZip`，CLI 会把 `src/` 打成一个 zip 资产）。你要负责的只有 `src/` 里的 Python 与 `agentcore/agentcore.json` 里的声明。

---

## 5. Prerequisites

| 项 | 要求 | 自检命令 |
|---|---|---|
| AWS 账号 | 可创建 Bedrock AgentCore 资源 | `aws sts get-caller-identity` |
| 区域 | **us-east-1**（本系列统一） | `aws configure get region` |
| AgentCore CLI | Node.js 20+ / `@aws/agentcore`（实测 0.31.1） | `agentcore --version` |
| 命令冲突 | 旧的 Python `agentcore` 会遮蔽 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| Python | **3.10–3.13**（CodeZip 支持范围），本例用 3.11 + `uv` | `python3 -V && uv --version` |
| 模型访问 | `deepseek.v3.2` 在 Bedrock 上可用 | `aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==\`deepseek.v3.2\`]'` |
| Docker | **本用例不需要**（CodeZip） | 不适用 |
| **其他用例** | **不需要。本用例自包含** | 不适用 |

一键自检：

```bash
python aia.py doctor --usecase 01
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
python aia.py down 01      # 在仓库根执行
```

---

## 7. Step-by-step

> 下面所有 `agentcore` 命令都必须在**用例根目录** `usecases/01-first-agent/` 执行。
> 在 `agentcore/` 子目录里执行会直接报 `Please run this command from your project root directory.`

### 7.1 自检环境

```bash
cd /path/to/bedrock-agentcore-in-action
python aia.py doctor --usecase 01
```

**预期输出**

```text
AgentCore in Action: environment check

toolchain
  PASS  aws cli aws-cli/2.15.6
  PASS  node v22.22.2
  PASS  python 3.11.9 (inside the CodeZip 3.10 to 3.13 range)
  PASS  pyyaml available (needed by aia list/new and verify-coverage.py)

agentcore cli
  PASS  agentcore 0.31.1

aws environment
  PASS  credentials work, account 123456789012
  PASS  region is us-east-1
  PASS  model deepseek.v3.2 is available

use case 01 extra requirements

all checks passed
```

**如何验证**：最后一行必须是 `all checks passed`，且 `credentials work` 后面是**你自己的账号 ID**。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `FAIL  agentcore ... not found` | CLI 没装或不在 PATH | `npm install -g @aws/agentcore@latest` |
| `agentcore --version` 报错但命令存在 | 旧的 Python 包遮蔽了 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| `FAIL  region is ...` | 默认区不是 us-east-1 | `aws configure set region us-east-1` |
| `FAIL  python 3.14.x` | CodeZip 只支持 3.10–3.13 | 用 3.11 或 3.13 |

---

### 7.2 部署

```bash
cd usecases/01-first-agent
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
| `CDK synth failed: node dist/bin/cdk.js: Subprocess exited with error 1` | 上一次部署遗留的 `cdk.out` 状态陈旧（实测复现过两次） | `rm -rf agentcore/cdk/cdk.out` 后重跑 deploy |
| 卡在 `Sync CDK dependencies` / `Build CDK project` 超过 15 min | 拉不到 npm / PyPI 源 | npm 走镜像；PyPI 加 `UV_DEFAULT_INDEX` 环境变量 |
| `Please run this command from your project root directory` | 在 `agentcore/` 里执行了 | `cd usecases/01-first-agent` 再执行 |
| `error: unknown option '--region'` | CLI 没有 `--region`，区域只认 `agentcore/aws-targets.json` | 删掉该参数，改 `aws-targets.json` |

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

**如何验证**：两个条件同时满足——回复里出现 `42`，且**没有**任何 `<｜DSML｜...` 或 `<thinking>` 之类的标记。

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
| 回复里混进 `<｜DSML｜function_calls` | 你的 `src/` 里没有输出过滤层 | 见 §9 与 `src/model/sanitize.py` |
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
.../usecases/01-first-agent/agentcore/.cli/traces/aia_uc01-6acf31f23c3645fd06e78ad839b659e8.json
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
cd ../..                       # 回到仓库根
python aia.py test 01
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

---

### 7.6 本地跑（不碰 AWS）

本地模式用一个真模型、假的 runtime——用来快速改 prompt，不产生部署。

```bash
cd usecases/01-first-agent
agentcore dev -l          # 监听 http://localhost:8080/invocations
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
| `Please run this command from your project root` | 在 `agentcore/` 里执行 | `cd usecases/01-first-agent` |
| 端口被占 | 上一个 dev server 没退 | `lsof -tnP -iTCP:8080 -sTCP:LISTEN \| xargs kill` |
| 改动没生效 | 热重载没触发 | 重启 dev server |

---

## 8. Verify

```bash
python aia.py test 01       # 等价于 python tests/smoke.py --usecase 01
python aia.py verify 01     # test + 覆盖 + 独立性三类校验
```

**期望输出**（`verify 01` 的尾部）

```text
[EVID] every declared deep capability is asserted in smoke.py

[INDEP] (a) difficulty ladder, (b) own iac stack, (c) own source tree

  PASS  uc01: all 2 deep capabilities are asserted
  PASS  difficulty sequence is non-decreasing: [1, 2, 3, 3, 4, 4, 5]
  PASS  uc01: agentcore/ is self-contained
  PASS  uc01: src/ does not import another use case

4 passed, 0 warned, 0 failed
```

核心断言：

1. runtime 存在且 READY ⇒ `docs/05-capability-map.yaml` 的 `usecases[uc01].deep` 含 `runtime`
2. 调用一次，模型**必须**走 `add_numbers`，答案正确，且回复里没有模型脚手架标记
3. 同一次调用在 X-Ray 里留下一棵含 `execute_tool` span 的树 ⇒ 对应 `observability`
4. 没有创建任何属于其他用例的资源（独立性）

> 断言 2、3 共用**同一次**调用，所以跑一遍 `test` 只花一次模型钱。

**独立性断言**（每个用例都有，最后一条）：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=02,03,04,05,06,07
# 期望：ResourceTagMappingList 为空，证明本用例没有顺手创建别人的资源
```

---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| `CDK synth failed: ... Subprocess exited with error 1`，手动 `cdk synth` 却只是长时间挂住 | `agentcore/cdk/cdk.out` 是上一次部署的陈旧状态 | `rm -rf agentcore/cdk/cdk.out`，重跑 deploy |
| 打包依赖时卡住十几分钟 | 国内拉不到 PyPI 官方源 | 见 §7.2 的 `UV_DEFAULT_INDEX` 变量 |
| `agentcore status` 报 `unknown option '--region'` | CLI 没有全局 `--region`；区域来自 `agentcore/aws-targets.json` | 删掉参数，改 json |
| 在 `agentcore/` 里执行命令报 `run this command from your project root directory` | 项目根是 `usecases/01-first-agent/` | 上退一级 |
| 回复里出现 `<｜DSML｜function_calls` | 模型在 text 通道里额外吐了脚手架 | 见下条 |
| 回复里出现 `<thinking>...</thinking>` | 同上，换成 Nova 系模型时的表现 | 见下条 |
| 部署成功但控制台 trace 是空的 | Transaction search 索引要几分钟 | 等，或先用 `agentcore traces list` |
| 资源名报错含连字符 | AgentCore 资源名不允许 `-` | 用下划线，例如 `aia_uc01` |

**关于模型输出里的脚手架标记（本用例踩到的真坑）**

实测发现：DeepSeek v3.2 会在 text 通道里额外吐出 `<｜DSML｜function_calls`，Nova 三个型号会吐出完整的 `<thinking>...</thinking>`——**绕开 Strands 用 boto3 直连 `converse_stream` 也一样**，所以这不是框架的问题，是模型/服务端行为。

本用例在 `src/model/sanitize.py` 里做了一层流式安全的过滤：按 `messageStart` 为每个 assistant message 重建过滤器（一次调用其实有多个 assistant message，工具调用前后各一个），剥掉配对的 `<thinking>...</thinking>`，并从 `<｜DSML｜` 处截断。因为标记不是原子 token、流式时会跨分片到达（实测被拆成 `<` / `｜DSML｜` / `function_c` / `alls` 四片），过滤器会 hold back 可能是标记前缀的尾巴。

单元测试在 `tests/test_sanitize.py`，用真实分片形态做断言：

```bash
cd usecases/01-first-agent && src/.venv/bin/python tests/test_sanitize.py
```

> 通用故障（配额、区域、凭证、`agentcore` 命令冲突）见 [`docs/99-troubleshooting.md`](../../docs/99-troubleshooting.md)。

---

## 10. Cleanup

**销毁本用例**：

```bash
python aia.py down 01
# 或
cd usecases/01-first-agent && agentcore remove all && agentcore deploy
```

第二条命令看着别扭：`agentcore remove all` 只是把资源从 `agentcore/agentcore.json` 里摘掉，**真正的删除靠随后的一次 `deploy` 把 stack 收敛到空**。

手动核对清单（不被 CLI 纳管的残留）：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/runtimes/aiauc01_*`（CLI 不删，建议手动设保留策略或删除）
- [ ] CloudFormation stack `AgentCore-aiauc01-default` 是否真的消失
- [ ] X-Ray trace（有保留期，会自然过期）
- [ ] 本地 `agentcore/cdk/cdk.out`、`.cli/logs`（已在 `.gitignore` 中，可随时删）
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
| 最小 agent 骨架 `src/main.py` + `src/model/` | 4 个文件 | 共享即会破坏 I4（代码独立） |
| 输出过滤层 `src/model/sanitize.py` | 1 个文件 | 同上；每个用例必须能独立演进自己的输出处理 |
| IaC 声明 `agentcore/agentcore.json` + `aws-targets.json` | 2 个文件 | 共享即会破坏 I3（栈独立） |
| 冒烟测试骨架 `tests/smoke.py` + `resourcegroupstaggingapi_check.py` | 2 个文件 | 共享即会破坏 I4；独立性断言必须每个用例自带 |
| 会话缓存 / 提示词提取等样板 | 约 30 行 | 同上 |

> 这些骨架由 `python aia.py new` 从 `shared/templates/baseline-agent/`
> 生成而来，只写一次，然后各自演进。

---

## 12. Going further

- 延伸实验：
  1. 把 `NullConversationManager` 换成 `SlidingWindowConversationManager`，观察同一 session 第二次调用时输入 token 是否变大——这就是 UC02 要解决的问题。
  2. 再 `agentcore deploy` 一次，让 runtime 升到 v3，然后用 `agentcore traces list` 对比两次版本的行为差异（对应附带的 `versioning-and-endpoints`）。
  3. 把 `codeLocation` 从 `src/` 改成一份含 `Dockerfile` 的目录，切到 Container 构建，对比打包体积与冷启动（对应 `codezip-vs-container`）。
- 官方文档：<https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html>
- 难度阶梯上的位置：本用例是第 1 档。下一档是 UC02 Memory（把「agent 记不住事」这件事解决掉）
- 文章版：`article.md`
