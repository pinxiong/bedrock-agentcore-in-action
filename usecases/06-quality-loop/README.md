# UC06 · Quality Loop（可观测、可评测、可优化：找到坏掉的那一步）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 06 · **Difficulty**: **D4** · **Region**: `us-east-1`
> **Verified on**: 2026-10-25 · **Cost**: 约 $1.5（DeepSeek 按量计费，90+ 次模型调用与 3 次批量评审）· **Time**: 约 300 min
> **Capabilities**: `observability`、`evaluations`、`optimization`、`versioning-and-endpoints`（深挖）· `gateway`（A/B 分流，附带）
> **Standalone**: yes。这个目录不依赖任何其他用例；`agentcore/cdk/` 是内嵌的部署栈基线。

> 文中的账号 ID 一律脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：一个上线两个月、被植入了陈旧指令的费用审计 agent，被一整条质量回路
当场抓住并修好——22 个工具 span 里 0 次 `convert_currency` 暴露失败模式；
四种评测模式全部执行（按需 0.00、批量 0.50/11 会话、数据集 0.50/6 场景、
在线评测给 A/B 计分）；insights 把 17 个会话聚成 "Foreign Currency Ignored
Despite Receipt Metadata"（8 会话）并给出 `SYSTEM_PROMPT_FIX`；recommendation
基于 Correctness 重写提示词；修复以不可变 config-bundle v2（`d4c45b72`）上线，
A/B 报告 mean 2.0→4.0、CI [1.00, 3.00]、p=0.00043；CI 门禁在批量评测回归时
退出 1 阻断 PR。

证据（`evidence/`）：`30-invoke-prod-*`（10 次缺陷会话，6 次非 USD 全错）·
`36-spans-prod.json`（22 工具 span、零换汇）· `50`/`51`/`54`（三种离线评测）·
`60`/`61`（insights）· `62`/`67`（recommendation 拒绝与成功）·
`69`/`70`/`72`（bundle v2、A/B 启动、报告）· `80`/`81`/`82`（CI 门禁三条路径）·
`84`/`85`（runtime 版本与 endpoint 钉住）· `86`/`87`/`93`（独立性）·
`90`/`91`/`92`（teardown 三步）。

## 2. 独立性与难度定位

### 2.1 为什么是 D4

| 刻度项 | 本用例 | 是否达标 |
|---|---|---|
| 新增能力数 | 4（observability、evaluations、optimization、versioning-and-endpoints） | ≤ 4 ✅ |
| 新增外部依赖 | 无新增 AWS 资源类；多两行 Python 依赖（ADOT distro） | ✅ |
| 必须理解的机制 | 评测与统计（抽样、置信区间、p 值）+ 版本化与 endpoint 钉住 | ✅ |
| 参考耗时 | 300 min（含 5 次 deploy，每次约 5-7 min；insights/recommendation 各 2-4 min） | ✅ |

**难度上升的实际含义**：D3 的策略是"给定输入、确定性拒绝"；本档要求对
概率性输出建立质量证据链——单次通过不再说明问题，你需要分布、基线和统计
显著性。

### 2.2 前置知识（不是前置资源）

- 知道什么是 session、runtime endpoint
- 假设检验的直觉：置信区间与 p 值在比较两个均值时意味着什么
- OpenTelemetry span 的大致形态（名字 + 属性）

> 没读过前面的用例也能做。

### 2.3 独立性声明

| # | 条件 | 本用例如何成立 | 怎么验证 |
|---|---|---|---|
| I1 | 部署独立 | `agentcore deploy -y --target default` 一次完成 | 干净账号跑一次 |
| I2 | 清理独立 | 所有资源带 `UseCase=06` | §8.2 的 tag 全量查询 |
| I3 | IaC 独立 | `agentcore/agentcore.json` 唯一声明，无跨栈引用 | 仓库级校验（§8.3） |
| I4 | 代码独立 | `app/aia_uc06/` 不 import 其他用例 | 同上 |
| I5 | 文档独立 | 本节以上即全部前置知识 | 通读本文 |
| I6 | 拷贝即独立 | 目录内无外部路径、无自建运维脚本 | 仓库级校验（§8.3） |

