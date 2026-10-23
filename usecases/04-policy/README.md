# UC04 · Policy（给自主权划死边界：LOG_ONLY 先行，再 ENFORCE）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 04 · **Difficulty**: **D3** · **Region**: `us-east-1`
> **Verified on**: 2026-10-23/24 · **Cost**: 约 $1（按需计费 + 短时部署；1 个最小 Lambda）· **Time**: 约 120 min
> **Capabilities**: `policy`（深挖）· `gateway`（复用概念，刻意最小）· `observability`（决策日志，附带）
> **Standalone**: yes。这个目录不依赖任何其他用例；`agentcore/cdk/` 是内嵌的部署栈基线。

> 文中的账号 ID 一律脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：同一个 `processRefund(amount=3000)` 请求，在 LOG_ONLY 模式下被网关记为
DENY 但照常放行（拿到退款号），切成 ENFORCE 后被同一个引擎当场拒绝
（MCP error -32002）；决策日志里写着是哪条策略定的——
`determiningPolicies: ["refundCeiling-hrk1reemhq"]`；CNY 200 全程畅通。

七个证据（`evidence/`）：`23-invoke-3000-logonly`（放行）·
`26b-decision-log-both-modes`（两种模式的判定记录，含策略名）·
`25-invoke-3000-enforce`（拒绝）· `26-invoke-200-enforce`（放行）·
`27-policy-metrics`（DenyDecisions 5→1 的指标对照）·
`28-direct-mcp-enforce`（绕过 agent 直接调网关同样被拒）· `17`（基线）。

## 2. 前提

| 项 | 要求 | 验证 | 失败修复 |
|---|---|---|---|
| CLI | agentcore 0.31.1 | `agentcore --version` | `npm i -g @aws/agentcore` |
| 区域 | us-east-1 | `aws configure get region` | 所有命令显式 `--region us-east-1` |
| 模型 | deepseek.v3.2 可用 | 部署后 invoke 即验 | 换 `MODEL_ID` 为可用模型 |
| uv | 0.11.9 | `uv --version` | `pip install uv` |
| 网络 | 能访问 PyPI wheel 源 | `uv pip install` 试装 | 走内网/镜像时 `export UV_DEFAULT_INDEX=<镜像>`，CLI 的 synth 会继承 |
| 权限 | Lambda/IAM/AgentCore（含 policy-engine API） | 部署时报错即缺 | 补 IAM |

## 3. Step 1 · 后端：一个只为被拦截而存在的函数

```bash
aws iam create-role --role-name aia-uc04-lambda \
  --assume-role-policy-document '{"Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --region us-east-1
aws iam attach-role-policy --role-name aia-uc04-lambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region us-east-1
zip -j /tmp/aia-uc04-refund.zip infra/refund_api.py
aws lambda create-function --function-name aia-uc04-refund \
  --runtime python3.13 --handler refund_api.lambda_handler \
  --zip-file fileb:///tmp/aia-uc04-refund.zip \
  --role arn:aws:iam::<账号>:role/aia-uc04-lambda --region us-east-1
```

预期输出（`evidence/06`）：`FunctionName: aia-uc04-refund`、`CodeSize: 868`。

Verify：直接调用返回 echo（`evidence/07`）：
`{"ok": true, "approved": true, "orderId": "SO-2214", "approvedAt": ...}`。

If it fails：502 查 CloudWatch `/aws/lambda/aia-uc04-refund`；`client.context`
为 None 时函数会走 fallback（按事件形状识别工具），不影响本用例。

## 4. Step 2 · 网关与目标：刻意最小的单工具网关

```bash
agentcore add gateway --name refund-gateway --protocol-type MCP --authorizer-type NONE
agentcore add gateway-target --name refund --gateway refund-gateway \
  --type lambda-function-arn --lambda-arn arn:aws:lambda:us-east-1:<账号>:function:aia-uc04-refund \
  --tool-schema-file agentcore/gateway/refund-tools.json
```

两个工具（`agentcore/gateway/refund-tools.json`）：`approveRefund`（登记对话内的
审批）与 `processRefund`（打款，带 `amount` 整数参数）。本用例的主角是策略，
所以网关刻意只有一个 target——这是系列里唯一一处刻意重复（与 UC03 的分界：
UC03 讲"怎么接进来"，UC04 讲"怎么限制住"）。

Verify：`agentcore validate` 通过；`evidence/10`、`evidence/11`。

If it fails：tool schema 必须是 JSON 数组；`--lambda-arn` 用完整 ARN。

## 5. Step 3 · 部署与接线

```bash
agentcore deploy -y --target default     # 首次 3m 8s（evidence/15-deploy-2）
```

