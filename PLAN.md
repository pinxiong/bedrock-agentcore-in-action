# AgentCore in Action · 系列总体规划（v3 · 独立用例 + 难度阶梯）

> **v3 修订说明**
>
> | 版本 | 结构 | 独立性怎么实现 | 问题 |
> |---|---|---|---|
> | v1 | 9 个平行用例 | 9 个目录、9 套 IaC | 无难度曲线，读者不知道该从哪开始；9 套样板重复 |
> | v2 | 1 个项目、7 个渐进阶段 | **git tag** | 伪独立：`stage-04` 无法脱离 `stage-01..03` 部署 |
> | **v3** | **7 个独立用例，按难度递增排列** | **每例自带 agent 与 IaC 栈** | 真独立，代价是每例自带基线（见 §2.3） |
>
> **你的原话（v3 的设计目标）**：「每个用例的难度是逐个递增的，并且每个用例的 use case 都是相互独立的。」
>
> 目标不变：覆盖 AWS Bedrock AgentCore 全部 **14 项能力**；每个用例可独立部署、可独立清理、有可照抄执行的文档、能写成一篇英文技术文章。
>
> 事实基线日期：**2026-10-13**

---

## 1. 事实基线（截至 2026-10）

### 1.1 能力清单（14 项，系列覆盖的全部对象）

| # | 能力 | 一句话 | GA | 深挖于 |
|---|---|---|---|---|
| 1 | **Harness** | 托管 agent loop，配置文件声明即得一个 agent | 2026-06 | UC05 |
| 2 | **Runtime** | Serverless 运行时，会话隔离、长时异步、多协议 | 2025-10 | UC01、UC07 |
| 3 | **Memory** | 短期 + 长期记忆（semantic / preference / summary / episodic） | 2025-10 | UC02 |
| 4 | **Gateway** | API / Lambda / 已有 MCP server → MCP 工具 | 2025-10 | UC03 |
| 5 | **Identity** | 入站认证、出站凭证代理、token vault | 2025-10 | UC03 |
| 6 | **Policy** | 在 Gateway 前拦截每次工具调用，自然语言 → Dogwood/Cedar | 2026-03 | UC04 |
| 7 | **Code Interpreter** | 隔离沙箱执行 Python / JS / TS | 2025-10 | UC05 |
| 8 | **Browser** | 云端托管浏览器（CDP / Playwright） | 2025-10 | UC05 |
| 9 | **Web Search** | 托管 Web 索引，MCP 兼容，查询不出 AWS | 2026-06 | UC05 |
| 10 | **Observability** | CloudWatch GenAI Observability，OTel 标准 | 2025-10 | UC01、UC06 |
| 11 | **Evaluations** | 13 个内置 evaluator + 自定义 LLM-as-judge | 2026-03 | UC06 |
| 12 | **Optimization** | trace → prompt/tool 改进建议，batch eval + A/B | 2026-06 | UC06 |
| 13 | **Payments** | x402 / MPP 微支付 + 消费上限 | 2026-08 | 番外 |
| 14 | **Registry** | Agent / 工具 / Skill 的治理型目录 | 2026-08 | UC07 |

**这 14 项的出处**（2026-10-15 对齐官方，两处清单口径不同，勿混用）：

- AWS 文档 `what-is-bedrock-agentcore` 的核心服务表列 **13 项**：Harness、Runtime、Memory、Gateway、Identity、Code Interpreter、Browser、Observability、Payments、Evaluations、Optimization、Policy、Registry（**没有 Web Search**）；
- `awslabs/agentcore-samples` 的 `01-features/README.md` 也列 **13 项**，但含 Web Search、不含 Optimization；
- **并集 = 14**，即本表。`docs/05-capability-map.yaml` 的 `capabilities[].src` 逐项标注了每项出自哪份清单。
- 措辞修正：Policy 的规则语言官方写法是 **Dogwood**（与 Cedar 兼容），只说 Cedar 不准确。

### 1.2 部署形态（v1 里我表述不清的地方，已核实修正）

**AgentCore 不涉及 ECS。** Runtime 是 serverless 托管运行时，每个 session 跑在独立 microVM 里，你不管集群、节点、扩缩容、负载均衡。

构建 agent 有**两条顶层路径**，这是系列结构的地基：

| 路径 | 你写什么 | 适合 |
|---|---|---|
| **Managed harness** | 一个配置文件（model、prompt、tools、memory） | 最快从想法到跑起来的 agent |
| **Code-based agent** | Python agent loop（Strands / LangGraph / Google ADK / OpenAI Agents） | 需要完全控制编排逻辑 |

部署包有**两种 build type**，取决于要不要 Docker：

| | `CodeZip`（默认） | `Container` |
|---|---|---|
| 本地需要 Docker | **不需要** | 需要（构建镜像的 daemon） |
| 包大小上限 | 250 MB | 2 GB |
| 语言 | Python 3.10–3.13 | 多语言 |
| 会话创建率 | 25 个新会话/秒 | 1.6 个新会话/秒 |
| 产物存放 | ZIP 存 S3（服务账号侧） | 镜像存你账号的 ECR |
| 安全补丁责任 | AgentCore 自动打语言运行时补丁 | AgentCore 只打内核，镜像要你自己重建 |

**系列统一走 `CodeZip`**：读者不需要装 Docker，`agentcore create` 的默认选项就是这个。

另有 **Runtime 自选 EC2 实例类型**（2026-08-06 GA）：用来指定底层实例类型做性能/成本调优，实例仍由 AgentCore 托管，**不是让你自己开 EC2 机器**。

### 1.3 CLI 能力（每例的骨架命令）

```
agentcore create                 # 建项目（选 Harness 或 Agent）
agentcore dev                    # 本地跑，浏览器里打开 agent inspector 看 trace
agentcore deploy                 # 部署（底层用 AWS CDK 合成资源）
agentcore invoke                 # 调已部署的 agent
agentcore logs / traces list|get # 命令行看日志与 trace
agentcore add agent              # 加第二个 agent
agentcore add memory             # 加记忆
agentcore add gateway            # 加工具网关
agentcore add credential         # 加第三方 API key
agentcore add evaluator          # 加质量评估
agentcore add payment-manager    # 支付管理器
agentcore add payment-connector  # 支付渠道
agentcore remove all             # 清空配置，再 deploy 即销毁资源
```

### 1.4 必须写进文档的六个坑

1. **Registry 换过命名空间**：已迁到独立的 `agent-registry`（ARN 前缀 `arn:aws:agent-registry`、服务主体 `agent-registry.amazonaws.com`、托管策略 `AgentRegistryFullAccess`）。旧 `bedrock-agentcore` 命名空间 2026-09-17 已关闭。
2. **区域割裂**：Registry 仅 5 区，Web Search 需 us-east-1，**全系列锁 `us-east-1`**。
3. **`agentcore` 命令名冲突**：若曾 `pip install bedrock-agentcore-starter-toolkit`，旧的 Python `agentcore` 会遮蔽 npm 的。前置检查要包含 `pip uninstall bedrock-agentcore-starter-toolkit`。官方文档把这个坑单独列了一条提示。
4. **本机 CLI 默认区域不是 us-east-1**（2026-10-14 实测：`~/.aws/config` 里是 `ap-southeast-1`）。任何没带 `--region us-east-1` 的命令都会落到错误的区域，读者会以为服务不可用。`aia doctor` 因此校验区域而不是信任环境变量。
5. **美国模型厂商有地理封锁**（2026-10-14 实测）：从受限地区调用 Bedrock 上的 Anthropic 与 OpenAI 模型，一律返回 `ValidationException: Access to Anthropic/OpenAI models is not allowed from unsupported countries, regions, or territories`。**这与 Model access 权限无关**，是厂商国别政策，控制台里开通也没用。→ 系列默认模型因此选 DeepSeek（见 §1.5）。
6. **`agentcore create` 会装 Python 依赖**：PyPI 官方源在部分网络下不可达，命令会**静默卡死**在 "Set up Python environment"（venv 停在 68K，无报错）。必须先设镜像：`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple`。实测加上后 3 分 31 秒成功。

