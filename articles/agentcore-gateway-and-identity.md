---
title: "Reaching Real Systems Without Holding Credentials: Gateway and Identity"
description: "One JWT in, three systems out: an AgentCore Gateway fronts an order API, a ticketing function and a CRM, and the agent source holds no system credential."
tags: ["ai", "agents", "agentcore", "security"]
date: 2026-10-22
draft: false
canonical_url: "https://xiongpin.dev/posts/agentcore-gateway-and-identity/"
cover:
  image: "/images/agentcore-gateway-and-identity/cover.png"
  alt: "Cover art: an agent source holding only a secret ARN, a gateway checking a JWT, and three systems behind it"
---

An agent that can reach a real system usually carries that system's key, and the
key outlives every rotation policy you wrote. This article builds the opposite:
an operations assistant that reaches an order service, a ticketing function and
a CRM through one AgentCore Gateway, proves a caller with a JWT, and holds
nothing but the ARN of a secret. Every number was measured in one account, in
`us-east-1`.

## The use case

Northwind Gear's support lead starts the week with one question: which orders
slipped, which need a ticket, and who owns the customer. Three systems answer
it, and none of them should trust the agent directly. The order service demands
a bearer token, the ticketing function writes rows, and the CRM is a small MCP
server. The assistant has to orchestrate all three in one turn.

## What AgentCore does here

Three of the nine capabilities carry this use case.

- Gateway: one MCP endpoint in front of the three backends. It turns an OpenAPI
  descriptor, a Lambda tool schema and a remote MCP server into one tool list,
  and it does every outbound authentication itself.
- Identity: a Cognito machine client mints the token the gateway demands, and a
  second OAuth credential is what the gateway presents to the order service.
- Runtime, lightly: hosts the assistant, one microVM per session, which is why
  the token cache lives for the process lifetime.

The other six stay off. No Memory, no Policy engine, no Evaluations.

## Requirements

- Node.js 20 or newer, the AgentCore CLI 0.31.1, AWS CLI 2.x
- Python 3.10 to 3.14 on the host; the runtime target is `PYTHON_3_13`
- An AWS account in `us-east-1` with Bedrock model access
- Model `deepseek.v3.2`, passed to the code through `MODEL_ID`
- IAM permissions for Cognito, Lambda, DynamoDB, Secrets Manager, IAM roles, and
  AgentCore resources; the CLI writes the runtime and gateway roles

## The code

The whole use case is this folder:

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/03-gateway-identity

```text
03-gateway-identity/
├── app/aia_uc03/main.py        three tools, one JSON-RPC client, one token cache
├── app/aia_uc03/model/         model client and response cleanup
├── infra/orders_api.py         order service, refuses any caller without a bearer
├── infra/ticketing.py          Lambda behind the ticketing target
├── infra/crm_mcp.py            small MCP server over a function URL
├── agentcore/agentcore.json    runtime, gateway, credential, three targets
├── agentcore/aws-targets.json  account and region
└── agentcore/gateway/          OpenAPI descriptor and Lambda tool schema
```

Five files matter. `main.py` is the only one the runtime executes, and it holds
the token cache, the `mcp_call` helper and the three `@tool` wrappers.
`orders_api.py` returns `401` until it sees a bearer it can verify, and echoes
which token it saw, which is how the outbound hop becomes observable.
`ticketing.py` writes a ticket row and returns its id. `crm_mcp.py` answers
`initialize`, `tools/list` and `tools/call` over JSON-RPC. The two files under
`agentcore/gateway/` are the descriptors the gateway turns into tools.

## How it works

The gateway is a declaration, not code. Its whole behaviour sits in the
`agentCoreGateways` array of `agentcore.json`: one protocol, one authorizer,
three targets.

```json
{
  "name": "ops-gateway",
  "protocolType": "MCP",
  "authorizerType": "CUSTOM_JWT",
  "authorizerConfiguration": {
    "customJwtAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_CZAVbCDhv/.well-known/openid-configuration",
      "allowedClients": ["66n9f4uo3eqc18jdeujq3tltd2"]
    }
  },
  "targets": [
    { "name": "orders", "targetType": "openApiSchema",
      "outboundAuth": { "type": "OAUTH", "credentialName": "cognito-orders-m2m" },
      "schemaSource": { "inline": { "path": "agentcore/gateway/orders-openapi.json" } } },
    { "name": "ticketing", "targetType": "lambdaFunctionArn",
      "lambdaFunctionArn": { "lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:aia-uc03-ticketing",
                             "toolSchemaFile": "agentcore/gateway/create-ticket-tool.json" } },
    { "name": "crm", "targetType": "mcpServer",
      "endpoint": "https://pakjn2tjya3tmiocnqpujerppe0pidtw.lambda-url.us-east-1.on.aws/mcp" }
  ]
}
```

Three shapes, one tool list: an OpenAPI document, a Lambda with a tool schema,
and a remote MCP server become `orders___listOrders`, `ticketing___createTicket`
and `crm___getCustomer`. The triple underscore prefix is the target name the
gateway prepends, so the model sees where a tool lives without being told. Only
the first target carries `outboundAuth`, because only the order service demands
a credential of its caller.

On the agent side there is no system key at all. The runtime mints the gateway's
token from a Cognito machine client, and caches it for the life of the process:

```python
def bearer() -> str:
    creds = client_credentials()
    basic = base64.b64encode(
        f"{creds['client_id']}:{creds['client_secret']}".encode()
    ).decode()
    body = f"grant_type=client_credentials&scope={SCOPE}".encode()
    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=body,
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "authorization": f"Basic {basic}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        payload = json.load(r)
    _cache["token"] = payload["access_token"]
    _cache["expires"] = time.time() + float(payload.get("expires_in", 3600))
    return payload["access_token"]
```

