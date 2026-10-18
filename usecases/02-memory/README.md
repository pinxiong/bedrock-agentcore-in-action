# UC02 · Memory（短期记忆与跨会话长期记忆）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 02 · **Difficulty**: **D2** · **Region**: `us-east-1`
> **Verified on**: 2026-10-18 · **Cost**: 全程 ≈ $0.02 的模型调用 + 一天的 memory 存储（上界 < $2）· **Time**: 60 min（其中部署 4 m 20 s，等情节抽取 16 m 30 s）
> **Capabilities**: `memory`（深挖）· `runtime` / `identity`（附带）
> **Standalone**: yes。目录不依赖任何其他用例，也不需要仓库里的其他文件；拷到任何地方照样能跑（见 §2.3）。

> 文中的账号 ID 已脱敏为 `123456789012`；真实输出里出现的是你自己的账号。
> 本用例目录里没有任何自己写的操作脚本，每一步都是一条 `agentcore` 或 `aws` 命令。

---

## 1. 本用例结束时你会看到什么

一句话：一个上周说过「只要华南区」的补货助手，在这周的全新 session 里不再问第二遍。

跑完之后你会得到：

- 一个 runtime 与一个 memory（`agentcore status` 会把两个都列出来）
- 一次跨会话回忆：session 1 只说了偏好，session 2 四分钟后按偏好下单
- 一次隔离证明：两位店长在同一分钟问同一个问题，各自只拿到自己的区域
- 一次情节回忆：一条失败补货记录被检索找回来，然后在回答里主动说出来
- 一条 independence 查询：账号里只有打着 `UseCase=02` 的四行资源

---

## 2. 独立性与难度定位

### 2.1 为什么是 D2

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | 1（`memory` 深挖，`runtime` 复用） | ≤ 2 ✅ |
| 新增外部依赖 | 1 个有状态 AWS 资源（AgentCore Memory） | 1 个 ✅ |
| 必须理解的机制 | 状态、检索、隔离三个轴：什么进短期、什么进长期、谁看不见谁 | ✅ |
| 参考耗时 | 60 min（其中约 17 min 在等异步抽取） | ≤ 60 min ✅ |

**难度上升的实际含义**：UC01 里 agent 是无状态的，invoke 结束即归零。本用例第一次让状态活过 invoke，于是三个新问题必须回答：写进去的东西什么时候变得可读（异步抽取）、读回来的东西怎么进 prompt（检索结果拼进 system prompt）、两个人怎么不串（actor id 进 namespace）。

### 2.2 前置**知识**（不是前置资源）

- 知道 AgentCore 的一次 invoke 属于某个 `runtimeSessionId`
- 知道 namespace 是带前缀的路径，不是数据库表

不需要先跑过 UC01。两篇的目录结构相同只是同源，代码不互相 import。

### 2.3 独立性声明

- 本目录**不 import** 任何其他用例，也不读其他用例的 stack outputs
- 本目录的 `agentcore/agentcore.json` 只声明自己的 runtime 与 memory
- 独立性由仓库级工具用原生命令核对：目录内没有指向目录外的路径、合约自包含、CDK 产物里没有跨栈引用
- 所有资源带 `Project=agentcore-in-action`、`UseCase=02`、`AutoDelete=true` 三个 tag，§9 的清理断言靠它们
- independence 要求账号里没有其他用例的资源。**跑之前请确认其他用例已经拆除**，否则它失败得理直气壮

### 2.4 官方坐标（对齐 awslabs/agentcore-samples）

- `01-features/04-manage-context-of-your-agent/memory`
- `02-use-cases/01-conversational-agents/episodic-memory-claims-agent`

两者都强调「短期是 event、长期是 strategy 抽出来的 record」，本用例的 `app/aia_uc02/memory.py` 就是这条分界线。

---

## 3. 为什么需要这一层

补货助手的第一版只会看着系统提示词回答。于是每周一，店长都要重新说一遍「我只要某个区」。

把这句话塞进 prompt 缓存不解决问题：换一个店长就串了，隔一周就过期了，而且没人说得清它存在哪。AgentCore Memory 把这件事拆成两个可以分别验证的动作：

- **写**：`CreateEvent`，一次 invoke 一条，键是 `(actorId, sessionId)`，30 天后过期
- **读**：`RetrieveMemoryRecords`，按 namespace 检索抽取出来的 record

关键在于「写」和「可读」之间隔着一个异步抽取。这个间隔是本用例最容易被低估的部分，也是唯一需要「等」的地方：偏好 2 到 4 分钟可读，情节 16 分半可读。

---

## 4. Architecture