### 1.5 CLI 的项目形态与模型选型（2026-10-14 实测，UC01 本地闭环已跑通）

**项目是 schema-first 的，IaC 就是一份 JSON。** 实测的产出结构：

```
<project>/
├── AGENTS.md                      # 官方约定：JSON 是唯一真相源
├── README.md                      # create 生成的项目说明
├── .git/                          # create 会执行 git init
├── agentcore/agentcore.json       # ★ 所有资源在这里声明
├── agentcore/aws-targets.json     # 部署目标（account + region）
├── agentcore/.llm-context/*.ts    # 权威 schema，字段级约束写在这里
├── agentcore/cdk/                 # CLI 生成的 CDK 应用（明令不可手改）
└── app/<AgentName>/               # agent 代码（create 生成的 starter），codeLocation 指向它
```

`create` 的完整形态（带 agent 脚手架）：

```bash
agentcore create --name <AgentName> --framework Strands \
  --model-provider Bedrock --memory none --defaults
```

`--name` 同时决定项目目录名、runtime 名和 `app/<AgentName>/` 的目录名；加
`--project-name` 可以只改项目目录名。只想要空项目时用 `--no-agent`（不生成 app/ 代码目录）。

三条官方不变量，直接影响我们的文档写法：

- **JSON 是唯一真相源**，改行为要改 JSON，不要改 `cdk/` 里生成的代码
- **`name` 决定 CloudFormation Logical ID**：改名 = 销毁重建，改其他字段 = 原地更新
- **删资源用 `agentcore remove` 再 `agentcore deploy`**，不是手工删

`agentcore.json` 的顶层字段**就是能力清单本身**：
`runtimes / memories / knowledgeBases / credentials / evaluators / onlineEvalConfigs / agentCoreGateways / policyEngines / configBundles / abTests / harnesses / datasets / capacityProviders / payments`。

本仓库的取舍：**完全对齐 CLI 官方布局**，`codeLocation: "app/<AgentName>/"`（本系列即
`app/aia_uc01/` … `app/aia_uc07/`），不另造 `src/`。理由是"照抄就能做"：读者按官方命令
跑出来的目录必须和文档/图片里画的一致。带自己的代码时官方另有 BYO 入口
（`agentcore add agent --type byo --code-location <dir> --entrypoint <file>`），这条只在
文档里作为脚注提一句。

> 2026-10-15 修订：此前本仓库用 `codeLocation: "src/"`（自造目录），导致读者按官方命令
> 生成的 `app/<AgentName>/` 与文档不一致，已全量改回官方路径。

**模型选型（全部实测，2026-10-14）**

| model id | 可用性 | 备注 |
|---|---|---|
| `deepseek.v3.2` | ✅ Converse + Strands 双通 | **系列默认**；OpenAI 兼容响应；流式原文可能带 `<｜DSML｜function_calls` 标记 |
| `amazon.nova-pro-v1:0` | ✅ | 输出干净，字符串里会带 `<thinking>` |
| `amazon.nova-lite-v1:0` | ✅ | 同上 |
| `anthropic.*` | ❌ | 地理封锁 |
| `openai.*` | ❌ | 地理封锁 |
| `deepseek.r1-v1:0` | ❌ | 不支持 on-demand，需 inference profile |
| `amazon.nova-2-lite-v1:0` | ❌ | 同上 |

切换方式：`MODEL_ID` 环境变量（`app/aia_ucNN/model/load.py`，默认 `deepseek.v3.2`）。

**其余实测约束**

- `runtimeVersion` 默认 `PYTHON_3_14`（预发布）→ 本系列**钉 `PYTHON_3_13`**
- agent 名与项目名只能 `^[a-zA-Z][a-zA-Z0-9_]{0,47}$`，**不能有连字符**
- 本地开发：`agentcore dev` 起的 server **端口是动态的**（本次 8082，Chat UI 在 8081），日志在 `agentcore/.cli/logs/dev/`
- **0.31.1 的 `agentcore invoke` 没有 `--dev` 参数**（CLI 模板 README 里的 `agentcore invoke --dev "..."` 是旧语法）。本地验证直接 POST `http://127.0.0.1:<port>/invocations`
- 本地闭环实测通过：真实工具调用（`toolUse: add_numbers {"a": 17, "b": 25}`）→ 第二轮答 `The sum of 17 plus 25 is 42.`（454 + 490 tokens，2.5s + 1.2s）

---

## 2. v3 的三个核心定义

这一节是 v3 与 v2 的全部差别所在，也是后面所有设计决策的依据。

### 2.1 「独立」的精确定义（可验证，不是形容词）

一个用例"独立"，必须同时满足六条。任何一条不满足，就不是独立用例：

| # | 条件 | 判据 |
|---|---|---|
| **I1** | **部署独立** | 在干净账号里 `python aia.py up 05` 成功，此时 UC01–04 **从未部署过** |
| **I2** | **清理独立** | `python aia.py down 05` 后，该用例资源与账单归零，且**不影响**其他用例 |
| **I3** | **IaC 独立** | 每例一个独立栈、独立资源命名空间；**无跨栈 export/import**，不读别的用例的参数 |
| **I4** | **代码独立** | 每例的 `codeLocation`（= `usecases/NN-*/app/aia_ucNN/`）**不 import** 其他用例的模块；共享代码只能以"生成器模板"形式**复制**进来后各自演进 |
| **I5** | **文档独立** | README 从零讲起；前置条件只写**知识**，绝不写"你必须先跑完 UC0X" |
| **I6** | **拷贝即独立** | `cp -r usecases/NN-* /tmp/ucNN` 之后，目录内**没有任何路径指向目录之外**，也不含任何自建运维脚本（`run.py` / `Makefile` / `tests/smoke.py` / `tests/copy_check.py` …）；这一条由仓库级校验**读取目录**得出 |

**回归测试（每条用例的 DoD 之一）**

```bash
# 前置：账号里没有任何 Project=agentcore-in-action 的资源
python aia.py up 05 && python aia.py status 05 && python aia.py down 05

# 断言：本次操作没有创建过其他用例的资源
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=01,02,03,04,06,07
# 期望：ResourceTagMappingList 为空
# 注意：`--tag-filters` 跨 filter 是 AND、单个 filter 的 Values 是 OR。
# 写成 Key=UseCase,Values=01 Key=UseCase,Values=02 是要求一个资源同时属于两个用例，
# 永远返回空、假通过。多值必须写在一个 filter 里（如上面这条）。

# 断言 I6 与能力实证（这一步不需要 AWS）
python aia.py check 05
# 期望：0 failed。它读取目录：无路径逃逸、无自建运维脚本、evidence/ 里有每条声明能力的存档
```

资源标签里带 `UseCase=NN` 就是为了让前两条断言可执行。**独立性是跑出来的，不是写出来的。**

**I6 的实测口径**（仓库级 `[COPY]` 类，见 §2.4）：不是起一个脚本扫一遍就算，而是**把目录当数据读一遍**——逐行检查有没有路径指向目录之外、有没有本系列禁用的自建运维脚本、合约标签与 `codeLocation` 是否自洽。用例目录里**不自带**任何检查脚本：脚本一旦在目录里，它就既是被检查的对象又是检查者，而且拷走之后还要能自证，等于给每个用例塞一份可以漂移的实现。

### 2.2 「难度递增」的度量（不是感觉，是刻度尺）

每个用例在 `docs/05-capability-map.yaml` 里声明 `difficulty: 1..5`，声明值必须落在下表的刻度内，且**序列必须单调不减**（CI 校验）。

