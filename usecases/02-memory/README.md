# UC02 · Memory（短期记忆与跨会话长期记忆）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 02 · **Difficulty**: **D2** · **Region**: `us-east-1`
> **Verified on**: 2026-10-18 · **Cost**: 全程 ≈ $0.03 的模型调用 + 一天的 memory 存储（上界 < $2）· **Time**: 60 min（其中首次部署 4 m 23 s，断言 17 m 27 s）
> **Capabilities**: `memory`（深挖）· `runtime` / `identity`（附带）
> **Standalone**: yes。目录不依赖任何其他用例，也不需要仓库里的其他文件；拷到任何地方照样能跑（见 §2.3）。

> 文中的账号 ID 已脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：一个上周说过「只要华北区」的补货助手，在这周的全新 session 里不再问第二遍。

跑完之后你会得到：

- 一个 runtime ARN 与一个 memory ARN（`make status` 会打印出来）
- 一次跨会话回忆：session 1 只说了偏好，session 2 直接按偏好下单
- 一次隔离证明：`store_manager_north` 与 `store_manager_south` 各自只看到自己的偏好
- 一次情节回忆：一条失败补货记录被语义检索找回来，而不是靠重放对话
- 一份可重复执行的断言：`make test` 输出 `4 passed, 0 failed`

---

## 2. 独立性与难度定位

### 2.1 为什么是 D2

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | 1（`memory` 深挖，`runtime` 复用） | ≤ 2 ✅ |
| 新增外部依赖 | 1 个有状态 AWS 资源（AgentCore Memory） | 1 个 ✅ |
| 必须理解的机制 | 状态、检索、隔离三个轴：什么进短期、什么进长期、谁看不见谁 | ✅ |
| 参考耗时 | 60 min | ≤ 60 min ✅ |

**难度上升的实际含义**：UC01 里 agent 是无状态的，invoke 结束即归零。本用例第一次让状态活过 invoke，于是三个新问题必须回答：写进去的东西什么时候变得可读（异步抽取）、读回来的东西怎么进 prompt（检索结果拼进 system prompt）、两个人怎么不串（actor id 进 namespace）。

### 2.2 前置**知识**（不是前置资源）

- 知道 AgentCore 的一次 invoke 属于某个 `runtimeSessionId`
- 知道 namespace 是带前缀的路径，不是数据库表

不需要先跑过 UC01。两篇的目录结构相同只是同源，代码不互相 import。

### 2.3 独立性声明

- 本目录**不 import** 任何其他用例，也不读其他用例的 stack outputs
- 本目录的 `agentcore/agentcore.json` 只声明自己的 runtime 与 memory
- `make check` 会把整个目录拷到临时目录再跑一遍检查，证明「拷贝即独立」
- 所有资源带 `Project=agentcore-in-action`、`UseCase=02`、`AutoDelete=true` 三个 tag，清理断言靠它们
- 断言 4（`independence`）要求账号里没有其他用例的资源。**跑之前请确认其他用例已经 `make down`**，否则它失败得理直气壮

### 2.4 官方坐标（对齐 awslabs/agentcore-samples）

- `01-features/04-manage-context-of-your-agent/memory`
- `02-use-cases/01-conversational-agents/episodic-memory-claims-agent`

两者都强调「短期是 event、长期是 strategy 抽出来的 record」，本用例的 `app/aia_uc02/memory.py` 就是这条分界线。

---

## 3. 为什么需要这一层

补货助手的第一版只会看着系统提示词回答。于是每周一，店长都要重新说一遍「我只要华北区」。

把这句话塞进 prompt 缓存不解决问题：换一个店长就串了，隔一周就过期了，而且没人说得清它存在哪。AgentCore Memory 把这件事拆成两个可以分别验证的动作：

- **写**：`CreateEvent`，一次 invoke 一条，键是 `(actorId, sessionId)`，30 天后过期
- **读**：`RetrieveMemoryRecords`，按 namespace 检索抽取出来的 record

