"""Ticketing tool exposed as a Lambda target on the gateway.

The gateway calls it with the tool arguments the model produced. It writes one
row per ticket, so the article can prove the call reached a real system by
reading the table afterwards.
"""

import json
import os
import uuid

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE = os.environ.get("TICKETS_TABLE", "aia-uc03-tickets")
ddb = boto3.resource("dynamodb", region_name=REGION)


def lambda_handler(event, context):
    order_id = event.get("order_id") or (event.get("arguments") or {}).get("order_id")
    summary = event.get("summary") or (event.get("arguments") or {}).get("summary")
    if not order_id or not summary:
        return {"ok": False, "error": "order_id and summary are both required"}

    ticket_id = "TCK-" + uuid.uuid4().hex[:10].upper()
    ddb.Table(TABLE).put_item(
        Item={"ticket_id": ticket_id, "order_id": order_id, "summary": summary}
    )
    return {"ok": True, "ticket_id": ticket_id, "order_id": order_id}