| 难度 | 新增能力数 | 新增外部依赖 | 交付前必须理解的机制 | 参考耗时 | 用例 |
|:--:|---|---|---|---|---|
| **D1** | 1–2 | 无（只有本账号与 Bedrock） | 部署模型、会话模型 | ≤ 30 min | UC01 |
| **D2** | 1–2 | 1 个 AWS 资源 | 状态、检索、隔离维度 | ≈ 1 h | UC02 |
| **D3** | 2–3 | 1 个身份系统或第三方 API | 认证、授权、网络边界、裁决与审计 | 2–2.5 h | UC03、UC04 |
| **D4** | 3–5 | 多服务 + 异步或流式 | 编排、评测、统计显著性 | 3–4 h | UC05、UC06 |
| **D5** | 5+ | 多 agent + 组织级治理 | 协议、隔离、并发、目录 | ≈ 4 h | UC07 |

难度上升的实际含义，用一句话说：**D1 你要理解"它跑在哪"，D2 理解"它记得什么"，D3 理解"它凭什么被允许"，D4 理解"它做得好不好"，D5 理解"它和别的 agent 怎么共处"。**

### 2.3 独立性的代价，与对策（必须对读者诚实）

真独立必然带来重复。这是物理规律，不是实现缺陷：**每个用例都要能在别人的账号里从零跑起来，就必须自带一个可跑的 agent 和一套 IaC。** 对策有三条：

| 重复项 | 规模 | 对策 |
|---|---|---|
| 最小 agent 骨架（≈ 1 个文件、20 行） | 7 份 | `aia.py new` 从 `shared/templates/baseline-agent/` **生成**出来，只写一次 |
| IaC 栈骨架（CDK app 入口 + 标签） | 7 份 | 同上，由生成器生成；各例只改自己的资源声明 |
| `AGENTS.md` | 7 份 | 同上，由生成器生成。这是 I6 的价格：入口一旦在目录外，目录就不能单独拷走 |

**入口为什么不再放进目录**（2026-10-18 改）：v3 曾经把 `run.py` + `Makefile` 放进每个用例目录，理由是"拷走即用"。代价是 7 份 × 5 个文件的实现要各自演进，而且它把本系列要教的东西挡在了读者和 CLI 之间：读者学的是 `run.py deploy`，不是 `agentcore deploy`。现在入口就是 CLI 本身：目录里只有 `agentcore ...` / `aws ...` 能跑的东西，`cp -r` 出来照样是活目录，因为活目录的判据是**内容自洽**，不是自带一个入口脚本。

**不做的事**：不建"公共运行时依赖"（例如让 7 个用例 import 同一个 `shared/lib`）。那样 IaC 与代码就重新耦合，I3/I4 立刻失效，等于回到 v2 的伪独立。同样不建"公共入口脚本"或"目录内入口脚本"（那会直接废掉 I6 的真正含义）。

**代价的诚实表述（要写进每篇文档）**：每个用例的文档里有一节列出"为独立而内嵌的基线是什么"。读者应当知道自己在看一份自包含的示例，而不是一个微服务仓库的最佳实践。

### 2.4 「覆盖」如何保证

`docs/05-capability-map.yaml` 声明每个用例的 `deep`（深挖）与 `incidental`（用到）能力，以及对应的 `assertions`（断言）。`shared/scripts/verify-coverage.py` 校验五类规则：

| 类 | 校验 | 依据 |
|---|---|---|
| `[COVER]` | 14 项能力每项至少被一个用例 `deep` | capability map |
| `[EVID]` | 某用例声明 `deep: [policy]`，则 `usecases/NN-*/evidence/` 里必须有一条原生命令（`agentcore ...` / `aws ...`）的输出存档能证明它 | evidence/ |
| `[COPY]` | 该用例目录被拷走后仍然自洽（I6） | **读取**该目录：无逃逸路径、无自建运维脚本、合约自洽 |
| `[INDEP]` | 难度序列单调不减（§2.2）；`agentcore/` 无跨栈引用（I3）；`codeLocation` 目录不 import 其他用例（I4） | 合约 + 源码 |
| `[CMD]` | capability map 的 `cli:` 字段里每条 `agentcore` 命令/子命令/参数都真实存在 | 安装的 CLI |

`[COPY]` 刻意不执行目录里的任何东西：仓库级校验自己把目录读一遍。曾经它是 shell 出去调每例自带的 `tests/copy_check.py`，2026-10-18 那批脚本被整体删掉后改成读目录——判据没变，只是不再需要一个"自己检查自己"的脚本。同理，`[CMD]` 存在的理由是本方案曾写过两条不存在的命令（`agentcore create --harness`、`agentcore add identity`），现在这类错误会被 CI 拦下。

"覆盖了全部 14 项能力"因此从一句声明变成一个 CI 检查项。

---

## 3. 七个用例（难度阶梯）

**贯穿背影**：一家中型电商公司的内部 agent 群。用例之间**没有剧情依赖**，共享的只是公司设定，各例有自己的部门、自己的 agent、自己的场景。这样每篇文章都有一个新鲜的开头，而系列仍像一个家族。

每个用例都有一列 **"自带基线"**：为满足独立性，这一例必须自己带上什么。这一列是 v3 相对 v2 新增的，也是读者判断"我要不要从头做"的依据。

---

### UC01 · First Agent：让 agent 上线

| 项 | 内容 |
|---|---|
| **难度** | **D1**：2 项能力、无外部依赖、≤ 30 min |
| **独立场景** | 客服组的第一个 agent：只根据系统提示词回答问题，没有任何工具和记忆。目标不是"能干活的 agent"，是"跑通部署闭环"。 |
| **自带基线** | 最小 Strands agent（1 个文件）+ CodeZip 部署。**这是整个系列最小的可运行单元。** |
| **做什么** | `agentcore create`（Agent / Strands / Bedrock / **CodeZip**）→ `agentcore dev` 看 inspector → `deploy` → `invoke` → `logs` / `traces` |
| **能力深挖** | **Runtime**（部署、会话隔离、endpoint、版本）、**Observability**（第一次看见完整 trace） |
| **附带** | CLI、CodeZip vs Container 取舍、Harness 一次路径对比、`agentcore status` 拿 ARN 后用 boto3 `InvokeAgentRuntime` 程序化调用 |
| **验证点** | ① 并发两个 `runtimeSessionId` 不串话 ② CloudWatch 与 inspector 都能看到完整 trace ③ 指向旧版本的具名 endpoint 行为不同 |
| **产出** | 可 invoke 的 endpoint ARN + inspector 截图 |
| **成本 / 耗时** | < $1 / 30 min |
| **文章角度** | `agentcore create` 到生产 30 分钟；顺带回答"如果没有 AgentCore，这 11 件事你得自己做"（含读者最先会问的 ECS 问题） |

---

### UC02 · Memory：让它记住你

| 项 | 内容 |
|---|---|
| **难度** | **D2**：1 项能力、1 个有状态资源、≈ 1 h |
| **独立场景** | 复购助手：用户昨天说过"我只关心华北区的货"，今天不该再说一遍。 |
| **自带基线** | UC01 同款最小 agent + 独立的 memory 资源。**不比 UC01 多任何前置条件。** |
| **做什么** | `agentcore add memory` → 配短期 + 长期策略 → 跑两次会话做对照 |
| **能力深挖** | **Memory**：STM 多轮上下文 → LTM 四策略（semantic / user preference / summary / **episodic**）→ 异步记忆提取 → 共享 memory store |
| **附带** | 按 `actorId` 做记忆隔离；Runtime；Evaluations 度量记忆召回（为 UC06 埋线） |
| **验证点** | ① 第二次会话检索命中第一次写入的偏好 ② 用户 A 检索不到用户 B 的记忆 ③ episodic 能召回"上次那个方案失败了" |
| **产出** | 对照组输出：有记忆 vs 无记忆的回答差异 |
| **成本 / 耗时** | < $2 / 1 h |
| **文章角度** | 你的 agent 不是"没有记忆问题"，是"记忆架构问题"：短期 / 长期 / 情景三种职责的分工 |

---

### UC03 · Gateway + Identity：接上企业系统，不交出凭证