关键在于「写」和「可读」之间隔着一个异步抽取。这个间隔是本用例最容易被低估的部分，也是断言唯一需要等待的地方。

---

## 4. Architecture

```text
caller ──invoke(prompt, actor_id)──> Runtime aia_uc02 ──converse──> Bedrock deepseek.v3.2
                                          │
                                          ├── CreateEvent（短期，一次一条）
                                          ▼
                              Memory aia_uc02_mem
                                 /users/{actorId}/preferences    USER_PREFERENCE
                                 /users/{actorId}/facts          SEMANTIC
                                 /episodes/{actorId}/{sessionId} EPISODIC
                                          │
                                          └── RetrieveMemoryRecords（长期，读一个 namespace）
```

一次 invoke 的顺序是固定的：

1. 解析 actor（payload 的 `actor_id` → 运行时 header → 固定默认值）
2. `RetrieveMemoryRecords` 三个 namespace，各自 try/except，失败只记日志
3. 把结果拼进 system prompt
4. 模型回答
5. `CreateEvent` 写入这一轮（在回答之后，慢写不拖慢回复）

---

## 5. Prerequisites

- Node.js ≥ 20（本机 22.22.2）、AgentCore CLI 0.31.1、AWS CLI 2.x、uv 0.11.9
- 宿主机 Python 3.10–3.14（本机 3.14.0）；运行时目标是 `PYTHON_3_13`，写死在契约里
- 一个有 Bedrock 模型权限的 AWS 账号，区域 `us-east-1`
- 模型 `deepseek.v3.2`，通过 `MODEL_ID` 环境变量传入

```bash
cd usecases/02-memory
make doctor          # 19 项检查，含 memory 契约与模型可用性
```

`make doctor` 会检查三件部署时才会暴露的事：memory 是否声明、`USER_PREFERENCE` 与 `EPISODIC` 两个 strategy 是否在、每个 strategy 的 namespace 模板里是否有 `{actorId}`。

### 5.1 最小权限（生产用法）

CLI 会为 runtime 和 memory 各生成一个 role。生产上你要的是：runtime role 能调 Bedrock 与 memory 的 `CreateEvent` / `RetrieveMemoryRecords` / `ListMemoryRecords`；memory execution role 能被 AgentCore Memory 服务 assume。实验室账号里这两件事由 CLI 自动完成，不需要手工建。

---

## 6. Cost & time

| 项 | 实测 |
|---|---|
| 首次部署（含建 memory 与两个 role） | 4 m 23 s |
| 第二次部署（只改描述） | 58 s |
| 单次 invoke（含 CLI 启动） | 19 s |
| 偏好抽取可见（空 namespace 首次） | 88 s |
| 情节抽取可见 | 959 s（约 16 min） |
| `make test` 全程 | 17 m 27 s（几乎都花在等情节抽取） |
| 模型调用 | 15 次 invoke，约 0.04 USD（单次实测 3 433 in / 210 out） |
| 拆除 | 4 m 11 s |

memory 资源本身按存储与它自己发起的抽取模型调用计费；本用例一天之内远低于 1 USD。

---

## 7. Step-by-step

### 7.1 自检

```bash
make doctor
```

期望结尾是 `19 passed, 0 warned, 0 failed` 与 `next: make deploy`。任何 FAIL 都带一行 fix，照着做即可。

离线也可以跑：`python3 tests/doctor.py --offline` 会跳过三个需要 AWS 的检查。

### 7.2 部署

```bash
make deploy
```

期望看到两行 Outputs，一行是 memory id，一行是 runtime ARN：

```text
ApplicationMemoryAiaUc02MemIdOutput7F0802F1: aiauc02_aia_uc02_mem-y7Ql9N3D59
ApplicationAgentAiaUc02RuntimeArnOutput9F81CB35:
  arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc02_aia_uc02-ACujAB8uYJ
```

