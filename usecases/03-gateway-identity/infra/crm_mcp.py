"""A CRM MCP server small enough to read, hosted on a Lambda Function URL.

The gateway only needs three MCP methods to make tools out of a server:
`initialize`, `tools/list` and `tools/call`. This file implements exactly those
over plain JSON-RPC at POST /mcp, which is the shape the gateway speaks. The
data is in-memory on purpose: the point of the target is that the agent reaches
a system outside AgentCore without holding its credentials, not that the CRM has
a database.
"""

import json

CUSTOMERS = {
    "CUS-7781": {
        "customer_id": "CUS-7781",
        "name": "Northwind Gear Harbin",
        "tier": "gold",
        "account_manager": "li.wei",
        "open_incidents": 2,
    },
    "CUS-7790": {
        "customer_id": "CUS-7790",
        "name": "Northwind Gear Shenyang",
        "tier": "silver",
        "account_manager": "zhao.min",
        "open_incidents": 0,
    },
}

TOOLS = [
    {
        "name": "getCustomer",
        "description": "Read one CRM customer record by id, including tier and the account manager to escalate to.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer id, for example CUS-7781"}
            },
            "required": ["customer_id"],
        },
    }
]


def result(msg_id, payload):
    return {"jsonrpc": "2.0", "id": msg_id, "result": payload}


def error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(req):
    method = req.get("method")
    msg_id = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        return result(
            msg_id,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "aia-uc03-crm", "version": "1.0.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name != "getCustomer":
            return error(msg_id, -32601, f"unknown tool {name}")
        customer = CUSTOMERS.get(args.get("customer_id"))
        if not customer:
            return result(
                msg_id,
                {"content": [{"type": "text", "text": "no such customer"}], "isError": True},
            )
        return result(
            msg_id,
            {
                "content": [{"type": "text", "text": json.dumps(customer)}],
                "isError": False,
            },
        )
    return error(msg_id, -32601, f"unknown method {method}")


def lambda_handler(event, context):
    path = event.get("rawPath") or "/"
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if not path.endswith("/mcp"):
        return {"statusCode": 404, "body": json.dumps({"error": f"no route for {path}"})}
    if method != "POST":
        return {"statusCode": 405, "body": json.dumps({"error": "POST only"})}

    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps(error(None, -32700, "parse error"))}

    batch = isinstance(payload, list)
    out = []
    for req in payload if batch else [payload]:
        reply = handle(req)
        if reply is not None:
            out.append(reply)

    if not out:
        return {"statusCode": 202, "headers": {"content-type": "application/json"}, "body": ""}
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json", "mcp-session-id": "aia-uc03-crm"},
        "body": json.dumps(out if batch else out[0]),
    }
