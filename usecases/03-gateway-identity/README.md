# UC03 · Gateway and Identity（网关与身份：不持密钥触达真实系统）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 03 · **Difficulty**: **D3** · **Region**: `us-east-1`
> **Verified on**: 2026-10-20 · **Cost**: 约 $3（按需计费 + 短时部署；Cognito 免费档）· **Time**: 约 150 min
> **Capabilities**: `gateway`（深挖）· `identity`（深挖）· `mcp-server-hosting`（附带）
> **Standalone**: yes。这个目录不依赖任何其他用例；`agentcore/cdk/` 是内嵌的部署栈基线。

> 文中的账号 ID 一律脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：一个 agent 通过一个 MCP 网关调用三类真实后端（OpenAPI 订单服务、
Lambda 工单函数、自托管 MCP 的 CRM），不带任何后端明文凭据，并且无 JWT 的
调用在网关就被 401 拒掉。

五个证据（`evidence/`）：`19` 工具清单与 401 · `20` 经网关调订单（含 auth 回显）
· `23` 端到端 invoke · `24` 独立性标签查询 · `22` 源码无明文凭据。

## 2. 前提

| 项 | 要求 | 验证 | 失败修复 |
|---|---|---|---|
| CLI | agentcore 0.31.1 | `agentcore --version` | `npm i -g bedrock-agentcore`；若被 pip 版遮蔽先卸载 |
| 区域 | us-east-1 | `aws configure get region` | 所有命令显式 `--region us-east-1` |
| 模型 | deepseek.v3.2 可用 | 部署后 invoke 即验 | 换 `MODEL_ID` 为可用模型 |
| 权限 | Cognito/Lambda/DynamoDB/SecretsManager/IAM/AgentCore | 部署时报错即缺 | 补 IAM |

## 3. Step 1 · 身份：建用户池、资源服务器、机器客户端

```bash
aws cognito-idp create-user-pool --pool-name aia-uc03-ops --region us-east-1
aws cognito-idp create-resource-server --user-pool-id <POOL_ID> \
  --identifier https://aia-uc03/ops --name aia-uc03-ops \
  --scopes ScopeName=orders.read,ScopeDescription="read orders" --region us-east-1
aws cognito-idp create-user-pool-domain --user-pool-id <POOL_ID> \
  --domain aia-uc03-ops-<后缀> --region us-east-1
aws cognito-idp create-user-pool-client --user-pool-id <POOL_ID> \
  --client-name aia-uc03-agent --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes "https://aia-uc03/ops/orders.read" \
  --allowed-o-auth-flows-user-pool-client --region us-east-1
```

预期输出：`UserPoolClient` 带 `ClientId` 与 `ClientSecret`。

Verify：换取令牌应返回 `access_token` 与 `expires_in: 3600`：

```bash
curl -s -X POST "https://<域名>.auth.us-east-1.amazoncognito.com/oauth2/token" \
  -u "<CID>:<CSECRET>" \
  -d "grant_type=client_credentials&scope=https://aia-uc03/ops/orders.read"
```

If it fails：`invalid_grant` 几乎总是 `AllowedOAuthFlowsUserPoolClient` 没开；
用 `update-user-pool-client` 把 `--allowed-o-auth-flows-user-pool-client` 加上。

## 4. Step 2 · 后端：两张表、两个函数、一个 MCP 端点

代码在 `infra/`（`orders_api.py`、`ticketing.py`、`crm_mcp.py`）。建表：

```bash
aws dynamodb create-table --table-name aia-uc03-orders \
  --attribute-definitions AttributeName=order_id,AttributeType=S \
  --key-schema AttributeName=order_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region us-east-1 \
  --tags Key=Project,Value=agentcore-in-action Key=UseCase,Value=03 Key=AutoDelete,Value=true
```

tickets 表同理。函数用 `aws lambda create-function`（runtime `python3.13`），
订单 API 再开 Function URL：

```bash
aws lambda create-function-url-config --function-name aia-uc03-orders-api \
  --auth-type NONE --region us-east-1
aws lambda add-permission --function-name aia-uc03-orders-api \
  --statement-id url --action lambda:InvokeFunctionUrl \
  --principal "*" --function-url-auth-type NONE --region us-east-1
aws lambda add-permission --function-name aia-uc03-orders-api \
  --statement-id inv --action lambda:InvokeFunction --principal "*" --region us-east-1
```

Verify：无 token `curl` 返回 401（来自函数自身的校验），带 token 返回订单
列表 + `"auth":"bearer"`。

If it fails：只加了 `InvokeFunctionUrl` 时全是 403（还没到你的代码），必须
再补 `lambda:InvokeFunction`；返回 502 查 CloudWatch，多半是 DynamoDB 的
`Decimal` 没转换就 `json.dumps`。

