"""Order API behind the gateway: a Lambda Function URL speaking REST.

It exists so the gateway has a real HTTP system to reach. Two things make it
useful for the article:

  * it refuses any request without a bearer token, so a gateway target that
    forgets to fetch one fails loudly;
  * it returns which authorization header it saw, so the article can show that
    the token was minted by the identity provider at call time, not stored in
    the agent.
"""

import json
import os
from decimal import Decimal

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE = os.environ.get("ORDERS_TABLE", "aia-uc03-orders")
ddb = boto3.resource("dynamodb", region_name=REGION)


def plain(value):
    """DynamoDB hands back Decimal, which json.dumps refuses."""
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value


def respond(status, payload):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(plain(payload)),
    }


def orders(event):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return respond(401, {"error": "missing bearer token"})

    status = (event.get("queryStringParameters") or {}).get("status", "delayed")
    table = ddb.Table(TABLE)
    items = table.scan().get("Items", [])
    picked = [o for o in items if o.get("status") == status]
    picked.sort(key=lambda o: o["order_id"])
    return respond(
        200,
        {
            "status_filter": status,
            "count": len(picked),
            "orders": picked,
            "auth": "bearer",
            "token_prefix": auth[7:19],
        },
    )


def lambda_handler(event, context):
    path = event.get("rawPath") or event.get("path") or "/"
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if path.endswith("/orders") and method == "GET":
        return orders(event)
    return respond(404, {"error": f"no route for {method} {path}"})