| 项 | 内容 |
|---|---|
| **难度** | **D3**：2 项能力、1 个身份系统 + 1 个第三方 API、2.5 h |
| **独立场景** | 运营助手：查订单（Lambda）、开 Slack 工单（OpenAPI）、读 CRM（已有 MCP server），三种后端、三种接入方式。 |
| **自带基线** | 最小 agent + **一个 1 工具的最小网关**（供 UC04 复用这个概念）+ Cognito user pool + 一个 Lambda 后端 + 一张 OpenAPI 描述 + 一个自建 MCP server。**这是系列第一个需要读者搭真实 AWS 资源的一例。** |
| **做什么** | `agentcore add gateway` + `agentcore add credential`；挂三种 target；配 Cognito 入站 JWT；配 3LO 出站 |
| **能力深挖** | **Gateway**（Lambda / OpenAPI / 已有 MCP server 三类 target、**语义工具检索**、入站 JWT 认证）、**Identity**（token vault、OAuth2 3LO、API key credential provider） |
| **附带** | **VPC + PrivateLink**（网关出网受控）、第三方 IdP（Okta / Entra）备选路径 |
| **验证点** | ① 三种 target 都出现在 `tools/list` ② 无 JWT 调用被拒 ③ 3LO 首次触发授权链接、token 到期自动刷新 ④ 代码里搜不到任何明文凭证 |
| **产出** | 一张"一个 agent 调三个企业系统"的 trace，凭证全部不在 agent 侧 |
| **成本 / 耗时** | < $5 / 2.5 h |
| **文章角度** | 把企业 API 变成 agent 工具，同时不交出凭证：入站认证和出站授权是两件不同的事 |

---

### UC04 · Policy：给自主权划死边界

| 项 | 内容 |
|---|---|
| **难度** | **D3**：1 项能力深挖，但需要裁决、审计与人工回路；2 h |
| **独立场景** | 退款审批：≤ ¥50 自动、¥50–500 需人工审批、> ¥500 直接拒绝；禁止读 PII 字段；生产操作必须确认。 |
| **自带基线** | **一个只为被拦截而存在的单工具网关**（含一个"退款"工具）。它刻意做得很小：本用例的主角是策略，不是接入方式。**这是 v3 里唯一一处刻意重复，也是最值得向读者解释的一处。** |
| **做什么** | 建 policy engine 挂到网关 → **先 Log-only 观察** → 切 **Enforce** → 用越权请求打它 |
| **能力深挖** | **Policy**：自然语言 → Dogwood/Cedar → 手写 Cedar 做细粒度条件 → Log-only vs Enforce → Guardrails 联动 → 时间 / 速率类策略 |
| **附带** | **inline_function 做人工审批回路**、Observability（策略判定审计日志） |
| **验证点** | ① 同一句越权请求：Log-only 放行并留痕、Enforce 被拒 ② 日志里能看到命中哪条策略 ③ ¥200 的退款走人工审批，全程不改 agent 代码 |
| **产出** | "同一次攻击，两种模式两种结果"的对照 |
| **成本 / 耗时** | < $3 / 2 h |
| **文章角度** | 别再把授权逻辑写在 prompt 里：**做权限裁决的东西，不能是攻击者能对话的东西** |

> **和 UC03 的分界（刻意保持）**：UC03 讲"怎么接进来"，UC04 讲"怎么限制住"。两件事合在一例会变成一锅粥，读者分不清哪段代码在解决哪个问题。代价是 UC04 带一个更小的网关。

---

### UC05 · Research Agent：上网、算数、出报告

| 项 | 内容 |
|---|---|
| **难度** | **D4**：4 项能力深挖、多服务 + 长时编排、3 h |
| **独立场景** | 市场调研：搜网页 → 打开页面抓数据表 → 写 Python 出图 → 交付一份 xlsx。 |
| **自带基线** | **Harness 配置文件本身**（这一例可以不写 agent loop，用托管 loop 起家），加三个工具资源。 |
| **做什么** | 配 Browser / Code Interpreter / Web Search 三个工具；再用 **Harness + 一次 `CreateHarness`** 做同一件事，对比两条路径 |
| **能力深挖** | **Harness**（配置即 agent、会话中途换模型不丢上下文）、**Web Search**（域 / 日期过滤、知识图谱观测）、**Browser**（多标签、截图、CDP）、**Code Interpreter** |
| **附带** | **Skills**（AWS curated 目录 + git 源）、`agentcore export harness`（配置 → Strands 代码的毕业路径）、Evaluations（调研质量打分） |
| **验证点** | ① 一次提问触发 search → browse → code 三段 span ② 生成真实 xlsx / png ③ 中途从 Claude 切到 GPT 后对话仍连续 ④ 导出的 harness 部署到 Runtime 后行为一致 |
| **产出** | 一份自动生成的调研报告 + "配置 5 行 vs 手工 300 行"的对比表 |
| **成本 / 耗时** | < $8 / 3 h |
| **文章角度** | 一次 API 调用，五种工具；顺带回答"Harness 和 Runtime 到底该选哪个"（**最适合当系列首发引流篇**） |

---

### UC06 · Quality Loop：上线之后怎么知道它变差了

| 项 | 内容 |
|---|---|
| **难度** | **D4**：3 项能力深挖 + 统计与 CI 门禁、4 h |
| **独立场景** | 一个上线两个月的 agent，用户开始抱怨，没人说得清是哪一步坏了。 |
| **自带基线** | **一个带 2–3 个工具的 agent**：要有足够的行为可被评测。本用例不关心工具怎么接，只关心它做得对不对。 |
| **做什么** | `agentcore add evaluator` → 四种 eval 模式各跑一次 → 故意注入一个失败 prompt → 让 Optimization 出建议 → batch eval 验证 → A/B 上线 |
| **能力深挖** | **Observability**（GenAI Observability 面板、session → trace → span 下钻、各原语日志内联）、**Evaluations**（13 内置 + 自定义 LLM-as-judge；online / on-demand / batch / simulation）、**Optimization**（failure / intent / trajectory insights、prompt 与 tool description 建议、**Gateway 流量切分做 A/B + 置信区间 / p 值**、config bundle 版本化） |
| **附带** | batch eval 挂进 GitHub Actions 做门禁；三方可观测（Datadog / Grafana）；endpoint 版本与回滚 |
| **验证点** | ① 四种 eval 模式各跑通 ② recommendation 是"有理由的具体改动"而非泛泛建议 ③ A/B 报告含置信区间与 p 值 ④ CI 里 eval 分数下降会 block merge |
| **产出** | 一张"分数从 X 涨到 Y，p < 0.05"的 A/B 报告 |
| **成本 / 耗时** | < $15 / 4 h |
| **文章角度** | 你怎么知道 agent 变差了？把"看着点"换成可度量的改进闭环（**技术含量最高的一篇**） |

---

### UC07 · Multi-Agent + Registry：从一个 agent 到组织资产

| 项 | 内容 |
|---|---|
| **难度** | **D5**：5+ 项能力、多 agent + 组织治理、4 h |
| **独立场景** | 合同审查：一个 orchestrator 通过 A2A 调「条款风险 agent」和「定价合理性 agent」；同时全公司的 agent 需要一个目录。 |
| **自带基线** | orchestrator + 2 个 specialist agent（全部由本用例部署），加 2 个"可注册对象"供 Registry 使用，**不依赖 UC01–06 的产出**。 |
| **做什么** | `agentcore add agent` 加第二个 agent → 部署成独立 Runtime endpoint → orchestrator 走 A2A 调它们 → 并发压测 → 把本用例产出注册进 Registry |
| **能力深挖** | **Runtime 进阶**：托管 MCP server、**A2A**、会话隔离、长时异步、**双向流式**、**AG-UI**、版本与 endpoint 灰度、**自选 EC2 实例类型**；**Registry**：record 类型、审批流（draft → pending → approved）、关键词 + 语义混合检索、Registry 作为 MCP server 被查询、从 runtime / gateway 自动发现、IaC（CloudFormation / Terraform / CDK）、AWS RAM 跨账号共享 |
| **附带** | Step Functions 编排 |
| **验证点** | ① A2A 消息在 trace 里可见 ② 并发 10 session 互不污染 ③ 异步任务超过同步超时上限仍能完成 ④ 双向流式下 barge-in 生效 ⑤ `aws agent-registry list-registries` 通 ⑥ 一句 "payment processing" 能命中叫 "billing" 的记录 |
| **产出** | 三 agent 协作的完整 trace + 一个装着本用例产出的私有目录 |
| **成本 / 耗时** | < $12 / 4 h |
| **文章角度** | 多 agent 不难，难的是隔离、协议和可观测；agent 到几百个之后，第一个问题不是"怎么建"而是"哪些已经有了" |
| **备注** | 内容量最大。若单篇过长，可拆成 UC07a（多 agent 协议）/ UC07b（Registry）两个**同样独立**的用例：Registry 那一例已自带可注册对象，拆开后依然独立 |