`make status` 会同时打印 memory 的三个 strategy，用来确认它们真的建出来了。

### 7.3 两个 session

第一次说偏好，第二次什么都不说直接要清单。两次用不同的 `--session`，同一个 actor。

```bash
python3 run.py invoke --session "$(uuidgen | tr A-Z a-z)-$(uuidgen | tr A-Z a-z | cut -c1-8)" \
  --prompt "From now on, only reorder for the North China region. Ignore every other region."

# 换一个 session id，再问一次
python3 run.py invoke --session "$(uuidgen | tr A-Z a-z)-$(uuidgen | tr A-Z a-z | cut -c1-8)" \
  --prompt "Draft this week's reorder list."
```

第二次的回答会主动提到「按你记录的偏好，只补华北」。

换 actor 看隔离：

```bash
python3 run.py invoke --actor store_manager_south --prompt "Draft this week's reorder list."
```

同一个问题，南区的店长拿到的是华南。actor 走 `x-amzn-bedrock-agentcore-runtime-custom-actor-id` 这个 header，入口把它变成 namespace 的一部分。

### 7.4 跑断言

```bash
make test
```

四条断言，逐条对应 §1 的四件事。期望 `4 passed, 0 failed`。若第 4 条失败并点名 `aiauc01` 之类的资源，说明账号里还有别的用例没拆，不是本用例的问题。

### 7.5 本地跑（不碰 AWS）

```bash
make dev      # 端口 8080，真实模型，没有 memory 资源
```

没有 `MEMORY_*_ID` 时 `from_env()` 返回 `None`，agent 退化成「会忘记的那个版本」，正好用来复现本用例开头的那句话。

---

## 8. Troubleshooting

| 症状 | 原因 | 修法 |
|---|---|---|
| `Invalid length for parameter runtimeSessionId, value: 22, valid min length: 33` | session id 太短，请求还没发出去就被参数校验拦下 | 用两个 uuid4 拼，单个 hex uuid 只有 32 位，差一位 |
| `no episodic record ... within 300s` | 情节抽取比偏好抽取慢一个数量级（本资源实测 15 min） | 把 deadline 抬到 20 min 以上；断言里打印实际等待时长 |
| `make invoke --session ...` 报 `unrecognized option` | make 不转发不认识的 flag | 用 `python3 run.py invoke --session ...`，或 `AIA_PROMPT=... make invoke` |
| 第二条断言里 actor 看到了对方的区域 | 某个 strategy 的 namespace 模板里没有 `{actorId}` | `make doctor` 的 memory contract 段会直接点出来 |
| `agentcore remove all` 报 `requires an interactive terminal` | 非 tty 环境 | `run.py` 已经固定传 `-y` |

---

## 9. Cleanup

```bash
make down
```

两步：`agentcore remove all -y` 把本地契约清空，随后的 `agentcore deploy` 才真正删栈。跑完期望 `aia_uc02: Local only` 与 `aia_uc02_mem: Local only`。

有意留下的只有一样：CDK bootstrap stack 与它的 asset bucket。那是账号级地基，每个用例都用，不该跟着单个用例删。memory 资源随栈一起删，所以重新部署时记忆是空的，所有断言要从头再挣一遍。

`agentcore.json` 与 `aws-targets.json` 会被改写，重新部署前从 git 恢复。

---

## 10. What you repeated（为独立而内嵌的基线）

- 一个最小 Strands agent、`model/load.py`、`model/sanitize.py`、`tests/doctor.py`、`tests/copy_check.py`、`run.py`、`Makefile`：与 UC01 同源
- 重复是独立性的代价：本用例不 import UC01，也不读它的 stack outputs，所以这些文件必须自带

内容上真正新增的只有三处：`app/aia_uc02/memory.py`、`agentcore.json` 里的 `memories` 段、以及 `tests/smoke.py` 里那三条 memory 断言。