```text
agentcore invoke --user-id <actor>
   └─► Runtime aia_uc02 ──converse──► Bedrock deepseek.v3.2
            │
            ├── RetrieveMemoryRecords（进 system prompt，先读后答）
            ▼
   Memory aia_uc02_mem
       /users/{actorId}/preferences    USER_PREFERENCE
       /users/{actorId}/facts          SEMANTIC
       /episodes/{actorId}/{sessionId} EPISODIC
            ▲
            └── CreateEvent（回答之后写，一次一轮）
```

一次 invoke 的顺序是固定的：

1. 解析 actor（`x-amzn-bedrock-agentcore-runtime-user-id` → 自定义 actor header → 固定默认值）
2. `RetrieveMemoryRecords` 三个 namespace，各自 try/except，失败只记日志
3. 把结果拼进 system prompt
4. 模型回答（必要时调 `reorder_candidates`）
5. `CreateEvent` 写入这一轮（在回答之后，慢写不拖慢回复）

---

## 5. Prerequisites

- Node.js ≥ 20（本机 22.22.2）、AgentCore CLI 0.31.1、AWS CLI 2.x、uv 0.11.9
- 宿主机 Python 3.10–3.14（本机 3.14.0）；运行时目标是 `PYTHON_3_13`，写死在契约里
- 一个有 Bedrock 模型权限的 AWS 账号，区域 `us-east-1`
- 模型 `deepseek.v3.2`，通过 `MODEL_ID` 环境变量传入
- `jq`（本文用它把 trace 里的 span 摊平成表格）

```bash
agentcore --version
aws configure get region
aws sts get-caller-identity --query Account --output text
```

### 5.1 最小权限（生产用法）

CLI 会为 runtime 和 memory 各生成一个 role。生产上你要的是：runtime role 能调 Bedrock 与 memory 的 `CreateEvent` / `RetrieveMemoryRecords`；memory execution role 能被 AgentCore Memory 服务 assume。实验室账号里这两件事由 CLI 自动完成，不需要手工建。

---

## 6. Cost & time

| 项 | 实测 |
|---|---|
| 部署（含建 memory 与两个 role） | 4 m 20 s |
| 应用改动后再部署 | 1 m 44 s |
| 单次 invoke（CLI 墙钟） | 17–21 s |
| 偏好抽取可读 | 113 s 时还读不到，236 s 时读得到 |
| 情节抽取可读 | 990 s（16 m 30 s） |
| 一次 trace 过的 invoke 的模型消耗 | 1 400 in / 94 out token ≈ $0.001 |
| 拆除（`remove all` + 收敛部署） | 见 §9 |

memory 资源本身按存储与它自己发起的抽取模型调用计费；本用例一天之内远低于 1 USD。

---

## 7. Step-by-step

> 下面所有 `agentcore` 命令都必须在**用例根目录** `usecases/02-memory/` 执行。
> 在 `agentcore/` 子目录里执行会直接报 `Please run this command from your project root directory.`
> CLI 没有 `--region`，区域只认 `agentcore/aws-targets.json`。

### 7.1 部署

```bash
cd usecases/02-memory
agentcore deploy -y --target default
agentcore status
```

期望看到 `Runtime: READY`，以及 `Memories` 一栏列出三个 strategy（`USER_PREFERENCE, EPISODIC, SEMANTIC`）。Outputs 里有一行 memory id、一行 runtime ARN。

### 7.2 偏好：写一次，换一个 session 读

两次 invoke 用**不同的 `--session-id`**，同一个 `--user-id`。第一次只说偏好：

```bash
agentcore invoke --user-id store_manager_south \
  --session-id "<uuid>-<uuid8>" \
  --prompt "From now on, only reorder for the South China region. Ignore every other region."
```

> session id 最短 33 字符，一个 uuid4 的 hex 只有 32 位。用两段 uuid 拼：
> `--session-id "$(uuidgen | tr A-Z a-z)-$(uuidgen | tr A-Z a-z | cut -c1-8)"`

等三到四分钟（`CreateEvent` 只是触发抽取，抽取本身不在 invoke 里），换一个 session id 再问：

```bash
agentcore invoke --user-id store_manager_south \
  --session-id "<另一个 uuid>" \
  --prompt "Draft this week's reorder list."
```

这次什么都不解释，回答却是华南三店。它不可能来自这个 session，也不可能来自默认策略：没有记忆时 agent 会明确说自己在猜华北（见 §7.3 的第一步）。

### 7.3 隔离：同一分钟，两位店长

先给第二位店长一条偏好，然后是关键的两次对照调用，中间只隔 14 秒：

```bash
agentcore invoke --user-id store_manager_east \
  --session-id "<uuid>" \
  --prompt "From now on, only reorder for the East China region. Ignore every other region."

# 等三到四分钟
agentcore invoke --user-id store_manager_east --session-id "<uuid>" \
  --prompt "Draft this week's reorder list."

agentcore invoke --user-id store_manager_south --session-id "<uuid>" \
  --prompt "Draft this week's reorder list."
```