## 5. Step 3 · 凭据、网关、三个目标

```bash
agentcore add credential --name cognito-orders-m2m --type oauth \
  --discovery-url "https://cognito-idp.us-east-1.amazonaws.com/<POOL_ID>/.well-known/openid-configuration" \
  --client-id <CID> --client-secret <CSECRET> \
  --scopes "https://aia-uc03/ops/orders.read"

agentcore add gateway --name ops-gateway --protocol-type MCP \
  --authorizer-type CUSTOM_JWT --discovery-url "$DISCOVERY" \
  --allowed-clients <CID>

agentcore add gateway-target --name orders --gateway ops-gateway \
  --type open-api-schema --schema agentcore/gateway/orders-openapi.json \
  --outbound-auth oauth --credential-name cognito-orders-m2m
agentcore add gateway-target --name ticketing --gateway ops-gateway \
  --type lambda-function-arn --lambda-arn <工单函数ARN> \
  --tool-schema-file agentcore/gateway/create-ticket-tool.json
agentcore add gateway-target --name crm --gateway ops-gateway \
  --type mcp-server --endpoint <CRM函数URL>/mcp
```

Verify：`agentcore validate` 返回 `Valid`；`agentcore.json` 的
`agentCoreGateways[0].targets` 恰好 3 项、类型各异。

If it fails：tool schema 文件必须是 JSON 数组（单个对象会被拒）；
`--host` 对 `mcp-server` 目标不适用，直接给 `--endpoint`。

## 6. Step 4 · 部署与接线

```bash
agentcore deploy -y --target default     # 首次 3m 4s（evidence/15）
agentcore fetch access --name ops-gateway --json   # 拿网关 /mcp URL 与令牌
```

把网关 URL 写回 `agentcore.json` 的 `GATEWAY_MCP_URL`，再部署一次
（evidence/16，1m 32s）。同时给运行时角色挂一条最小策略：只允许读
`aia-uc03-gateway-client-*` 这一个 secret（`secretsmanager:GetSecretValue`）。

If it fails：第一次 invoke 报模糊的 tool error，先查运行时日志
`agentcore logs --since 15m --query "minted"`，令牌铸出来了还失败，就是网关
调用层；工具名必须是 `orders___listOrders` 这类带目标前缀的全名。

## 7. Step 5 · 验证五个断言

| 断言 | 命令 | 证据 |
|---|---|---|
| 三类目标都进 tools/list | `curl $GATEWAY/mcp` + Bearer | `19` |
| 无 JWT 被拒 | 同上不带 Authorization，返回 401 | `19` |
| 出站 OAuth 由网关换票 | `tools/call orders___listOrders`，回显 `auth:bearer` | `20` |
| 源码无明文凭据 | `grep -rn "<真实secret>" app/`，结果 0 | `22` |
| 独立性 | 全量标签查询，全为 03 | `24` |

端到端：`agentcore invoke --prompt "Three delayed orders ... escalate to."`
（evidence/23）：3 条延迟单、SO-1041 开票 TCK-*、升级对象 `li.wei`。

## 8. 成本

部署栈：runtime + gateway + 两个 OAuth credential。后端：2 张按需 DynamoDB
表、3 个最小 Lambda、1 个 Cognito 用户池（免费档）。本例合计约 $3，拆干净后
不再计费。

## 9. 清理

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status        # 应为空
aws dynamodb delete-table --table-name aia-uc03-orders --region us-east-1
aws dynamodb delete-table --table-name aia-uc03-tickets --region us-east-1
aws lambda delete-function --function-name aia-uc03-orders-api --region us-east-1
aws lambda delete-function --function-name aia-uc03-ticketing --region us-east-1
aws lambda delete-function --function-name aia-uc03-crm --region us-east-1
aws iam delete-role --role-name aia-uc03-lambda
aws secretsmanager delete-secret --secret-id aia-uc03-gateway-client --force-delete-without-recovery
aws cognito-idp delete-user-pool --user-pool-id <POOL_ID> --region us-east-1
```

注意：`remove all -y` 会清空 `agentcore/agentcore.json` 与
`agentcore/aws-targets.json`，复跑前从 git 恢复。CDK bootstrap 栈与其资产桶
是刻意保留的。

## 10. 为独立性而内嵌的基线

`agentcore/cdk/`（约 300MB node_modules 与 dist）与 `app/aia_uc03/model/`
骨架是从 UC01/UC02 原样复制的刻意重复：目录必须拷走即独立，所以不共享。
`infra/` 三个 Lambda 源文件是本例的真实后端，不是运维包装脚本。
