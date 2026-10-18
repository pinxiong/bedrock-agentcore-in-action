# UC0X · {{UC_TITLE}}

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 0X · **Difficulty**: **D{{DIFFICULTY}}** · **Region**: `us-east-1`
> **Verified on**: 2026-XX-XX · **Cost**: $X · **Time**: X min
> **Capabilities**: `{{cap-1}}`（深挖）· `{{cap-2}}`（深挖）· `{{cap-3}}`（附带）
> **Standalone**: yes。这个目录不依赖任何其他用例，也不需要仓库里的其他文件。把它拷到任何地方，它照样能跑（见 §2.4）。

> 文中的账号 ID 一律脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

<!-- 写作规则（提交前删除本节）：
     · 标题请补上中文名，例：# UC04 · Policy（策略边界）。
     · 每个 Step 必须是"复制粘贴就能跑"的完整命令，禁止出现 ... 占位。
     · 命令一律是 `agentcore ...` / `aws ...` 原生命令，禁止写 make 目标和仓库根脚本：
       目录必须能被单独拷走，任何依赖仓库根的写法都会让独立性校验失败。
     · 每张预期输出必须是真实终端输出，禁止编造；存档到本目录的 evidence/。
     · 凡是可能失败的地方，必须同时给 Verify 和 If it fails 两列。
     · §6 成本必须给数字。本系列用例相互独立，不谈"累计成本"。
     · §8 必须包含两类证明：能力证明（原生命令输出，存 evidence/）与独立性证明
       （目录内没有任何路径指向目录之外，由仓库级校验脚本读取目录得出）。
     · §10 的清理路径要自己验证过；§11 必须如实列出为独立而内嵌的基线。
     · 中文文档面向你本人评审；article.md 的成稿是英文。
     · 图放与本 README 同级新建的 `images/` 目录（`![](images/result.png)`）。 -->

---

## 1. 本用例结束时你会看到什么

一句话：{{这个用例跑完，读者能亲眼看到什么}}。

跑完之后你会得到一个：

- {{可观察产物 1，例：可以对话的 endpoint ARN}}
- {{可观察产物 2，例：CloudWatch 里一条包含 3 个工具 span 的 trace}}
- {{可观察产物 3，例：一个被策略明确拒绝的越权请求}}

---

## 2. 独立性与难度定位

### 2.1 为什么是 D{{X}}

对照本系列共用的难度刻度尺（四维取最高维：新增能力数 / 新增外部依赖 / 必须理解的机制 / 参考耗时）：

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | {{N}}（{{列举}}） | ≤ {{上界}} ✅ |
| 新增外部依赖 | {{无 / 1 个 AWS 资源 / 身份系统 / 多服务}} | {{…}} ✅ |
| 必须理解的机制 | {{部署模型 / 状态 / 认证与裁决 / 评测与统计 / 协议与并发}} | {{…}} ✅ |
| 参考耗时 | {{X}} min | ≤ {{上界}} ✅ |

**难度上升的实际含义**：{{一句话说明本用例比上一档多了什么认知负担}}。

### 2.2 前置**知识**（不是前置资源）

- {{知识点 1，例：知道什么是 session}}
- {{知识点 2}}

> 没读过前面的用例也能做。上面这些是**概念**，不是必须存在的资源。
> 如果某个概念你没接触过，看 §12 的链接，不用先把前面的用例跑一遍。

### 2.3 独立性声明

本用例满足六条独立性契约。每一条都能在你自己的终端里验证：

| # | 条件 | 本用例如何成立 | 怎么验证 |
|---|---|---|---|
| I1 | 部署独立 | `agentcore deploy -y --target default` 即可完成，不读取任何其他用例的 stack 输出 | 干净账号里跑一次这条命令 |
| I2 | 清理独立 | 所有资源带 `UseCase=0X` 标签，`agentcore remove all -y` + `agentcore deploy` 只销毁本用例 | §8 的 tag 查询 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 是本例唯一的资源声明，无跨栈引用 | 仓库级校验（见 §8.3） |
| I4 | 代码独立 | `app/{{AGENT_NAME}}/` 不 import 任何其他用例 | 仓库级校验（见 §8.3） |
| I5 | 文档独立 | 本节以上即为全部前置**知识**，没有"必须先跑完某用例" | 通读本文 |
| I6 | **拷贝即独立** | 目录内没有任何路径指向目录之外，整份目录自包含 | 仓库级校验（见 §8.3），它逐行读取目录 |

### 2.4 「拷贝即独立」是什么意思

把这一份目录拷到任何地方，不带着仓库剩余部分，它仍然是完整可跑的工程：

```bash
cp -r usecases/{{UC_SLUG}} /tmp/{{UC_ID}}
cd /tmp/{{UC_ID}}
agentcore validate                    # 合约自检
agentcore deploy -y --target default  # 部署
agentcore status                      # 状态
agentcore invoke --prompt "..."       # 调用
agentcore remove all -y               # 销毁：先清空合约
agentcore deploy -y --target default  # 再由这一次 deploy 把栈收敛到空
```