### 2.4 「拷贝即独立」

```bash
cp -r usecases/06-quality-loop /tmp/uc06
cd /tmp/uc06
agentcore validate && agentcore deploy -y --target default && agentcore status
```

> 拷到自己的账号后先改 `agentcore/aws-targets.json` 的 `account`，
> 并删掉 `agentcore/.cli/deployed-state.json`。

### 2.5 官方坐标（对齐 awslabs/agentcore-samples）

| 坐标 | 值 |
|---|---|
| 官方分组 | `06-observe-evaluate-optimize-your-agent` |
| 工作负载分类 | `workflow-automation-agents` |
| 业务垂直 | Cross-vertical |
| 可对照的官方样例 | `01-features/06-observe-evaluate-optimize-your-agent/01-observe`、`02-evaluate`、`03-optimize` |

**本目录的两条路线**：
- 主路线：`agentcore` CLI（`run eval` / `run batch-evaluation` / `run insights`
  / `run recommendation` / `run ab-test` / `view ab-test`）；
- 对照路线：`raw/README.md` 列出 CLI 背后的控制面/数据面 boto3 调用
  （`bedrock-agentcore-control` / `bedrock-agentcore`），按需展开。

---

## 3. 为什么需要这一层

费用审计 agent 上线两个月没人改过代码，但财务发现国际酒店账单总是以可疑的
整数通过。朴素做法是"再问一次模型它对不对"——单次自评既无分布也无基线，
模型可以为自己辩解。你真正需要的是：把每次决策留成可查询的 span，把历史
会话交给独立的评测器打分，把失败聚成有名字的模式，把修复变成可分流的
版本，再用统计证明"新版本更好"而不是"感觉好一点"。

---

## 4. Architecture

| 组件 | 职责 | AgentCore 托管？ |
|---|---|---|
| Runtime `aia_uc06` | 跑 Strands agent（3 工具），prompt 来自 config bundle | 是 |
| Gateway `expense-gateway` | A/B 分流：baggage 头决定 C/T1 各 50% | 是 |
| Config bundle `expense_config` | prompt 的不可变版本链 v1→v2 | 是 |
| Evaluators ×2 | `currency_guard`（pass-fail 守门）、`currency_score`（1-5 计分） | 是 |
| Online eval configs ×2 | prod 流量抽样评测，A/B 计分用 `prod_score` | 是 |
| Dataset `expense_audit_set` | 6 个已知正确答案的审计场景 | 是 |
| CloudWatch `aws/spans` | OTel span 落点，失败模式的原始证据 | 是（log 组自持） |

**数据流**：invoke → runtime（spans → `aws/spans`）→ 四种评测读 trace →
insights 聚类 → recommendation 链到 insights 重写 prompt → 人为应用为
bundle v2 → gateway 在 v1/v2 间分流 → A/B 报告出统计结论 → CI 门禁以批量
评测均值守住基线。

**为什么这样设计**：prompt 变更走 bundle 版本而非代码部署，是因为修复的
验证单位是"流量比例 × 评分"，不是"部署事件"；endpoint `prod` 钉在
runtime v1 上，让 C/T1 只差 bundle 一个变量。

---

## 5. Prerequisites

| 项 | 要求 | 自检命令 |
|---|---|---|
| AWS 账号 | 可创建 Bedrock AgentCore 资源 | `aws sts get-caller-identity` |
| 区域 | **us-east-1** | `aws configure get region` |
| AgentCore CLI | Node.js 20+ / `@aws/agentcore` 0.31.1 | `agentcore --version` |
| Python | 3.13（CodeZip），`uv` 同步依赖 | `python3 -V && uv --version` |
| 模型访问 | `deepseek.v3.2`（agent 与两个 evaluator 共用） | 部署后 invoke 即验 |
| CDK | `agentcore/cdk/` 里 `npm install` 过 | `agentcore deploy` |
| Transaction Search | 首次 deploy 后约 10 分钟才可索引 span | deploy 输出的 Note |
| **其他用例** | **不需要** | — |

### 5.1 最小权限

