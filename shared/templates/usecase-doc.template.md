# UC0X · {{UC_TITLE}}

> **Series**: [AgentCore in Action](../../README.md) · **Use case**: 0X · **Difficulty**: **D{{DIFFICULTY}}** · **Region**: `us-east-1`
> **Verified on**: 2026-XX-XX · **Cost**: $X · **Time**: X min
> **Capabilities**: `{{cap-1}}`（深挖）· `{{cap-2}}`（深挖）· `{{cap-3}}`（附带）
> **Standalone**: yes. This use case does not require any other use case to be deployed.

<!-- 写作规则（提交前删除本节）：
     · 标题请补上中文名，例：# UC04 · Policy（策略边界）。
     · 每个 Step 必须是"复制粘贴就能跑"的完整命令，禁止出现 ... 占位。
     · 每张预期输出必须是真实终端输出，禁止编造。
     · 凡是可能失败的地方，必须同时给 Verify 和 If it fails 两列。
     · §6 成本必须给数字。本系列用例相互独立，不谈"累计成本"。
     · §8 必须包含独立性断言；§10 的清理路径要自己验证过。
     · §11 必须如实列出为独立而内嵌的基线，不许含糊。
     · 中文文档面向你本人评审；article.md 的成稿是英文。 -->

---

## 1. 本用例结束时你会看到什么

一句话：{{这个用例跑完，读者能亲眼看到什么}}。

![result](diagrams/result.png)

跑完之后你会得到一个：

- {{可观察产物 1，例：可以对话的 endpoint ARN}}
- {{可观察产物 2，例：CloudWatch 里一条包含 3 个工具 span 的 trace}}
- {{可观察产物 3，例：一个被策略明确拒绝的越权请求}}

---

## 2. 独立性与难度定位

### 2.1 为什么是 D{{X}}

对照 [难度刻度尺](../../docs/06-difficulty-ladder.md)：

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

本用例满足五条独立性契约（见 [README](../../README.md#the-independence-contract)）：

| # | 条件 | 本用例如何成立 |
|---|---|---|
| I1 | 部署独立 | `python aia.py up 0X`（仓库根执行）即可完成，不读取任何其他用例的 stack 输出 |
| I2 | 清理独立 | 所有资源带 `UseCase=0X` 标签，`python aia.py down 0X` 只销毁本用例 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 是本例唯一的资源声明，各例独立合成栈，无跨栈引用 |
| I4 | 代码独立 | `app/{{AGENT_NAME}}/` 不 import 任何其他用例 |
| I5 | 文档独立 | 本节以上即为全部前置 |

### 2.4 官方坐标（对齐 awslabs/agentcore-samples）

| 坐标 | 值 | 说明 |
|---|---|---|
| 官方分组 | `{{八个分组之一}}` | 分组名见 [docs/08-official-alignment.md](../../docs/08-official-alignment.md) |
| 工作负载分类 | `{{conversational-agents / workflow-automation-agents / coding-assistants}}` | 官方按「有无用户在环」分三类 |
| 业务垂直 | {{例：Retail / E-commerce}} | 官方 use-cases 表有同样一列 |
| 可对照的官方样例 | `{{NN-layer/NN-group/NN-sample/}}` | 同一能力的另一种写法，读者可跳过去看 |

> 本系列的差异点是**难度阶梯**（官方没有难度阶梯），官方坐标只用来定位，不改变本例的独立性。

**本目录的两条路线**（对齐官方刻意分开的两种教学形态，见 docs/08-official-alignment.md §3.1）：

- 主路线：`agentcore` CLI。可部署产物与官方 `00-getting-started` 完全一致，读者照抄即得；
- 对照路线：`raw/` 下的 boto3 脚本（控制面 `bedrock-agentcore-control` + 数据面 `bedrock-agentcore`），
  只用于教学，把 CLI 替你做的那几个 API 调用摊开。官方 `01-features` 就是这个做法。

---

## 3. 为什么需要这一层

{{用一个真实痛点开头，一段话。例："上一档的 agent 记得住你，但它仍然只会说话，
用户问'我的订单到哪了'，它只能回答'我无法查询订单'。"}}

{{不加这一层会怎样：读者最可能想到的朴素做法是什么，它在生产里会怎么坏。
这一段是文章"张力"的来源，写得越具体越好。}}

---

## 4. Architecture

![architecture](diagrams/architecture.svg)

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
| Python | **3.10–3.13**（CodeZip 支持范围），本系列用 3.11 + `uv` | `python3 -V && uv --version` |
| 模型访问 | Bedrock 默认已开基础模型 | `aws bedrock list-foundation-models --query 'modelSummaries[?modelId==\`{{model-id}}\`]'` |
| Docker | **本用例不需要**（CodeZip） | 不适用 |
| **其他用例** | **不需要。本用例自包含** | 不适用 |
| {{第三方依赖}} | {{例：Cognito user pool，由本用例创建}} | {{…}} |

一键自检：

```bash
python aia.py doctor --usecase 0X
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
python aia.py down 0X      # 在仓库根执行
```

---

## 7. Step-by-step

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

```bash
python aia.py test 0X       # 等价于 python tests/smoke.py --usecase 0X
```

**期望输出**

```text
{{真实输出}}
```

核心断言：

1. {{断言 1 ⇒ 对应 docs/05-capability-map.yaml 里 usecases[uc0X].assertions[0]}}
2. {{断言 2}}
3. {{断言 3}}

**独立性断言**（每个用例都有，最后一条）：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values={{其他用例编号}}
# 期望：ResourceTagMappingList 为空，证明本用例没有顺手创建别人的资源
```

---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{症状}} | {{原因}} | {{修复}} |
| {{本用例特有的坑}} | {{原因}} | {{修复}} |

> 通用故障（配额、区域、凭证、`agentcore` 命令冲突）见 [`docs/99-troubleshooting.md`](../../docs/99-troubleshooting.md)。

---

## 10. Cleanup

**销毁本用例**：

```bash
python aia.py down 0X
# 或
agentcore remove all && agentcore deploy
```

手动核对清单（不被 CLI 纳管的残留）：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/...`
- [ ] S3 存储桶（CodeZip 产物 / Browser / Code Interpreter 输出）
- [ ] Secrets Manager 里的凭证
- [ ] AgentCore Identity token vault 条目
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
| {{其他}} | {{…}} | {{…}} |

> 这些骨架由 `python aia.py new` 从 `shared/templates/baseline-agent/`
> 生成而来，只写一次，然后各自演进。

---

## 12. Going further

- 延伸实验：{{3 条具体的、可动手的改进方向}}
- 官方文档：{{本用例涉及能力的 doc 链接}}
- 难度阶梯上的位置：上一档 {{上一档用例链接}} · 下一档 {{下一档用例链接}}
- 文章版：`article.md`