把部署输出的网关 URL 写进 `agentcore.json` 的 `GATEWAY_MCP_URL` 环境变量，再
`agentcore deploy -y --target default` 一次。基线验证（无任何策略）：

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
```

两个都拿到退款号（`evidence/17`、`evidence/19`）：此时规则只写在提示词里，
对系统来说不存在。

If it fails：invoke 报 `Access to Anthropic models is not allowed` 说明
`model/load.py` 没读到 `MODEL_ID`（默认 Claude 被区域限制）；回复里出现
`<｜DSML｜` 是 DeepSeek 模板泄漏，`main.py` 已接 `StreamSanitizer`，确认部署的
是新代码即可。

## 6. Step 4 · 建引擎、自然语言生成策略（LOG_ONLY）

```bash
agentcore add policy-engine --name refundPolicyEngine \
  --description "Refund ceiling for the refund gateway" \
  --attach-to-gateways refund-gateway --attach-mode LOG_ONLY --json
agentcore deploy -y --target default          # 引擎要先上线（evidence/22-deploy-policy-engine）

agentcore add policy --name refundCeiling --engine refundPolicyEngine \
  --description "Refunds are permitted up to CNY 500; anything above falls through to default deny" \
  -g "permit a processRefund tool call only when its amount argument is less than or equal to 500" \
  --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json
agentcore add policy --name approvalAlways --engine refundPolicyEngine \
  --description "Recording an approval is allowed whenever the order id is present" \
  -g "permit an approveRefund tool call only when its orderId argument is a non-empty string" \
  --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json
agentcore deploy -y --target default          # （evidence/22-deploy-policy）
```

自然语言进、Cedar 出（写进 `agentcore.json`）：

```json
"statement": "permit (principal, action == AgentCore::Action::\"refund___processRefund\",
  resource == AgentCore::Gateway::\"...\") when { context.input.amount <= 500 };"
```

If it fails：只写 forbid（无 permit）部署被拒 `Overly Restrictive`——全拒的
策略被服务校验挡下；无条件的 permit 被拒 `Overly Permissive`。工作形态是
**带 `when` 条件的 permit**，其余请求走默认拒绝。

## 7. Step 5 · 打观测（一次性）并验证 LOG_ONLY

网关的日志/trace 投递要自己配（boto3：`put_delivery_source` + `put_delivery_destination`
+ `create_delivery`，traces 目的地是 XRAY；CloudWatch Transaction Search 需已启用）。
之后跑两条对照：

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."
```

3000 照样拿到退款号（`evidence/23-invoke-3000-logonly`，RF-2774152577），但决策
日志里每一步都记着 DENY（`evidence/26b` 的 LOG_ONLY 段）；200 是 ALLOW，且
`determiningPolicies` 写着策略名 `refundCeiling-hrk1reemhq`。决策指标
（`evidence/27`）：LOG_ONLY DenyDecisions = 5，工具一次都没被挡。

## 8. Step 6 · 切 ENFORCE，再打一遍

改 `agentcore.json` 一处：`policyEngineConfiguration.mode: "LOG_ONLY" → "ENFORCE"`，
然后 `agentcore deploy -y --target default`（1m 24s，`evidence/24`）。

```bash
agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."
agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."
```

3000：approveRefund 过了（`approvalAlways` ALLOW），processRefund 被网关拒绝，
agent 只能如实转述（`evidence/25`）。200：两个工具都 ALLOW，退款号
RF-2774662593（`evidence/26`）。指标变成 ENFORCE DenyDecisions = 1（`evidence/27`）。
绕过 agent 直接调网关同样被拒（`evidence/28`）：

```bash
curl -s -X POST "$GATEWAY_URL" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
  "params":{"name":"refund___processRefund","arguments":{"orderId":"SO-2214","amount":3000}}}'
# {"jsonrpc":"2.0","id":2,"error":{"code":-32002,"message":"Tool Execution Denied: ..."}}
```

If it fails：ENFORCE 后 200 也挂了，检查 `approvalAlways` 是否存在——没有它的
引擎会把审批工具一起挡掉（见 §5 的坑 5）。

## 9. 成本

runtime + gateway + policy engine + 1 个最小 Lambda。Policy/Gateway 按请求
计费，本例全部流量是个位数请求，合计约 $1，拆干净后不再计费。

## 10. 清理

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status        # 应为空
aws lambda delete-function --function-name aia-uc04-refund --region us-east-1
aws iam delete-role --role-name aia-uc04-lambda
# 决策日志组 /aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/... 一并删除
```

注意：`remove all -y` 会清空 `agentcore/agentcore.json` 与
`agentcore/aws-targets.json`，复跑前从 git 恢复。

## 11. 为独立性而内嵌的基线

`agentcore/cdk/`（node_modules + dist）与 `app/aia_uc04/model/` 骨架、
`mcp_client/` 是从基线模板复制的刻意重复；网关本身与 UC03 概念重复但刻意更小。
`infra/refund_api.py` 是本例真实后端。决策日志的投递配置（CloudWatch delivery）
是账号级一次性设置，不属于本例的 IaC。

## 12. Going further

- 时间/速率类策略与 Guardrails 联动（`--form-category`）是 `agentcore add policy`
  的另外两种形态，本例未展开。
- 官方文档：Policy in Amazon Bedrock AgentCore（docs.aws.amazon.com/bedrock-agentcore）。
- 难度阶梯：上一档 UC03（接入），下一档 UC05（工具组合）。