Bedrock AgentCore 全套（runtime/gateway/evaluator/online-eval/config-bundle/
dataset/AB-test 的 create·list·invoke）、CloudWatch Logs（`aws/spans` 读写、
`/aws/bedrock-agentcore/*` 读）、IAM 创建执行角色（CLI 自动建）、
`resourcegroupstaggingapi:GetResources`。

---

## 6. Cost & time

| 项 | 本用例 |
|---|---|
| 实测花费 | 约 **$1.5**（DeepSeek 按量计费） |
| 最贵的一项 | insights + recommendation 的批量 trace 评审 ≈ $0.6 |
| 预计耗时 | 300 min（5 次 deploy ≈ 35 min，评测/聚类/推荐排队 ≈ 25 min，其余为写作与排查） |

⚠️ 常见超支点：A/B 忘了 `pause` 会让在线评测按 100% 抽样持续计费；
`--lookback-days` 拉大会让批量评测吃进更多历史会话。

```bash
agentcore remove all -y && agentcore deploy -y --target default
```

---

## 7. Step-by-step

### 7.1 声明资源

```bash
agentcore add gateway --name expense-gateway --protocol-type NONE --authorizer-type NONE
agentcore add gateway-target --name expense-agent --gateway expense-gateway \
  --type http-runtime --runtime aia_uc06 --outbound-auth none
agentcore add evaluator --name currency_guard --level TRACE \
  --type llm-as-a-judge --model deepseek.v3.2 --rating-scale pass-fail \
  --instructions "You are reviewing one trace of an expense audit agent. Trace context: {context}. Rule: if the receipt the agent loaded with load_receipt has a currency other than USD, the agent must call the convert_currency tool and use its USD result in the final reimbursable total. Fail the trace if a non-USD receipt is totalled without a convert_currency call, or if the final total ignores the converted amount. Pass otherwise. End with pass or fail and one sentence of reasoning."
agentcore add evaluator --name currency_score --level TRACE \
  --type llm-as-a-judge --model deepseek.v3.2 --rating-scale 1-5-quality \
  --instructions "Score how well the agent handled receipt currency on a 1-5 scale, where 5 means every non-USD receipt was converted with convert_currency before comparing to the policy cap, and 1 means a foreign amount was treated as USD. Trace context: {context}. End with the score and one sentence of reasoning."
agentcore add online-eval --name prod_quality --runtime aia_uc06 \
  --evaluator currency_guard --sampling-rate 100 --enable-on-create
agentcore add online-eval --name prod_score --runtime aia_uc06 \
  --evaluator currency_score --sampling-rate 100 --enable-on-create
agentcore add config-bundle --name expense_config \
  --components-file agentcore/bundles/prompt-v1.json --branch main \
  --commit-message "production prompt as it has run for two months"
agentcore add dataset --name expense_audit_set \
  --schema-type AGENTCORE_EVALUATION_PREDEFINED_V1 \
  --description "Fixed audit scenarios with known-correct answers"
```

**预期输出**：每条一行 `{"success":true,...}` 或 `Added ...`（evidence/20, 27, 21, 63, 28, 64, 33, 40）。

**如何验证**：`agentcore status` 列出全部资源且均为 Local only（部署前）。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `Invalid name` | evaluator/online-eval/batch 名不接受连字符 | 用下划线：`currency_guard`、`prod_score` |
| gateway-target 报 protocol 错误 | http-runtime target 要求 gateway `protocolType: None` | 重建 gateway 用 `--protocol-type NONE` |

### 7.2 部署

```bash
agentcore deploy -y --target default        # evidence/05-deploy-1.log
```

**预期输出**：`✓ Deployed to 'default' (stack: AgentCore-aiauc06-default)`，
Outputs 含 runtime/dataset 的 ARN，并提示 Transaction Search 需约 10 分钟生效。

**如何验证**：`agentcore status` 全部 READY。

### 7.3 复现缺陷（10 个会话）

```bash
agentcore invoke --runtime aia_uc06 \
  --session-id qloop-prod-02-r4107-audit-run-2026 \
  --prompt "Audit receipt R-4107 for reimbursement. Apply the travel desk policy and end with the decision line."
```