这不是一句承诺。仓库级校验（见 §8.3）会**逐行读取这个目录**，逐项验证：

1. 运行所需的文件（`AGENTS.md` / `agentcore/` 合约 / `app/{{AGENT_NAME}}/` / `README.md`）都在目录内；
2. 目录内没有任何文件指向目录之外（父目录跳转、绝对路径、仓库级共享目录、仓库级脚本）；
3. 合约自包含：`codeLocation` 落在目录内、三个标签齐全、部署目标有 region；
4. 目录里不存在本系列禁用的自建运维脚本（`run.py` / `Makefile` / `tests/doctor.py`
   / `tests/smoke.py` / `tests/copy_check.py`）：本系列教的是 CLI，不是包装脚本。

> 拷贝到自己的账号后，第一件事是改 `agentcore/aws-targets.json` 里的 `account`，
> 并删掉 `agentcore/.cli/deployed-state.json`（它记的是作者那次部署的状态）。
> `aws sts get-caller-identity` 拿到的账号应与 `aws-targets.json` 一致。

### 2.5 官方坐标（对齐 awslabs/agentcore-samples）

本用例的能力在官方样例仓库里的位置，方便你对照另一种写法：

| 坐标 | 值 |
|---|---|
| 官方分组 | `{{八个分组之一}}` |
| 工作负载分类 | `{{conversational-agents / workflow-automation-agents / coding-assistants}}`（官方按"有没有用户在环"分三类） |
| 业务垂直 | {{例：Retail / E-commerce}} |
| 可对照的官方样例 | `{{NN-layer/NN-group/NN-sample/}}` |

差异点在于：官方按**能力**组织样例，本系列按**难度**组织用例，并额外要求每个用例自证独立（I1 到 I6）。官方坐标只用来定位，不改变本例的独立性。

<!-- 如果你在 raw/ 下真的写了 boto3 对照脚本，保留下面这段；否则整段删掉：
**本目录的两条路线**（对齐官方刻意分开的两种教学形态）：
- 主路线：`agentcore` CLI，可部署产物与官方 `00-getting-started` 一致，读者照抄即得；
- 对照路线：`raw/` 下的 boto3 脚本（控制面 `bedrock-agentcore-control` + 数据面 `bedrock-agentcore`），
  只用于教学，把 CLI 替你做的那几个 API 调用摊开。官方 `01-features` 就是这个做法。
-->

---

## 3. 为什么需要这一层

