"""A2A client helpers for the uc07 orchestrator.

The orchestrator reaches the two specialist agents over the A2A protocol.
Both specialists are AgentCore runtimes in the same project, so discovery is
a control-plane ListAgentRuntimes call plus a data-plane GetAgentCard call,
and the conversation itself is SigV4-signed JSON-RPC POSTs to each runtime's
/invocations URL. Nothing here is specific to this use case's business
logic; it is the smallest A2A client that exercises discovery, blocking
send, non-blocking send, streaming, polling and cancel.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import uuid

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from a2a.types import (
    CancelTaskRequest,
    GetTaskRequest,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendStreamingMessageRequest,
    TaskIdParams,
    TaskQueryParams,
    TextPart,
)

REGION = os.environ.get("AWS_REGION", "us-east-1")
DATA_PLANE = f"https://bedrock-agentcore.{REGION}.amazonaws.com"

_arn_cache: dict[str, str] = {}


def find_runtime_arn(name: str) -> str:
    """Resolve a project runtime's name to its ARN via the control plane."""
    if name in _arn_cache:
        return _arn_cache[name]
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    next_token = None
    while True:
        kwargs = {"maxResults": 100}
        if next_token:
            kwargs["nextToken"] = next_token
        page = client.list_agent_runtimes(**kwargs)
        for runtime in page.get("agentRuntimes", []):
            # the CLI prefixes runtime names with the project name on deploy:
            # aia_uc07_legal becomes aiauc07_aia_uc07_legal
            deployed = runtime.get("agentRuntimeName", "")
            if deployed == name or deployed.endswith("_" + name):
                arn = runtime["agentRuntimeArn"]
                _arn_cache[name] = arn
                return arn
        next_token = page.get("nextToken")
        if not next_token:
            break
    raise RuntimeError(f"runtime named {name} not found in {REGION}")


def fetch_agent_card(arn: str) -> dict:
    """Read the specialist's A2A agent card through the data plane."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.get_agent_card(agentRuntimeArn=arn)
    response.pop("ResponseMetadata", None)
    # the data plane wraps the card: {"runtimeSessionId": ..., "agentCard": {...}}
    return response.get("agentCard", response)


def runtime_url(arn: str) -> str:
    """The public invoke URL of an AgentCore runtime."""
    encoded = urllib.parse.quote(arn, safe="")
    return f"{DATA_PLANE}/runtimes/{encoded}/invocations?qualifier=DEFAULT"


def _signed_headers(url: str, body: str, session_id: str) -> dict:
    request = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        },
    )
    credentials = boto3.Session().get_credentials().get_frozen_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", REGION).add_auth(request)
    return dict(request.headers)


def _user_message(text: str) -> Message:
    return Message(
        role=Role.user,
        message_id=uuid.uuid4().hex,
        parts=[Part(root=TextPart(text=text))],
    )


def _result_or_raise(payload: dict) -> dict:
    if "error" in payload:
        raise RuntimeError(f"A2A error {payload['error'].get('code')}: {payload['error'].get('message')}")
    return payload.get("result", {})


def send_message(arn: str, text: str, session_id: str, blocking: bool = True) -> dict:
    """message/send: returns the Task. blocking=False hands the task back
    immediately in a working state, which is the async pattern."""
    request = SendMessageRequest(
        id=uuid.uuid4().hex,
        params=MessageSendParams(
            message=_user_message(text),
            configuration=MessageSendConfiguration(blocking=blocking),
        ),
    )
    body = request.model_dump_json(by_alias=True, exclude_none=True)
    url = runtime_url(arn)
    with httpx.Client(timeout=httpx.Timeout(300.0, connect=15.0)) as client:
        response = client.post(url, content=body, headers=_signed_headers(url, body, session_id))
        response.raise_for_status()
        return _result_or_raise(response.json())


def get_task(arn: str, task_id: str, session_id: str) -> dict:
    """tasks/get: poll the state of a task accepted non-blocking."""
    request = GetTaskRequest(id=uuid.uuid4().hex, params=TaskQueryParams(id=task_id))
    body = request.model_dump_json(by_alias=True, exclude_none=True)
    url = runtime_url(arn)
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        response = client.post(url, content=body, headers=_signed_headers(url, body, session_id))
        response.raise_for_status()
        return _result_or_raise(response.json())


def cancel_task(arn: str, task_id: str, session_id: str) -> dict:
    """tasks/cancel: the barge-in. Interrupts an in-flight task."""
    request = CancelTaskRequest(id=uuid.uuid4().hex, params=TaskIdParams(id=task_id))
    body = request.model_dump_json(by_alias=True, exclude_none=True)
    url = runtime_url(arn)
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        response = client.post(url, content=body, headers=_signed_headers(url, body, session_id))
        response.raise_for_status()
        return _result_or_raise(response.json())


async def stream_message(arn: str, text: str, session_id: str):
    """message/stream: yields each JSON-RPC result object as it arrives.

    The result objects are Task, TaskStatusUpdateEvent and
    TaskArtifactUpdateEvent shapes; the caller inspects kind/status/state.
    """
    request = SendStreamingMessageRequest(
        id=uuid.uuid4().hex,
        params=MessageSendParams(message=_user_message(text)),
    )
    body = request.model_dump_json(by_alias=True, exclude_none=True)
    url = runtime_url(arn)
    async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=15.0)) as client:
        async with client.stream(
            "POST", url, content=body, headers=_signed_headers(url, body, session_id)
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line[len("data:"):].strip())
                if "error" in payload:
                    raise RuntimeError(
                        f"A2A stream error {payload['error'].get('code')}: {payload['error'].get('message')}"
                    )
                if "result" in payload:
                    yield payload["result"]


def task_text(task: dict) -> str:
    """Pull every text part out of a Task's status message and artifacts."""
    texts: list[str] = []

    def collect(parts) -> None:
        for part in parts or []:
            if isinstance(part, dict) and part.get("kind") == "text" and part.get("text"):
                texts.append(part["text"])

    status = task.get("status") or {}
    collect((status.get("message") or {}).get("parts"))
    for artifact in task.get("artifacts") or []:
        collect(artifact.get("parts"))
    if not texts:
        for entry in task.get("history") or []:
            if entry.get("role") == "agent":
                collect(entry.get("parts"))
    return "\n".join(texts)