---

### 番外 · Agent Payments：让 agent 自己付钱，但花不超

| 项 | 内容 |
|---|---|
| **难度** | **D3** 技术难度，但**外部门槛**把它挡在阶梯之外：需要 Coinbase CDP 或 Stripe Privy 钱包账号 + 少量真金 |
| **为什么是番外不是 UC08** | 阶梯的前提是"读者能连续做下去"。要求读者先注册一个钱包，会打断这条路径。所以它是分支，不是台阶。 |
| **独立场景** | 一个付费数据采购 agent：买一份付费行情数据 → 生成报告，全程受消费上限约束。 |
| **自带基线** | 最小 agent + 支付管理器 + 一个付费端点。 |
| **做什么** | `agentcore add payment-manager` + `add payment-connector` → 设限额 → 成功付一笔小额 → 再故意付一笔超额的 |
| **能力深挖** | **Payments**：x402 / MPP、钱包 provider、session 级 spending limit、支付全链路可观测 |
| **附带** | Gateway（付费端点作为 target）、Identity（钱包凭证托管）、Policy（额度写成硬约束，双保险） |
| **验证点** | ① 小额交易成功拿到数据 ② 超额交易被拒且拒绝原因清晰 ③ 每笔支付可追溯到 session |
| **成本 / 耗时** | ~$2（含真实小额支付）/ 2 h |
| **文章角度** | Agent 会花钱这件事，出路不是禁止，是限额加可审计 |
| **备注** | 文档必须给 sandbox / 测试网路径，以及"没有钱包账号"时的降级演示 |

---

## 4. 覆盖矩阵

● = 深挖（文章核心章节）　○ = 使用　空 = 不涉及

| 能力 | UC01 | UC02 | UC03 | UC04 | UC05 | UC06 | UC07 | 番外 |
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

**14 / 14 项均有至少一个用例深挖。** UC05 一例吃掉 4 项工具类能力：它们在"研究型 agent"里本来就是一起用的，硬拆反而假。

**难度序列（CI 校验单调不减）**

| | UC01 | UC02 | UC03 | UC04 | UC05 | UC06 | UC07 | 番外 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 难度 | D1 | D2 | D3 | D3 | D4 | D4 | D5 | D3（分支） |

### 横切能力

| 横切能力 | 落点 |
|---|---|
| A2A 协议 | UC07 ● |
| Runtime 托管 MCP server | UC07 ●（UC03 ○ 连接已有 MCP server） |
| 双向流式（语音） | UC07 ● |
| AG-UI 协议 | UC07 ● |
| 长时异步任务 | UC07 ●（UC02 / UC05 ○） |
| 会话隔离与多租户 | UC07 ●（UC01 ○ 首次验证） |
| 版本、endpoint 与回滚 | UC01 ●（UC06 ● config bundle / UC07 ○ 灰度） |
| Skills（AWS curated + git 源） | UC05 ● |
| Step Functions 集成 | UC07 ○ |
| VPC + PrivateLink | UC03 ● |
| 自选 EC2 实例类型 | UC07 ● |
| inline_function / Human-in-the-loop | UC04 ● |
| CodeZip vs Container | UC01 ● |
| Harness vs Runtime 路径选择 | UC05 ● |
| IaC | 每例自带独立栈；UC07 追加 Terraform（Registry 支持） |
| 第三方 IdP（Okta / Entra） | UC03 ○ 备选路径 |
| 三方可观测（Datadog / Grafana） | UC06 ○ |

---

## 5. GitHub 仓库结构

仓库名：**`bedrock-agentcore-in-action`**

> 与 v2 的关键差别：**`stages/` 换成 `usecases/`**。每例是一个自包含目录（`app/` + `agentcore/` + `tests/` + 文档 + 文章），不是同一个项目的某个 commit。

```
bedrock-agentcore-in-action/
├── README.md                    # 系列导读 + 难度阶梯 + 14 项能力表 + 覆盖矩阵 + 独立性契约
├── PLAN.md                      # 本文件
├── aia.py                       # ★ 唯一调度器：python aia.py up|down|status|check|verify-all（纯 Python，无 Make/bash/WSL）
├── LICENSE  CONTRIBUTING.md  .gitignore
│
├── usecases/                    # ★ 每例一个自包含目录，互不 import
│   ├── 01-first-agent/
│   │   ├── README.md            #   十二节可操作文档
│   │   ├── app/aia_uc01/        #   ★ 自带 agent（CLI 官方布局）；agentcore.json 的 codeLocation 指向这里
│   │   ├── agentcore/           #   ★ 本用例的 IaC：agentcore.json 是唯一真相源 + CLI 生成的 CDK 应用
│   │   ├── raw/                 #   boto3 对照脚本（控制面 + 数据面），只用于教学，不参与部署
│   │   ├── evidence/            #   ★ 原生命令的输出存档，与 capability-map 的断言一一对应
│   │   ├── tests/               #   本例 agent 自身 Python 的单元测试（离线）
│   │   └── article.md           #   发表稿（英文）
│   ├── 02-memory/
│   ├── 03-gateway-identity/
│   ├── 04-policy/
│   ├── 05-research-agent/
│   ├── 06-quality-loop/
│   └── 07-multi-agent-registry/
│
├── bonus/
│   └── payments/                # 番外：独立小项目（需要钱包账号）
│
├── docs/
│   ├── 00-overview.md           # AgentCore 全景（含"不需要 ECS"）
│   ├── 01-capability-map.md     # 14 项能力详解 + 覆盖矩阵
│   ├── 02-prerequisites.md      # 区域 / 模型访问 / CLI / 权限（含命令冲突排查）
│   ├── 03-conventions.md        # 命名、标签、区域
│   ├── 04-cost-and-cleanup.md   # 成本模型与清理核对
│   ├── 05-capability-map.yaml   # ★ 机器可读覆盖清单（含 difficulty 与独立性子句）
│   ├── 06-difficulty-ladder.md  # ★ 难度刻度尺（§2.2 的公开版）
│   ├── 07-how-to-add-a-usecase.md  # ★ 用生成器加一例，并让 CI 通过
│   └── 99-troubleshooting.md
│
├── shared/
│   ├── scripts/
│   │   └── verify-coverage.py   # ★ 覆盖 + 实证 + 拷贝独立性 + 独立 + 命令五类校验
│   │                            #   （调度 / 自检 / 生成器 / 成本清单都收敛在根目录 aia.py）
│   └── templates/
│       ├── usecase-doc.template.md
│       ├── article.template.md
│       └── baseline-agent/      # ★ 最小独立 agent 骨架（被生成器复制；无 run.py / Makefile / smoke.py）
│           ├── app/{{AGENT_NAME}}/main.py
│           ├── app/{{AGENT_NAME}}/model/load.py
│           ├── app/{{AGENT_NAME}}/pyproject.toml
│           ├── tests/test_sanitize.py
│           └── agentcore/agentcore.json
│
└── .github/workflows/
    ├── usecase-ci.yml           #   改动哪个用例就只测哪个
    ├── independence-check.yml   # ★ 独立性：干净账号单例部署 + 标签断言
    ├── docs-link-check.yml
    └── eval-gate.yml            #   UC06：batch eval 分数下降则 block PR
```

### 5.1 与 v2 结构的对照