{{用一个真实痛点开头，一段话。例："上一档的 agent 记得住你，但它仍然只会说话，
用户问'我的订单到哪了'，它只能回答'我无法查询订单'。"}}

{{不加这一层会怎样：读者最可能想到的朴素做法是什么，它在生产里会怎么坏。
这一段是文章"张力"的来源，写得越具体越好。}}

---

## 4. Architecture

| 组件 | 职责 | AgentCore 托管？ |
|---|---|---|
| {{组件}} | {{职责}} | 是 / 否 |

**数据流**：{{1 → 2 → 3，标出哪一步由 AgentCore 托管、哪一步是读者自己负责}}

**为什么这样设计**：{{关键取舍，一段话}}

---

## 5. Prerequisites

| 项 | 要求 | 自检命令 |
|---|---|---|
| AWS 账号 | 可创建 Bedrock AgentCore 资源 | `aws sts get-caller-identity` |
| 区域 | **us-east-1**（本系列统一） | `aws configure get region` |
| AgentCore CLI | Node.js 20+ / `@aws/agentcore` | `agentcore --version` |
| 命令冲突 | 旧的 Python `agentcore` 会遮蔽 npm 版 | `pip uninstall bedrock-agentcore-starter-toolkit` |
| Python | **3.10–3.14**（CodeZip 支持范围），本系列用 3.11 + `uv` | `python3 -V && uv --version` |
| 模型访问 | Bedrock 默认已开基础模型 | `aws bedrock list-foundation-models --query 'modelSummaries[?modelId==\`{{model-id}}\`]'` |
| Docker | **本用例不需要**（CodeZip） | 不适用 |
| **其他用例** | **不需要。本用例自包含** | 不适用 |
| **仓库其余部分** | **不需要。仓库级校验会读目录验证这一点** | 见 §8.3 |
| {{第三方依赖}} | {{例：Cognito user pool，由本用例创建}} | {{…}} |

一键自检（在本目录执行，这两条命令也是自我完备的）：

```bash
agentcore --version
aws sts get-caller-identity
```

### 5.1 最小权限（生产用法）

```json
{{本用例真正需要的最小 IAM policy，不要贴 * }}
```

---

## 6. Cost & time

| 项 | 本用例 |
|---|---|
| 预估花费 | **${{X}}** |
| 最贵的一项 | {{资源}} ≈ ${{X}} |
| 预计耗时 | {{X}} min |

⚠️ 常见超支点：{{例：忘记删 CloudWatch 日志组 / Browser 会话空转 / Memory 事件量}}

```bash
agentcore remove all -y                   # 在本目录执行，清空合约
agentcore deploy -y --target default      # 再由这一次把本用例的资源收敛到空
```

---

## 7. Step-by-step

> 下面所有 `agentcore` 命令都必须在**用例根目录**执行；
> 在 `agentcore/` 子目录里执行会报 `Please run this command from your project root directory.`
> 每条命令的输出都要存档到本目录的 `evidence/`，文件名写明是哪条命令。

### 7.1 {{步骤名}}

```bash
{{完整命令}}
```

**预期输出**

```text
{{真实输出}}
```

**如何验证**：{{一条独立的确认命令，或其输出特征}}

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `{{错误信息}}` | {{原因}} | {{修复}} |

---

### 7.2 {{步骤名}}

```bash
{{完整命令}}
```

**预期输出**

```text
{{真实输出}}
```

**如何验证**：{{…}}

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `{{错误信息}}` | {{原因}} | {{修复}} |

---

<!-- 按需重复 7.x。每步保持 命令 / 预期输出 / 验证 / 失败修复 四要素 -->

---

## 8. Verify

两类证明，都在本目录执行。没有断言脚本：能力靠原生命令的输出证明，独立性靠
目录自身的内容证明。

```bash
agentcore status                 # 这个用例部署了什么
agentcore invoke --prompt "..."  # 它真的会回答
agentcore traces list            # 它留下了 trace
```

### 8.1 能力证明（原生命令的输出）

**期望输出**：把每一条命令的真实输出贴到这里，同时存档到 `evidence/`。

```text
{{真实输出}}
```

核心证明：

1. {{证明 1 ⇒ 对应 docs/05-capability-map.yaml 里 usecases[uc0X].assertions[0]，
   并写明是哪条命令的哪一行输出证明了它}}
2. {{证明 2}}
3. {{证明 3}}

### 8.2 独立性证明（目录自包含）

目录内没有任何路径指向目录之外，且不含本系列禁用的自建运维脚本。这一条由
仓库级校验读取目录得出（见 §8.3），用例目录里不自带任何检查脚本。

**tag 层面的独立性**（上面查的是本地声明，这一条查的是 AWS 上的实际资源）：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values={{其他用例编号}}
# 期望：ResourceTagMappingList 为空，证明本用例没有顺手创建别人的资源
```

### 8.3 完整仓库里的额外一层

如果你手上是完整仓库，仓库根还有一层系列级校验（能力覆盖 / `evidence/` 里有没有
对应存档 / 目录自包含 / 难度单调 / 跨栈引用 / 命令是否存在）。它是仓库级工具，
通过**读取**本目录来判断，用例之间不需要共享任何代码，单独拷走本目录时也不需要它。

---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{本用例特有的坑}} | {{原因}} | {{修复}} |
| 独立性校验报某文件 points outside itself | 目录里混进了指向外部的路径 | 按报出的行号改回目录内相对路径 |

> 配额、区域、凭证、`agentcore` 命令冲突等跨用例的通用故障，完整仓库里另有一份汇总
> （`docs/99-troubleshooting.md`）。单独拷走本目录时不需要它。

---

## 10. Cleanup

**销毁本用例**：

```bash
agentcore remove all -y && agentcore deploy -y --target default
```

{{把你实测用的那条命令写在这里}}

手动核对清单（不被 CLI 纳管的残留）：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/...`
- [ ] S3 存储桶（CodeZip 产物 / Browser / Code Interpreter 输出）
- [ ] Secrets Manager 里的凭证
- [ ] AgentCore Identity token vault 条目
- [ ] `agentcore/agentcore.json` 被 `remove all` 改写过，要再部署请先恢复它
- [ ] {{本用例特有资源}}

**确认清空，且没有波及别的用例**：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=0X
# 期望：ResourceTagMappingList 为空，且任何其他 UseCase 的资源数量不变
```

---

## 11. What you repeated（为独立而内嵌的基线）

本用例是自包含的，因此内嵌了以下本可以共享的东西。如实列出，避免你误以为
这是一个微服务仓库的最佳实践。

| 内嵌内容 | 规模 | 为什么不能共享 |
|---|---|---|
| {{最小 agent 骨架}} | {{1 个文件，约 N 行}} | 共享即会破坏 I4（代码独立） |
| {{IaC 栈骨架}} | {{CDK app 入口 + 标签}} | 共享即会破坏 I3（栈独立） |
| `AGENTS.md` | 1 个文件 | 共享即会破坏 I6（拷贝即独立）：入口一旦在目录外，目录就不能单独拷走 |
| {{其他}} | {{…}} | {{…}} |

> 这些骨架由系列的用例生成器从一个基线模板**复制**进来，只写一次，然后各自演进。
> 生成器和模板本身不参与运行，所以删掉它们也不影响本目录：本目录的运行只依赖
> `agentcore` 与 `aws` 两个命令。

---

## 12. Going further

- 延伸实验：{{3 条具体的、可动手的改进方向}}；I6 的硬性要求是目录内不出现指向外部的路径，也不出现自建运维脚本
- 官方文档：{{本用例涉及能力的 doc 链接}}
- 难度阶梯上的位置：上一档 {{上一档用例名，写名字不写相对路径}} · 下一档 {{下一档用例名}}
- 文章版：`article.md`
