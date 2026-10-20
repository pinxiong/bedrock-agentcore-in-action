"""uc03 · Gateway and Identity: an operations assistant that holds no keys.

The situation: a support lead needs tomorrow's delayed orders, two tickets
opened, and the account manager to escalate to. Three systems answer that: an
order service behind an OpenAPI descriptor, a ticketing function, and a CRM that
speaks MCP. None of their credentials live in this folder.

What this file actually does on every call:

  1. asks Cognito for a machine token with the scope the gateway demands;
  2. speaks MCP to the AgentCore Gateway, which validates that token;
  3. the gateway, not the agent, exchanges its own credential for the order
     service token and holds the CRM connection.

The only thing stored here is the ARN of a secret. The secret is read at
runtime, and the token lives in memory for one hour.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from collections import OrderedDict
from typing import Any

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager

from model.load import load_model, model_id
from model.sanitize import StreamSanitizer

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.environ.get("AWS_REGION", "us-east-1")
GATEWAY_MCP_URL = os.environ.get("GATEWAY_MCP_URL", "")
TOKEN_ENDPOINT = os.environ.get("TOKEN_ENDPOINT", "")
SCOPE = os.environ.get("GATEWAY_SCOPE", "https://aia-uc03/ops/orders.read")
SECRET_ARN = os.environ.get("CLIENT_SECRET_ARN", "")

SYSTEM_PROMPT = """You are the operations assistant for Northwind Gear.

Work in this order, and do not skip a step:
1. call list_orders with status delayed;
2. open a ticket for every delayed order whose units are above 100, using create_ticket;
3. call get_customer for CUS-7781 to find who to escalate to.

Then answer in at most five sentences: how many delayed orders there are, which
order ids got a ticket, and the account manager to escalate to. Quote the numbers
you were given. Never invent an order id or a customer id.
"""

_cache: dict[str, Any] = {"token": None, "expires": 0.0}


def client_credentials() -> dict:
    """Read the machine client from Secrets Manager, once per process."""
    if "client" in _cache:
        return _cache["client"]
    client = boto3.client("secretsmanager", region_name=REGION)
    raw = client.get_secret_value(SecretId=SECRET_ARN)["SecretString"]
    _cache["client"] = json.loads(raw)
    return _cache["client"]


def bearer() -> str:
    """A token the gateway will accept, refreshed before it expires."""
    if _cache["token"] and time.time() < float(_cache["expires"]) - 60:
        return str(_cache["token"])
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
    log.info("minted a gateway token, expires in %ss", payload.get("expires_in"))
    return payload["access_token"]


def mcp_call(tool_name: str, arguments: dict) -> dict:
    """One MCP tools/call against the gateway, with a fresh bearer."""
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
    ).encode()
    req = urllib.request.Request(
        GATEWAY_MCP_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            "authorization": f"Bearer {bearer()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
    except Exception as exc:  # noqa: BLE001 - the message is the diagnostic
        body = ""
        if hasattr(exc, "read"):
            try:
                body = exc.read().decode()[:200]
            except Exception:  # noqa: BLE001
                body = ""
        raise RuntimeError(
            f"gateway call failed: {type(exc).__name__}: {exc} "
            f"target={GATEWAY_MCP_URL or '<empty>'} body={body}"
        ) from exc
    if raw.startswith("event:"):
        for line in raw.splitlines():
            if line.startswith("data: "):
                raw = line[6:]
                break
    payload = json.loads(raw)
    if "error" in payload:
        raise RuntimeError(f"gateway error: {payload['error']}")
    result = payload.get("result", {})
    blocks = result.get("content") or []
    text = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict))
    if result.get("isError"):
        raise RuntimeError(text or "tool returned an error")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


@tool
def list_orders(status: str = "delayed") -> dict:
    """List orders by status through the gateway, which adds its own token.

    Args:
        status: Order status to filter on, one of delayed, shipped, cancelled.

    Returns:
        The order service payload, including how many units are outstanding.
    """
    return mcp_call("orders___listOrders", {"status": status})


@tool
def create_ticket(order_id: str, summary: str) -> dict:
    """Open a ticket for one order through the gateway.

    Args:
        order_id: Order id such as SO-1041.
        summary: One sentence describing what a human must do.

    Returns:
        The ticket id the ticketing system assigned.
    """
    return mcp_call("ticketing___createTicket", {"order_id": order_id, "summary": summary})


@tool
def get_customer(customer_id: str) -> dict:
    """Read a CRM record, including tier and account manager, through the gateway.

    Args:
        customer_id: Customer id such as CUS-7781.

    Returns:
        The CRM record for that customer.
    """
    return mcp_call("crm___getCustomer", {"customer_id": customer_id})


TOOLS = [list_orders, create_ticket, get_customer]

# One Agent per session id, bounded because one process serves many sessions.
MAX_SESSIONS = 128
_agents: "OrderedDict[str, Agent]" = OrderedDict()


def get_or_create_agent(session_id: str) -> Agent:
    if session_id in _agents:
        _agents.move_to_end(session_id)
        return _agents[session_id]
    if len(_agents) >= MAX_SESSIONS:
        _agents.popitem(last=False)
    _agents[session_id] = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=list(TOOLS),
        conversation_manager=NullConversationManager(),
    )
    return _agents[session_id]


def extract_prompt(payload: Any) -> str:
    """Accept a bare string or {"prompt": "..."}; reject anything else."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("prompt", "message", "input"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
    raise ValueError('payload must be a string or contain a "prompt" string')


def _text_delta(text: str, block_index: int) -> dict:
    """The streaming event shape BedrockAgentCoreApp forwards to the client."""
    return {
        "event": {
            "contentBlockDelta": {
                "delta": {"text": text},
                "contentBlockIndex": block_index,
            }
        }
    }


@app.entrypoint
async def invoke(payload: Any, context: Any):
    session_id = getattr(context, "session_id", "default-session")
    prompt = extract_prompt(payload)
    log.info("uc03 invoke: model_id=%s session_id=%s", model_id(), session_id)

    agent = get_or_create_agent(session_id)
    scrub = StreamSanitizer()
    block_index = 0
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        inner = event["event"]
        if not isinstance(inner, dict):
            yield event
            continue

        if "messageStart" in inner:
            scrub = StreamSanitizer()
            block_index = 0
            yield event
            continue
        if "messageStop" in inner:
            tail = scrub.flush()
            if tail:
                yield _text_delta(tail, block_index)
            yield event
            continue

        block = inner.get("contentBlockDelta")
        delta = block.get("delta") if isinstance(block, dict) else None
        if not isinstance(delta, dict) or "text" not in delta:
            yield event
            continue
        block_index = block.get("contentBlockIndex", block_index)
        clean = scrub.feed(delta["text"])
        if clean:
            yield _text_delta(clean, block_index)


if __name__ == "__main__":
    app.run()