| | v2（阶段 / git tag） | v3（独立用例） |
|---|---|---|
| 代码位置 | `app/Emma/` 一个 agent 逐阶段长大 | `usecases/NN-*/app/aia_ucNN/` 每例自带 agent（CLI 官方布局） |
| IaC | `agentcore/agentcore.json` 一份配置叠加 | 每例一个独立 `agentcore/agentcore.json`（各自合成独立栈） |
| 独立性载体 | git tag | **目录 + 独立栈** |
| 从中间切入 | `git checkout stage-04` 后拿到的仍是那一个项目的状态 | 直接 `python aia.py up 04` |
| 并行部署 | 不可能（同一个栈） | **可能**（任意子集、任意顺序） |
| 共享代码 | 天然共享 | **不允许**（生成器复制，之后各自演进） |
| 文章位置 | `stages/*.md` + `articles/*.md` 两处 | `usecases/NN-*/README.md`（操作）+ `article.md`（叙事）同目录 |

### 5.2 命名与标签

| 项 | 约定 |
|---|---|
| AWS 资源前缀 | `aia_uc0X_`（如 `aia_uc03_orders`）。**不能用连字符**：CLI 对 `name` 的校验是 `^[a-zA-Z][a-zA-Z0-9_]{0,47}$`，连字符会被拒 |
| 标签 | `Project=agentcore-in-action`、**`UseCase=0X`**、`AutoDelete=true` |
| `UseCase` 标签的用途 | 支撑 §2.1 的独立性与清理断言 |
| 分支 | `uc-0X-<name>`；合并后不保留长期分支 |
| agent 名 | 每例自带名字（不是同一个角色逐阶段长大） |

---

## 6. 标准用例文档模板（十二节）

> 文件：`shared/templates/usecase-doc.template.md`。这是"开发者照着做就行"的落地保证。

| 节 | 内容 | 硬要求 |
|---|---|---|
| **1. 本用例结束时你会看到什么** | 一句话 + 真实截图 / GIF | 必须有真实运行截图 |
| **2. 独立性与难度定位** | 难度 D{x}（对照刻度尺说明为什么）+ 前置**知识** + 本用例覆盖能力 + **独立性声明** + **本用例内嵌的基线** | v3 新增，是独立用例的核心一节 |
| **3. 为什么需要这一层** | 不加会怎样（用真实痛点开头） | 这一段决定文章有没有张力 |
| **4. Architecture** | 架构图 + 组件职责 + 数据流 | 标出哪些是 AgentCore 托管、哪些是读者自己负责 |
| **5. Prerequisites** | 区域、模型访问、CLI 版本、IAM；**独立性前提一栏写"无（本用例自包含）"** | 给 `aia doctor` 一键自检 |
| **6. Cost & time** | 本用例总成本与耗时（独立用例不谈"累计"） | 必须给数字 |
| **7. Step-by-step** | ★ 每步四要素：**命令 / 预期输出 / 如何验证 / 失败修复** | 每步可复制粘贴，无省略号占位 |
| **8. Verify** | 证明每条能力的原生命令 + 它的真实输出（存档在 `evidence/`）+ 独立性证明 | 输出贴真实的，禁止编造 |
| **9. Troubleshooting** | 症状 → 原因 → 修复 | ≥ 5 条，含 ≥1 条本用例特有的坑 |
| **10. Cleanup** | 本用例销毁 + 标签核对（确认没留下其他用例的资源） | 清理路径必须验证过 |
| **11. What you repeated** | 为独立而内嵌的基线清单 | v2 没有这一节；独立性的诚实成本 |
| **12. Going further** | 延伸实验 + 官方文档 + 难度阶梯上的位置（上一档 / 下一档） | 链接可达 |

第 7 节表格格式（示例，UC04）：

| Step | Command | Expected output | Verify | If it fails |
|---|---|---|---|---|
| 4.1 建 policy engine | `agentcore add policy`（或控制台） | `engineId: pol-xxxx` | `aws bedrock-agentcore-control list-policy-engines` | `AccessDenied` → 检查 `BedrockAgentCoreFullAccess` |
| 4.2 自然语言生成策略 | … | 返回 Dogwood/Cedar 文本 | 人工读一遍，确认金额条件为 `<= 50` | 策略过宽 → 改手写 Cedar（见 4.3） |
| 4.3 先 Log-only | … | 越权请求**通过**但日志有记录 | 查 CloudWatch 日志组 | 无日志 → 确认网关关联了 policy engine |

---

## 7. 工程约定

| 项 | 约定 |
|---|---|
| **区域** | 全系列 `us-east-1`；**每条命令显式带 `--region`**（本机默认区是 ap-southeast-1） |
| **构建方式** | `CodeZip`（**不需要 Docker**）；文档注明何时该换 `Container` |
| **框架** | 主力 **Strands Agents**；UC03 / UC07 各留一个 **LangGraph** 变体证明框架无关 |
| **Python** | 3.10–3.14（CodeZip 支持范围，2026-10-15 按官方 schema `.llm-context/agentcore.ts` 修正），本系列用 3.11 + `uv` |
| **Node** | 20+（AgentCore CLI 要求） |
| **代码布局** | **CLI 官方布局**：agent 代码在 `app/<AgentName>/`，`codeLocation` 指向它；不自造 `src/`（2026-10-15 用户裁定，此前自造 `src/` 导致读者产物与文档不一致） |
| **图文同步（硬规则）** | **正文一改，图片必改**：任何正文改动（命令、数字、名称、结论、结构）收尾时必须 ① grep `gen_figures.py` 里正文出现过的关键数字/命令/术语（只 grep markdown 会漏掉画在 SVG 里的字符串）② 逐图对照正文 ③ 重出 PNG ④ 重生成 PPT ⑤ 目检渲染图 |
| **清理** | `agentcore remove all && agentcore deploy`（官方路径）+ `python aia.py down 0X` 封装；手动核对 S3 / 日志组 / Secrets Manager / token vault |
| **幂等** | `aia up` / `aia down` 可重复执行 |
| **跨平台** | 仓库内全部命令只依赖 Python 与已装 CLI；`aia.py` 无 Make / bash / WSL 依赖，Windows 原生可跑 |
| **用例边界** | 禁止跨用例 import；禁止跨栈引用；共享代码只能经生成器复制 |
| **CI** | 路径过滤 + 独立性检查 + 文档链接检查；UC06 额外跑 eval 门禁 |
| **敏感信息** | 仓库内禁明文凭证；`.env.example` 只放占位符；`gitleaks` 进 CI |
| **提交** | Conventional Commits（`feat(uc-04): …`） |

---

## 8. 文章计划

### 8.1 发布策略（沿用你已确立的矩阵）

| 用途 | 渠道 |
|---|---|
| 单一真相源 / 门户 | GitHub Pages（文章 Markdown 存在仓库里，Pages 直接发布） |
| 英文主阵地 | **Dev.to**（带 #awscommunity 身份流量） |
| 英文副本 | Medium (@pinxiong.cn)、Hashnode，canonical 指回 GitHub Pages |
| 社区分发 | Hacker News、Lobsters、Reddit (r/aws)、daily.dev |
| 中文（可选） | 微信公众号做深度解读版，不逐字翻译 |
| 不做 | LinkedIn、DZone、InfoQ |

节奏：**双周一篇**。7 篇 + 1 概览 + 1 番外 ≈ 4.5 个月。

**首发 UC01**（2026-10-14 决策 E：按难度阶梯顺序发）。UC01 的"从 `agentcore create` 到上线 30 分钟"是整条阶梯的入口，也是唯一能在一篇里把 Runtime、Observability、CodeZip、以及"你不需要 ECS"全部交代清楚的一篇；读者读完能立刻自己跑，这才是系列首发该干的活。研究型 agent（UC05）爽感最强，但放在 D4 才讲的工具组合上更自然，届时它也自带引流能力。独立用例的结构让"乱序发布"没有代价：读者点进来的那篇本身就是完整的。

### 8.2 标题方向