6 个非 USD 收据（R-4107 EUR 210、R-4118 EUR 76.50、R-4125 GBP 195 及其重复）
全部错报；4 个 USD 会话正常（evidence/30-invoke-prod-*）。

**如何验证**：答案里出现 "Every receipt amount is already in USD" 的复述，
`Decision: approve, reimbursable total $210`（EUR 210 未换汇）。

### 7.4 span 揭示失败模式

```bash
aws logs filter-log-events --region us-east-1 --log-group-name aws/spans \
  --start-time $(python3 -c "import time;print(int((time.time()-7200)*1000))") \
  --query 'events[].message' --output json > evidence/36-spans-prod.json
```

**预期输出**：154 行 span；`execute_tool load_receipt` 11、
`execute_tool lookup_policy` 11、`execute_tool convert_currency` **0**。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `aws/spans` 无任何行 | ① 运行时没装 ADOT distro；② 新 runtime 默认 unified destination | ① `pyproject.toml` 加 `aws-opentelemetry-distro>=0.18.0` 后重部署；② `agentcore.json` envVars 加 `UNIFIED_TRACES_DESTINATION_ENABLED=false` |
| span 里查不到 session | Transaction Search 未生效 | 首次 deploy 后等约 10 分钟 |

### 7.5 四种评测模式

```bash
# 按需（evidence/50）
agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \
  --session-id qloop-prod-02-r4107-audit-run-2026
# 批量（evidence/51/52/52b/53）
agentcore run batch-evaluation -r aia_uc06 -e Builtin.Correctness currency_guard \
  -n baseline_audit_batch --lookback-days 1 --wait
# 数据集（evidence/54）
agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \
  --dataset expense_audit_set
```

**预期输出**：按需 `Builtin.Correctness: 0.00 / currency_guard: 0.00`；
批量 `Sessions: 11`，`Builtin.Correctness: 0.50 avg`，`currency_guard: 4 pass/7 fail`；
数据集 `Sessions: 6`，`Builtin.Correctness: 0.50`。

第四种是在线评测：`prod_quality`/`prod_score` 以 100% 抽样给 prod 流量计分，
A/B 报告（7.8）直接消费其结果。

### 7.6 insights：把失败聚成模式

```bash
agentcore run insights -r aia_uc06 --lookback-days 1 \
  -n baseline_failure_analysis --wait          # evidence/60
agentcore view insights baseline_failure_analysis-375c7e1293 --json   # evidence/61
```

**预期输出**：17 会话全部完成；失败簇
`Foreign Currency Ignored Despite Receipt Metadata`（8 会话），
子簇 `Currency Mismatch Contradiction Failures`，rootCause 带 span id、
trace id、`fixType: SYSTEM_PROMPT_FIX` 与逐会话 recommendation。

### 7.7 recommendation：从 trace 重写提示词

```bash
# categorical evaluator 会被拒绝（evidence/62）
agentcore run recommendation --type system-prompt -r aia_uc06 -e currency_guard \
  --prompt-file app/aia_uc06/system-prompt.md \
  --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix --wait
# 数值 evaluator 成功（evidence/67）
agentcore run recommendation --type system-prompt -r aia_uc06 -e Builtin.Correctness \
  --prompt-file app/aia_uc06/system-prompt.md \
  --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix3 --wait
```

**预期输出**：第一次
`[EvaluationNotSupportedException] ... categorical rating scale ...`；
第二次 COMPLETED，Explanation 逐条引用 EUR/GBP trace（0009、0012、0016…）、
指出 "every receipt amount is already in USD" 是根因，并给出
`+++ Recommended System Prompt +++`。

**人工应用**：优化器诊断准确，但它的完整改写加了"先申报再等用户批准"的门，
单轮审计场景会自我截断（本地试跑证实）。取其诊断、应用最小编辑——删除陈旧
禁令、改为"先查币种、非 USD 先 convert_currency"——写为
`agentcore/bundles/prompt-v2.json`（946 字符，符合 982 上限）。

### 7.8 提交 v2 并 A/B

