"""Refund tools behind the gateway: one function, two tools.

The gateway calls it with the tool arguments the model produced, and the tool
name arrives in the Lambda client context. The function writes nothing down
beyond its own response - the lab is about the policy decision at the gateway,
not about record keeping - so each tool echoes what it was told plus a
timestamp. The echo is the proof the call reached a real backend.
"""

import json
import time


def lambda_handler(event, context):
    cc = context.client_context
    custom = cc.custom if cc is not None and cc.custom else {}
    original = custom.get("bedrockAgentCoreToolName", "")
    tool_name = original.split("___", 1)[-1] if original else ""
    if not tool_name:
        # Fallback when no tool name arrives: the two schemas are disjoint on
        # "amount", so the event shape alone identifies the tool.
        tool_name = "processRefund" if "amount" in event else "approveRefund"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if tool_name == "approveRefund":
        order_id = event.get("orderId")
        if not order_id:
            return {"ok": False, "error": "orderId is required"}
        return {
            "ok": True,
            "approved": True,
            "orderId": order_id,
            "approvedAt": now,
        }

    if tool_name == "processRefund":
        order_id = event.get("orderId")
        amount = event.get("amount")
        if not order_id or amount is None:
            return {"ok": False, "error": "orderId and amount are both required"}
        refund_id = "RF-" + str(int(time.time() * 1000))[-10:]
        return {
            "ok": True,
            "refundId": refund_id,
            "orderId": order_id,
            "amountCny": amount,
            "status": "refunded",
            "refundedAt": now,
        }

    return {"ok": False, "error": f"unknown tool: {tool_name or '<none>'}"}