| # | 主标题 | 备选 |
|---|---|---|
| 00 | Amazon Bedrock AgentCore: 7 Independent Use Cases, 14 Capabilities | The AgentCore Field Guide, From Easy to Hard |
| 01 | From `agentcore create` to Production in 30 Minutes | AgentCore Runs Your Agent. You Do Not Need ECS. |
| 02 | Your Agent Does Not Have a Memory Problem. It Has a Memory Architecture Problem. | Short-Term, Long-Term, Episodic: What Your Agent Should Actually Remember |
| 03 | Turn Enterprise APIs into Agent Tools, Without Handing Over Your Credentials | Inbound vs Outbound: The Two Auth Problems Nobody Separates |
| 04 | Stop Writing Authorization Logic Inside Your Prompt | Why the Thing Enforcing Your Policy Must Not Be the Thing an Attacker Can Talk To |
| 05 | One API Call, Five Tools: How Research Agents Actually Get Built | Harness or Runtime? Building the Same Agent Two Ways |
| 06 | How Do You Know Your Agent Got Worse? | Closing the Quality Loop: Evaluations, Recommendations, and A/B Tests |
| 07 | Multi-Agent Systems Are Easy. Isolation, Protocol, and Traces Are Not. | Before You Build Another Agent, Search the Registry |
| 番外 | Your Agent Can Pay. Should It? | Spending Limits as a First-Class Control |

### 8.3 统一骨架（十二节，对齐官方样例 README）

1. **At a glance**（元信息表：agent 类型、用到的能力、框架与模型、构建方式、接口、区域、难度、官方分组）
2. **The problem**（业务场景，不谈技术）
3. **Why the obvious approach breaks**（先讲朴素做法的坑，张力来源）
4. **Architecture**（一张图）
5. **Walkthrough**（关键命令 + 真实输出，指向仓库目录，不堆全量代码）
6. **Verification**（真实运行输出 / 截图）
7. **Cleanup**（清理命令 + 说明哪些资源是故意留下的）
8. **What surprised me**（真实踩坑，决定能否被转发）
9. **When not to use this**（诚实说边界）
10. **Files**（每个路径一行：是什么、谁写的）
11. **Related official samples**（2·4 条官方样例路径 + 到那儿看什么）
12. **Try it yourself**（`cd usecases/NN-*` + 一键部署，强调不需要先做前面的用例）

第 1、7、10、11 节是 2026-10-15 从官方 `awslabs/agentcore-samples` 的样例 README 骨架里补进来的，
模板 `shared/templates/article.template.md` 已内置，**不要删**。官方骨架的对照见 `docs/08-official-alignment.md` §3.3。

每例的 README 还要多一节 **2.4 官方坐标**（官方分组 / 工作负载分类 / 业务垂直 / 可对照的官方样例），
四个字段与 `docs/05-capability-map.yaml` 里该用例的 `official:` 块一一对应。

---

## 9. 路线图

| 阶段 | 内容 | 完成标志 |
|---|---|---|
| **P0 地基** | 建仓库、`docs/`、生成器 `aia.py new`、`baseline-agent/` 模板、`verify-coverage.py`、`aia doctor` | 生成器能生成出一个能通过 CI 的空用例；五类校验全绿 |
| **P1 打底两档** | UC01（D1）+ UC02（D2）（+ 2 篇） | DoD 八条全绿；两例都能在干净账号单独部署 |
| **P2 跨过认证与裁决** | UC03（D3）+ UC04（D3） | 同上；UC04 的 Log-only → Enforce 可复现 |
| **P3 难度爬升** | UC05（D4）+ UC06（D4） | 同上；UC05 给 Harness 与 export 两条路径；UC06 A/B 有显著性截图 |
| **P4 封顶与分支** | UC07（D5）+ 番外 Payments | 同上；Registry 用新命名空间 |
| **P5 收口** | 概览文章 + 难度阶梯文档 + `python aia.py verify-all` 全绿 | 14 项覆盖矩阵全部有实证；难度序列单调 |

**每个用例 Definition of Done（八条，缺一不可）**

1. 干净账号里 `python aia.py up 0X` 成功（其他用例从未部署过）
2. `evidence/` 里每条声明的能力都有原生命令的存档，独立性由 `python aia.py check 0X` 通过
3. `python aia.py down 0X` 后 Cost Explorer 归零，且 `UseCase` 标签断言为空
4. 十二节文档齐全，每步有预期输出与失败修复
5. 至少一张真实运行截图
6. `article.md` 初稿完成
7. `docs/05-capability-map.yaml` 里的声明与 `evidence/` 里的实证一致（CI 校验）
8. `docs/06-difficulty-ladder.md` 里的难度声明与 §2.2 刻度一致，且难度序列仍单调不减

---

## 10. 已拍板（2026-10-14）

六项全部落定，规划、能力清单、README 与校验器已对齐。

| # | 决策 | 结论 |
|---|---|---|
| **A** | 用例数量 | **7 个用例 + 1 番外**（D1→D5）。D3 与 D4 各两例是刻意的：UC03/UC04 是"接入 vs 限制"，UC05/UC06 是"工具 vs 质量"，合并会变成一锅粥 |
| **B** | UC07 是否拆两例 | **不拆**。一例两篇主题（多 agent 协议 / Registry）。因为拆开后两半**依然独立**，将来要拆代价很低 |
| **C** | 接受"每例自带基线"的重复吗 | **接受**。这是真独立的必要条件，不是实现缺陷；用生成器把重复成本压到最低，并在每例 README 第 12 节（*What you repeated*）如实交代 |
| **D** | 仓库文档语言 | **英文为主**。仓库是英文文章的落地页；`README.zh-CN.md` 可选，且不逐字同步 |
| **E** | 发布顺序 | **按难度阶梯顺序**，首发 UC01。独立结构让乱序发布无损，但连载的价值本来就在于难度曲线 |
| **F** | 是否先跑一遍 | **是**。UC01 在真实账号跑通后才写文档，区域 / 配额 / 模型访问 / CLI 行为全部**来自实测**而非来自文档 |

### 10.1 由 F 项实测得到的环境事实（这不是预研，是已经发生的事）

| 项 | 实测结果 |
|---|---|
| AWS 身份 | 账号 `123456789012`，IAM user `xiongpin`，`sts get-caller-identity` 通过 |
| **默认区域** | `ap-southeast-1`（**不是 us-east-1**）→ 所有命令必须显式 `--region us-east-1` |
| Bedrock `us-east-1` | 可达，Claude 系列模型可见（`list-foundation-models` 返回完整列表） |
| Node / npm | v22.22.2 / 10.9.7，满足 CLI 的 Node 20+ 要求 |
| GNU Make | 3.81（macOS 自带；不支持 `.ONESHELL`，本仓库未使用） |
| Docker | **未安装** → 正是 `CodeZip` 路线存在的意义 |
| CDK CLI | 未单独安装；`agentcore deploy` 内部自带 CDK 调用路径 |

### 10.2 官方对齐拍板（2026-10-15 调研 awslabs/agentcore-samples 后）

完整调研见 [`docs/08-official-alignment.md`](docs/08-official-alignment.md)。

| # | 决策 | 结论 |
|---|---|---|
| **G** | 技术路线 | **CLI 为主 + `raw/` boto3 对照**。官方是刻意分两条路的：`01-features` 用 boto3（原文：`full visibility into every API call is the point of educational content`），`getting-started`/`IaC`/`blueprints` 用 CLI。我们两条都要：主路线保证读者产物与官方一致，`raw/` 保证看得见 API 层 |
| **H** | 身份鉴权是否单独成篇 | **不单独成篇，并入 UC03**。UC03 深挖 inbound JWT + 一种 3LO，M2M / OBO / 多 IdP 降为例内高级节 |
| **I** | 篇章结构 | **保留难度阶梯，叠加官方坐标**。官方没有难度阶梯，这是本系列的差异点；但每个用例必须带 `official.group / category / vertical / samples` 四个坐标，否则读者无法把它映射回官方分类 |
| **J** | A0 是否回填官方四块 | **四块全补**：元信息表、Cleanup、Files、Related official samples。官方骨架对照见 §8.3 |

由此**新增的两条硬约定**：