```bash
aws bedrock-agentcore-control update-configuration-bundle --region us-east-1 \
  --cli-input-json file:///tmp/update-bundle-v2.json     # evidence/69
agentcore run ab-test -n expense_ab_01 -g expense-gateway \
  --control-bundle expense_config --control-version f45629ba-e409-46b7-80b8-ce1858319573 \
  --treatment-bundle expense_config --treatment-version d4c45b72-99ec-4d39-a60b-b5a1541f68d5 \
  --online-eval prod_score --control-weight 50 --treatment-weight 50   # evidence/70
# 经 gateway URL 发 28 个审计请求（evidence/71-ab-invoke-*，baggage 头分流 C/T1）
agentcore view ab-test aiauc06_expense_ab_01-227c8af53d --json         # evidence/72
agentcore pause ab-test -i aiauc06_expense_ab_01-227c8af53d --json     # evidence/73
```

**预期输出**：v2 返回 `versionId: d4c45b72-...`；A/B 报告
`controlStats.mean: 2 (n=12)`、`variantResults[0].mean: 4 (n=14)`、
`confidenceInterval: [1.00, 3.00]`、`pValue: 0.00043`、`isSignificant: true`。

| 如果失败 | 原因 | 修复 |
|---|---|---|
| `agentcore add config-bundle` 同名拒绝 | add 语义是"新建" | 用 `update-configuration-bundle` + `parentVersionIds` |
| A/B 会话 400 | session id 短于 33 字符 | 加长，如 `qloop-ab-01-r4107-audit-run-2026` |

### 7.9 CI 门禁（eval-gate.yml）

仓库级 `.github/workflows/eval-gate.yml`：PR 触碰 `usecases/06-quality-loop/**`
即跑与 7.5 相同的批量评测，Python 步对 `results[].evaluatorId==Builtin.Correctness`
求均值，低于 `quality-baseline.json` 的 `min_mean_score` 则 `::error::` + exit 1。

本地逐步复现（GitHub 沙箱无法落凭证，PROVENANCE 见 evidence/80b）：

```bash
agentcore run batch-evaluation --runtime aia_uc06 -e Builtin.Correctness \
  -n gate_probe --lookback-days 1 --wait --json > evidence/80-gate-batch.json
# mean 0.678（45 会话）≥ 0.500 → gate passed（evidence/81）
# 把 baseline 抬到 0.900 → ::error:: + exit 1（evidence/82，模拟回归）
```

### 7.10 teardown

```bash
agentcore remove all -y                    # evidence/90
agentcore deploy -y --target default       # evidence/91
agentcore status                           # evidence/92：No resources match the given filters.
```

---

## 8. Verify

### 8.1 能力证明（原生命令的输出）

1. **四种评测模式全部执行** ⇒ assertions[0]：`run eval`（50）、
   `run batch-evaluation`（51）、`run eval --dataset`（54）、online eval
   打分事件在 `/aws/bedrock-agentcore/evaluations/results/` 日志组、并作为
   A/B 计分来源（72）。
2. **recommendation 引用观察到的失败模式** ⇒ assertions[1]：67 的
   Explanation 命名 insights 簇 "Foreign Currency Ignored Despite Receipt
   Metadata" 与具体 EUR/GBP trace 清单。
3. **A/B 报告含置信区间与 p 值** ⇒ assertions[2]：72 中
   `confidenceInterval [1.00, 3.00]`、`pValue 0.00043`、`isSignificant true`。
4. **CI 在批量评测回归时阻断 PR** ⇒ assertions[3]：workflow 定义 +
   本地复现 81（pass, exit 0）/ 82（regression, exit 1），PROVENANCE 80b。
5. **版本化与 endpoint** ⇒ 84（runtime v5）、85（prod 钉 v1 READY）、
   69（bundle v1→v2）、PROVENANCE 84b。

### 8.2 独立性证明

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action \
  --query 'ResourceTagMappingList[].{arn:ResourceARN,uc:Tags[?Key==`UseCase`].Value|[0]}' \
  --output text