The secret behind `client_credentials()` never reaches the source. The runtime
reads it from Secrets Manager through `CLIENT_SECRET_ARN`, an environment
variable in the contract:

```python
def client_credentials() -> dict:
    client = boto3.client("secretsmanager", region_name=REGION)
    raw = client.get_secret_value(SecretId=SECRET_ARN)["SecretString"]
    return json.loads(raw)
```

One IAM detail is easy to miss. The runtime role that the CLI creates knows
nothing about Secrets Manager, so `get_secret_value` fails on the first invoke,
and the model reports the access denied as a vague tool error. The fix is one
inline policy, attached once with `aws iam put-role-policy` against the runtime
role and scoped to the single secret:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:aia-uc03-gateway-client-*" }
  ]
}
```

Least privilege survives here too: the role can read one secret, not the vault.

## Deploy it

The three backends come up first, because the gateway needs their addresses.
Then the declarations, in this order:

```bash
agentcore add gateway --name ops-gateway --description "Northwind operations gateway" \
  --protocol-type MCP --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY" --allowed-clients 66n9f4uo3eqc18jdeujq3tltd2

agentcore add credential --name cognito-orders-m2m --type oauth \
  --discovery-url "$DISCOVERY" --client-id "$CID" --client-secret "$CSECRET" \
  --scopes "https://aia-uc03/ops/orders.read"

agentcore add gateway-target --name orders --gateway ops-gateway \
  --type open-api-schema --schema agentcore/gateway/orders-openapi.json \
  --outbound-auth oauth --credential-name cognito-orders-m2m

agentcore add gateway-target --name ticketing --gateway ops-gateway \
  --type lambda-function-arn \
  --lambda-arn arn:aws:lambda:us-east-1:123456789012:function:aia-uc03-ticketing \
  --tool-schema-file agentcore/gateway/create-ticket-tool.json

agentcore add gateway-target --name crm --gateway ops-gateway \
  --type mcp-server \
  --endpoint https://pakjn2tjya3tmiocnqpujerppe0pidtw.lambda-url.us-east-1.on.aws/mcp
```

![Five declarations and five confirmations, ending with the CRM target added](/images/agentcore-gateway-and-identity/D1-add-sequence.png)

Five confirmations, no AWS resource touched yet: the CLI is editing
`agentcore.json`. Three Lambda functions, two DynamoDB tables and one user pool
are the whole lab, and every resource carries the tags
`Project=agentcore-in-action`, `UseCase=03`, `AutoDelete=true`. The credential
command also prints the warning every reader should see once, about secrets on
the command line.

One command then deploys the runtime, the gateway and both credentials:

```bash
agentcore deploy -y --target default
```

![The first deploy: ten steps, 1m 38s of it in the gateway, 3m 4s in total](/images/agentcore-gateway-and-identity/D2-deploy.png)

The first deploy took 3 minutes 4 seconds. Changing one environment variable
afterwards, because the gateway URL is only knowable once the gateway exists,
took 1 minute 32 seconds on the second deploy. The CLI reuses the CDK project,
so the second run is a stack update, not a rebuild.

## What it produced

The shape of the finished lab, three backends and one gateway in front of them:

![The agent, the gateway and the three systems behind it](/images/agentcore-gateway-and-identity/F1-gateway-architecture.png)

A call without a token is rejected before any routing happens:

![tools/list without a token returns 401, with a token it lists four tools](/images/agentcore-gateway-and-identity/S1-tools-and-401.png)

Four tool names come back, one per target plus the built-in search tool, and the
prefixes map one to one onto the three target types. Calling the order tool
through the gateway returns three delayed orders, and the payload ends with
`"auth": "bearer"` plus the first characters of the token the gateway minted.
The order service saw a credential that exists nowhere in the repository:

![orders___listOrders through the gateway, with the auth echo](/images/agentcore-gateway-and-identity/S2-orders-through-gateway.png)

One invoke then runs the whole workflow. The assistant lists the delayed orders,
opens a ticket for the only one above 100 units, reads the CRM record and quotes
`li.wei` as the account manager to escalate to:

![agentcore invoke runs list, ticket and CRM in one turn](/images/agentcore-gateway-and-identity/S3-agent-invoke.png)

The independence check closes the loop. One unfiltered tag query lists every
resource in the account, and every row says `03`:

![every resource in the account is tagged UseCase 03](/images/agentcore-gateway-and-identity/S4-independence.png)

## Troubleshooting

- A Lambda function URL with `AuthType NONE` needs two permissions, not one.
  With only `lambda:InvokeFunctionUrl` every request returns 403 before reaching
  the handler. Add `lambda:InvokeFunction` as a second statement.
- DynamoDB hands back `Decimal`, and `json.dumps` refuses it, so the function
  returned 502 on exactly the requests that read the table. Convert before
  serialising.
- The gateway prefixes every tool with its target name. The first agent build
  called `listOrders` and failed; the real name is `orders___listOrders`.
- Cognito returns `invalid_grant` for `client_credentials` until the app client
  has `AllowedOAuthFlowsUserPoolClient` set to true.

## Takeaways

- The credential boundary is the gateway, not the agent. Agent source that
  contains a system key cannot be rotated, audited or shared.
- Three target shapes, one tool list. OpenAPI, Lambda and MCP look identical to
  the model, so the backend choice stays a backend decision.
- The order service echoing which token it saw is the cheapest possible proof
  that outbound authentication works. Build the echo into your first backend.
- Environment variables are part of the contract, and a value the deploy itself
  produces needs a second deploy. Budget for it.
- `agentcore remove all -y` empties `agentcore.json` and `aws-targets.json`;
  restore both from git before deploying again.