1. **能力数口径必须标出处**。AWS 文档核心服务表 13 项（无 Web Search，含 Optimization），samples 的 `01-features` 表 13 项（含 Web Search，无 Optimization），并集才是我们的 14 项。任何地方写「14 项」都要能对上 `docs/05-capability-map.yaml` 的 `capabilities[].src`。
2. **写进文档的命令必须在本机 CLI 里存在**。`verify-coverage.py` 的 `[CMD]` 校验会用 `Usage:` 行核对 `cli:` 字段里的命令、子命令与 flag。这条是被真实错误逼出来的：计划里曾出现 `agentcore create --harness` 与（照抄官方 samples 根 README 的）`agentcore add identity`，两者都不存在。

### 10.3 「拷贝即独立」拍板（2026-10-16）

用户提出的原话是：**每个 usecase 都是可以独立运行的，copy any folder and it runs independently。** 审计后确认：此前 I1–I5 描述的是**部署期**独立，而**操作入口全在仓库根**（`aia.py doctor/up/test/down`），文档里甚至写着 `cd ../..` 回到仓库根，所以把 `usecases/01-first-agent/` 单拷出来是一个死目录。这句话当时是承诺，不是事实。

| # | 决策 | 结论 |
|---|---|---|
| **K** | 入口放哪 | **放进每个用例目录**（2026-10-16 结论）。新增 `run.py`（唯一实现）、`Makefile`（只转发）、`AGENTS.md`、`tests/doctor.py`、`tests/copy_check.py`；契约加 **I6 拷贝即独立**。**2026-10-18 反转：入口不再放进目录**，这五个文件全部删除（见 §10.4） |
| **L** | 为什么是 `run.py` 而不是 Make 或 shell | 根 README 原有约定是"所有命令走 Python，不用 Make"，为的是 macOS / Linux / Windows 一致。用 Makefile 当唯一入口会推翻这条约定，所以 Makefile 降级为转发层，`run.py` 是唯一实现。**2026-10-18 反转：两个入口都不要，入口是 `agentcore` 本身**（见 §10.4） |
| **M** | I6 怎么验证 | 用例自带 `tests/copy_check.py`（2026-10-16 结论）。**2026-10-18 反转**：仓库级 `[COPY]` 类**读取目录**（逃逸路径、禁用脚本、合约标签与 `codeLocation`、部署目标），用例目录里不再有任何检查脚本 |
| **N** | 生成器与模板 | `aia.py new` 生成骨架；两份文档模板同步改写，**禁止写仓库根命令**；删除 `diagrams/`（官方布局没有），生成 `agentcore/.gitignore`（此前漏了，会让 `agentcore/.env.local` 被提交）。2026-10-18 起生成器改为生成 `evidence/` 与仅含单元测试的 `tests/`，不再生成 K 里的五个文件 |

**由此新增的一条硬约定（仍然有效）**：**用例文档与代码里不得出现指向目录之外的路径**。`agentcore` / `aws` 是唯一允许出现在用例文档里的操作形式；仓库级调度器只在完整仓库的语境里提，且要显式说明"如果你手上有完整仓库"。这条由仓库级 `[COPY]` 类断言（父目录跳转、绝对路径、仓库级共享目录、仓库级脚本四类模式）。

**实测结果**：UC01 `python3 run.py check` → `16 passed, 0 failed`；生成器新造的用例 → `15 passed, 0 failed`（2026-10-16 口径，随 K/L/M 的反转作废）。

---

### 10.4 「原生命令 + evidence/」拍板（2026-10-18）

K/L/M 的代价在写完两篇用例后变得无法接受：**系列要教的是 AgentCore CLI，而目录里的 `run.py` 把 CLI 挡在了读者身后**。读者照文档跑的是 `make deploy`，学到的是我们的包装；文章里每一条命令都不是读者能在自己终端里复现的原生命令。于是拍板：

| # | 决策 | 结论 |
|---|---|---|
| **O** | 用例目录里有什么 | `app/`、`agentcore/agentcore.json`、`agentcore/aws-targets.json`、`evidence/`、`README.md`，以及可选的 agent 自身 Python 的 pytest。**没有** `run.py`、`Makefile`、`tests/doctor.py`、`tests/smoke.py`、`tests/copy_check.py` |
| **P** | 能力怎么证明 | 用原生命令的输出，存档到 `evidence/`。曾经的 `CAPABILITY_ASSERTIONS` 字典取消：断言写在脚本里不等于被证明，读者无法复现。典型命令：`agentcore status`、`agentcore invoke --prompt`、`agentcore traces list`、`agentcore traces get <id>`（过 `jq`）、`aws resourcegroupstaggingapi get-resources` |
| **Q** | I6 怎么验证 | 仓库级校验**读目录**（见 §2.4 的 `[COPY]`），不再执行目录里的任何脚本 |
| **R** | 销毁命令 | `agentcore remove all -y` 清空合约，**再跑一次 `agentcore deploy -y --target default`** 才真正把栈收敛到空。`-y` 不可省：非交互 shell 里它会以"requires an interactive terminal"退出 |
| **S** | 文章里的输出 | 每条命令的输出是**图**，不是代码块；同一份输出打印两遍（一次文本一次图）是阻塞缺陷。GitHub 链接一律 `/tree/master/` |

**由此新增的一条硬约定**：**没有 `evidence/` 存档的能力，不能写进文章**。推论：跑不通的步骤不上文章，编造的截图比缺失的章节更糟。

`aia.py` 相应收敛：`test` 目标删除（能力证明不再是一条命令），`verify` 随之删除（它等于 `check`），`check` 改为委托 `verify-coverage.py`；`down` 补上 `-y`。

---

## 11. 风险与注意事项

| 风险 | 影响 | 对策 |
|---|---|---|
| 服务演进快（14 项里 8 项是 2026 年才 GA 的） | 文章 6 个月后过时 | 每篇顶部标注"验证于 YYYY-MM-DD"；成熟度写进正文 |
| **区域割裂** | 读者在你没写的区域跑不通 | 全系列锁 `us-east-1`，前置条件显式说明 |
| **Registry 命名空间迁移** | 照旧资料做必踩 | UC07 单列"避坑"小节；README 故障排查表置顶 |
| **`agentcore` 命令冲突** | `agentcore --version` 报错，读者卡第一步 | `aia doctor` 自动检测并提示 `pip uninstall bedrock-agentcore-starter-toolkit` |
| **独立性的重复成本** | 维护 7 套骨架容易漂移 | 生成器统一生成；CI 校验 I3/I4/I6；文档第 11 节如实列出重复项 |
| **目录里混进自建运维脚本** | 读者学到的是包装，不是 CLI；7 份实现各自漂移 | 已删除（§10.4）：`[COPY]` 类把五个禁用文件名列为硬失败，仓库级校验读目录而非执行脚本 |
| **用例文档里混进仓库根命令** | 目录被拷走后命令全失效，I6 沦为口号 | 仓库级 `[COPY]` 类扫描四类逃逸模式（父目录跳转 / 绝对路径 / 仓库级共享目录 / 仓库级脚本），文档模板明令禁止 |
| **用例难度声明失真** | 阶梯名不副实，读者预期落空 | 难度只按 §2.2 的可量化刻度声明；CI 校验单调性与刻度区间 |
| **Harness vs Runtime 定位混淆** | 读者选错路径 | UC05 用同一场景两种实现做正面对比 |
| **Payments 前置门槛** | 读者卡在第一步 | 番外给 sandbox / 测试网路径 + 无钱包账号降级演示 |
| **成本失控** | 读者被账单吓到 | 每例给数字；`AutoDelete` 标签；`python aia.py cost` |
| **官方口径漂移** | 照抄过时写法（官方 samples 根 README 自己就写着不存在的 `agentcore add identity`），或能力数出处混用 | `[CMD]` 校验兜住命令；`capabilities[].src` 兜住出处；`docs/08-official-alignment.md` 附可复核命令，季度重核 |
| **配额**（并发 session、Bedrock TPM） | UC07 压测失败 | 文档给配额申请指引；压测默认降到 10 并发 |