```

实测（evidence/86）：除 UC05 的 harness 条目外全部 `UseCase=06`；拆机后
（evidence/93）只剩 UC05 残留。tag 索引对已删资源有滞后，两个 UC05 "ghost"
条目用 `get-harness` 404 佐证已不存在（evidence/87）。

### 8.3 仓库级校验

完整仓库根自带一层系列级校验（能力覆盖 / `evidence/` 存档 / 目录自包含 /
难度单调 / 命令存在）。它是仓库级工具，通过**读取**本目录判断；单独拷走
本目录时不需要它。实测结果：EVID / COPY / INDEP / CMD 全部通过。

---

## 9. Troubleshooting

| 症状 | 原因 | 修复 |
|---|---|---|
| `No session spans found` / `aws/spans` 为空 | bedrock-agentcore 1.25.0 起不再自带 ADOT | `pyproject.toml` 加 `aws-opentelemetry-distro>=0.18.0`，重部署 |
| span 落进 runtime 自己日志组的 `spans` 流 | 新 runtime 默认 unified trace destination | envVars 加 `UNIFIED_TRACES_DESTINATION_ENABLED=false` |
| `EvaluationNotSupportedException` | recommendation 不接受 categorical 评分 | 注册 1-5 数值 evaluator（`currency_score`） |
| 400 on `runtimeSessionId` | session id 短于 33 字符 | 加长 id |
| 缺陷不复现（模型无视提示照常换汇） | 软性表述（"amounts are already in USD"）压不过工具结果 | 改为强禁令 "must never be called"（这就是 PROMPT_V1 的形态） |
| evaluator/online-eval/batch 名含连字符被拒 | 命名校验 | 一律下划线 |
| 独立性校验报某文件 points outside itself | 混入外部路径 | 改回目录内相对路径 |
| tag 查询「按其他用例过滤」永远返回空 | 重复 `Key=UseCase` 是 AND | 一个 filter 多值（OR） |

---

## 10. Cleanup

```bash
agentcore remove all -y && agentcore deploy -y --target default
```

手动核对清单：

- [ ] CloudWatch 日志组 `/aws/bedrock-agentcore/...`（runtime/evaluations 结果组）
- [ ] `aws/spans` 与 Transaction Search 索引
- [ ] S3（CodeZip 产物）
- [ ] `agentcore/agentcore.json`、`agentcore/aws-targets.json` 被 `remove all` 改写，从 git 恢复
- [ ] A/B test 已 pause（`view ab-test` 确认无 RUNNING）

**确认清空**：

```bash
aws resourcegroupstaggingapi get-resources --region us-east-1 \
  --tag-filters Key=Project,Values=agentcore-in-action Key=UseCase,Values=06 \
  --query 'ResourceTagMappingList[].ResourceARN' --output text
# 期望：空
```

---

## 11. What you repeated（为独立而内嵌的基线）

| 内嵌内容 | 规模 | 为什么不能共享 |
|---|---|---|
| 审计 agent（3 工具 + 缺陷 prompt） | `app/aia_uc06/`，约 260 行 | 评测的对象必须随用例自带（I4） |
| 两版 prompt bundle | `agentcore/bundles/prompt-v{1,2}.json` | A/B 的两个变体是本例的实验材料 |
| 6 场景数据集 | `agentcore/datasets/expense_audit_set.jsonl` | 数据集随合约走（I3） |
| 质量基线 | `quality-baseline.json` | CI 门禁必须提交在仓库里才可执行 |
| CDK 栈骨架 | `agentcore/cdk/` | 共享即破坏 I3 |
| `AGENTS.md` | 1 个文件 | 破坏 I6 |
| 离线单测 | `tests/test_agent_math.py`、`test_sanitize.py` | agent 自身 Python 的离线测试，pytest 允许保留 |

---

## 12. Going further

- 延伸实验：把 `--lookback-days` 提到 7 观察均值漂移；给 `currency_score`
  换模型看评测器本身的一致性；把 A/B 权重改成 80/20 观察 CI 收窄速度
- 官方文档：Amazon Bedrock AgentCore User Guide 的 Observability、Evaluations
  （online/batch）、Optimization 章节
- 难度阶梯上的位置：上一档 Research Agent（托管 Harness）· 下一档 Multi-Agent and Registry
- 文章版：`article.md`；英文成稿 `articles/agentcore-evaluate-and-optimize.md`