同一个问题、同一个 runtime、同一个 memory 资源：一个答华东（上海/杭州/南京），另一个答华南（广州/深圳/东莞）。`--user-id` 进 nanospace 的键，所以隔离不需要任何过滤。

### 7.4 情节：失败一次，被记住一次

```bash
agentcore invoke --user-id store_manager_east --session-id "<uuid>" \
  --prompt "I tried restocking my stores from the Guangzhou warehouse last month. It failed: the lead time was 9 days and three stores stocked out. Make a note of it."

# 等约 16 分钟，情节抽取比偏好慢一个数量级
agentcore invoke --user-id store_manager_east --session-id "<另一个 uuid>" \
  --prompt "How should I restock the East China stores this week?"
```

第二次回答会主动提起「上次从广州仓补货失败、lead time 9 天」这件事，并据此给方案。没有人把那段话重新发了一遍。

### 7.5 看这次调用到底做了什么

```bash
agentcore traces list
agentcore traces get <trace id>
```

`traces get` 会把 JSON 落到 `agentcore/.cli/traces/`（该目录下的 `@ptr` 字段是 base64，解出来含账号 ID，别直接贴出去）。用 `jq` 把 span 摊平：

```bash
jq -r '[.[] ."@message" | select(type == "object" and .name != null)] as $spans
  | $spans | sort_by(.startTimeUnixNano) | .[] | (.attributes // {}) as $a
  | [.name, (((.durationNano // 0) / 1000000 | floor | tostring) + " ms"),
     (if $a["gen_ai.usage.input_tokens"] then ($a["gen_ai.usage.input_tokens"] | tostring) + " in / " + ($a["gen_ai.usage.output_tokens"] | tostring) + " out" else "-" end)] | @tsv' \
  agentcore/.cli/traces/<trace file>.json | column -t -s $'\t'
```

你会看到模型之前有三次 `RetrieveMemoryRecords`（三个 namespace 各一次），模型之后有一次 `CreateEvent`，中间还夹着一个 `execute_tool reorder_candidates`。这条表格就是「读了什么、写了什么」的全部证据。

### 7.6 本地跑（不碰 AWS）

```bash
agentcore dev -l    # 监听 http://localhost:8080/invocations
```

没有 `MEMORY_*_ID` 时 `memory.py::from_env()` 返回 `None`，agent 退化成「会忘记的那个版本」，正好用来复现 §3 开头的那句话。

---

## 8. Verify

四类断言，全部用原生命令的输出自证（`evidence/` 里按顺序留了原始输出）：

1. **跨会话偏好**：session 2 在从未见过那句话的前提下按偏好下单（`evidence/31`）
2. **actor 隔离**：同一分钟同一个问题，两位店长拿到各自的区域（`evidence/39` 与 `evidence/40`）
3. **情节回忆**：后一个 session 主动复述上一次失败的补货方案（`evidence/44`）
4. **independence**：只有本用例的资源挂在 `Project=agentcore-in-action` 下（`evidence/38`、拆除后 `evidence/45`）

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' --output text
```

期望：部署期间四行且都是 `02`，拆除后零行。

> 完整仓库里还有一层系列级校验，会在这之上再核对能力覆盖、目录自包含、难度单调、跨栈引用与命令是否存在。本目录不含那份工具，也不需要它来跑通本文的每一步。

---

## 9. Cleanup

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status
```

两步都要：`remove all` 只是把资源从 `agentcore/agentcore.json` 里摘掉，**真正的删除靠随后这次 deploy 把 stack 收敛到空**。`-y` 不是可选项：没有 tty 时（CI、管道、脚本）命令会以 `This command requires an interactive terminal` 直接失败。

`remove all` 会把 `agentcore/agentcore.json` 与 `agentcore/aws-targets.json` 写到空，所以**重新部署之前先从 git 恢复这两个文件**：

```bash
git checkout agentcore/agentcore.json agentcore/aws-targets.json
```

有意留下的只有一样：CDK bootstrap stack 与它的 asset bucket。那是账号级地基，每个用例都用，不该跟着单个用例删。memory 资源随栈一起删，所以重新部署时记忆是空的，所有结论要从头再挣一遍。

---

## 10. Going further

- 延伸实验：
  1. 把 `agentcore/agentcore.json` 里 `eventExpiryDuration` 从 30 改成 7，重新部署，观察事件留存窗口的变化。
  2. 把 EPISODIC strategy 删掉再部署一次，§7.4 那两次调用就再也问不出「上次失败」——没人抽出那条 record，即使 event 还在。
  3. 再跑一次 `agentcore deploy`，让 runtime 升一个版本，然后对比两次版本的 trace。
- 官方文档：<https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html>
- 难度阶梯上的位置：本用例是第 2 档。
- 文章版：`articles/agentcore-memory-that-remembers.md`
