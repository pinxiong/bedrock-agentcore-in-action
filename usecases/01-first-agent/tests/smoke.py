#!/usr/bin/env python3
"""smoke.py for uc01 · 01-first-agent

This file is the executable definition of "done" for this use case. It talks to
the real deployment and proves the two capabilities uc01 declares:

  runtime        the agent is deployed as a managed runtime that answers calls
  observability  each call leaves a trace you can inspect, tool calls included

The tests are deliberately concrete: they invoke the deployed agent and read the
trace that invoke produced. Nothing here can pass against a stopped runtime.

Contract with shared/scripts/verify-coverage.py:
  * CAPABILITY_ASSERTIONS maps each capability this use case declares as `deep`
    to the list of assertions that prove it. The verifier fails CI if a declared
    capability is absent here.
  * Each assertion string maps to a function named assert_<capability>_<n>.
    An unimplemented function is a hard failure, so a half-finished use case can
    never be mistaken for a finished one.

Run:  python aia.py test 01   # or: python tests/smoke.py --usecase 01

The run makes exactly one billable invoke; the observability check reuses it.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

USE_CASE = "uc01"

# ── what this use case asserts ──────────────────────────────────────────────
# Everything below is measured against the deployed agent, not mocked.
RUNTIME_PREFIX = "aiauc01_"
PROMPT = "What is 21 plus 21? Use the tool."
EXPECTED = "42"
TOOL_NAME = "add_numbers"

CAPABILITY_ASSERTIONS: dict[str, list[str]] = {
    "runtime": [
        "the runtime exists in the target region and reports status READY",
        "invoking it answers a tool-using prompt and the reply has no model scaffolding",
    ],
    "observability": [
        "that same invoke left an X-Ray trace whose span tree contains an execute_tool span",
    ],
}

OTHER_USE_CASE_NUMBERS = [n for n in ("01", "02", "03", "04", "05", "06", "07") if n != "01"]

USE_CASE_DIR = Path(__file__).resolve().parent.parent
TARGETS_FILE = USE_CASE_DIR / "agentcore" / "aws-targets.json"

RESET, RED, GREEN, YELLOW, DIM = "\033[0m", "\033[31m", "\033[32m", "\033[33m", "\033[2m"


# ── environment ─────────────────────────────────────────────────────────────
def region() -> str:
    """The region this deployment lives in, read from the deployment target."""
    try:
        return json.loads(TARGETS_FILE.read_text())[0]["region"]
    except Exception:  # noqa: BLE001
        return os.environ.get("AWS_REGION", "us-east-1")


def _client(service: str):
    import boto3

    return boto3.Session(region_name=region()).client(service)


def assert_credentials() -> None:
    from botocore.exceptions import NoCredentialsError

    try:
        _client("sts").get_caller_identity()
    except NoCredentialsError as exc:
        raise AssertionError(
            "no usable AWS credentials. fix: make `aws sts get-caller-identity` work "
            f"for region {region()}, then re-run"
        ) from exc


# ── talking to the deployment ───────────────────────────────────────────────
def find_runtime() -> dict:
    client = _client("bedrock-agentcore-control")
    found: list[dict] = []
    token = None
    while True:
        kwargs: dict = {"maxResults": 50}
        if token:
            kwargs["nextToken"] = token
        resp = client.list_agent_runtimes(**kwargs)
        found += [
            r
            for r in resp.get("agentRuntimes", [])
            if str(r.get("agentRuntimeName", "")).startswith(RUNTIME_PREFIX)
        ]
        token = resp.get("nextToken")
        if not token:
            break

    if not found:
        raise AssertionError(
            f"no runtime named {RUNTIME_PREFIX}* in {region()}. "
            "fix: from this use case's root run `agentcore deploy -y --target default`"
        )
    if len(found) > 1:
        names = ", ".join(r["agentRuntimeName"] for r in found)
        raise AssertionError(f"expected one {RUNTIME_PREFIX}* runtime, found {len(found)}: {names}")
    return found[0]


def invoke(prompt: str = PROMPT) -> dict:
    """One invoke against the deployed runtime. Returns the two channels that matter.

    The runtime streams Server-Sent Events. The text channel is what a user reads;
    the contentBlockStart channel is what the agent asked the model to run. Keeping
    them separate is what lets the assertions below tell "answered with a tool" apart
    from "answered from memory".
    """
    runtime = find_runtime()
    started_at = time.time()
    resp = _client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=runtime["agentRuntimeArn"],
        payload=json.dumps({"prompt": prompt}).encode(),
        contentType="application/json",
    )
    raw = resp["response"].read().decode("utf-8", "replace")

    texts: list[str] = []
    tools: list[str] = []
    events = 0
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk:
            continue
        try:
            payload = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        event = payload.get("event", payload)
        if not isinstance(event, dict):
            continue
        events += 1

        delta = (event.get("contentBlockDelta") or {}).get("delta") or {}
        if isinstance(delta.get("text"), str):
            texts.append(delta["text"])

        start = (event.get("contentBlockStart") or {}).get("start") or {}
        name = (start.get("toolUse") or {}).get("name")
        if name:
            tools.append(name)

    return {
        "text": "".join(texts),
        "tools": tools,
        "session_id": resp.get("runtimeSessionId"),
        "events": events,
        "started_at": started_at,
    }


_LAST_INVOKE: dict | None = None


def last_invoke() -> dict:
    """The single invoke shared by the runtime and observability assertions."""
    global _LAST_INVOKE
    if _LAST_INVOKE is None:
        _LAST_INVOKE = invoke()
    return _LAST_INVOKE


# ── capability checks ───────────────────────────────────────────────────────
def assert_runtime_1() -> None:
    """The runtime is there and the service considers it able to serve traffic."""
    runtime = find_runtime()
    if runtime.get("status") != "READY":
        raise AssertionError(
            f"{runtime['agentRuntimeName']} reports status {runtime.get('status')!r}, not READY"
        )
    print(
        f"       {runtime['agentRuntimeName']} v{runtime.get('agentRuntimeVersion')} · "
        f"{runtime['agentRuntimeArn']}"
    )


def assert_runtime_2() -> None:
    """The agent answers through its own tool, and the reply is safe to show a user."""
    result = last_invoke()
    print(f"       session {result['session_id']} · {result['events']} events · tools {result['tools']}")
    print(f"       reply {result['text'].strip()!r}")

    if TOOL_NAME not in result["tools"]:
        raise AssertionError(
            f"the agent answered without calling {TOOL_NAME} (tools seen: {result['tools']}); "
            f"prompt was {PROMPT!r}"
        )
    if EXPECTED not in result["text"]:
        raise AssertionError(f"the reply does not contain {EXPECTED!r}: {result['text']!r}")
    for marker in ("DSML", "<thinking>"):
        if marker in result["text"]:
            raise AssertionError(
                f"model scaffolding leaked into the reply: {marker!r} in {result['text']!r}"
            )


def assert_observability_1() -> None:
    """The invoke above is traceable: its span tree shows the tool call, not just text."""
    result = last_invoke()
    runtime_name = find_runtime()["agentRuntimeName"]
    # Only look at traces that started after this invoke, otherwise an older trace
    # from a previous run would satisfy the assertion and prove nothing.
    since = result["started_at"] - 60

    deadline = time.time() + 150
    reason = "no trace found yet"
    while time.time() < deadline:
        try:
            hit = _find_tool_trace(runtime_name, since=since)
        except Exception as exc:  # noqa: BLE001
            hit, reason = None, f"{exc.__class__.__name__}: {exc}"
        if hit:
            print(f"       trace {hit['id']} · span {hit['tool_span']!r}")
            return
        time.sleep(6)

    raise AssertionError(
        f"no X-Ray trace containing an execute_tool span showed up for {runtime_name} "
        f"within 150s ({reason}). fix: confirm transaction search is enabled in {region()}; "
        "indexing can lag a few minutes"
    )


def _find_tool_trace(runtime_name: str, since: float) -> dict | None:
    from datetime import datetime, timedelta, timezone

    xray = _client("xray")
    start = datetime.fromtimestamp(since, tz=timezone.utc)
    end = datetime.now(timezone.utc)
    if end <= start:
        return None
    stamp = "%Y-%m-%dT%H:%M:%S"

    summaries = xray.get_trace_summaries(
        StartTime=start.strftime(stamp), EndTime=end.strftime(stamp)
    ).get("TraceSummaries", [])
    ids = [
        s["Id"]
        for s in summaries
        if any(runtime_name in str(sid.get("Name", "")) for sid in s.get("ServiceIds", []))
    ]
    if not ids:
        return None

    for trace in xray.batch_get_traces(TraceIds=ids[:5]).get("Traces", []):
        for segment in trace.get("Segments", []):
            doc = json.loads(segment["Document"])
            if not str(doc.get("name", "")).startswith(runtime_name):
                continue
            span = _first_span(doc.get("subsegments", []), "execute_tool")
            if span:
                return {"id": trace["Id"], "tool_span": span}
    return None


def _first_span(subsegments: list, prefix: str) -> str | None:
    for sub in subsegments:
        if str(sub.get("name", "")).startswith(prefix):
            return sub["name"]
        found = _first_span(sub.get("subsegments", []), prefix)
        if found:
            return found
    return None


def assert_independence_1(client=None) -> None:
    """No resource belonging to another use case exists in this account."""
    from resourcegroupstaggingapi_check import check_other_use_cases

    check_other_use_cases(USE_CASE, OTHER_USE_CASE_NUMBERS)


# ── runner ──────────────────────────────────────────────────────────────────
def run() -> int:
    try:
        assert_credentials()
    except Exception as exc:  # noqa: BLE001
        print(f"{RED}FAIL{RESET} cannot reach AWS: {exc}")
        return 1

    passed, failed = 0, 0
    for capability, assertions in CAPABILITY_ASSERTIONS.items():
        print(f"\n{DIM}{capability}{RESET}")
        for idx, text in enumerate(assertions, start=1):
            name = f"assert_{capability.replace('-', '_')}_{idx}"
            fn = globals().get(name)
            if fn is None:
                print(f"  {RED}FAIL{RESET} {name}: not implemented  ({text})")
                failed += 1
                continue
            try:
                fn()
                print(f"  {GREEN}PASS{RESET} {name}: {text}")
                passed += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  {RED}FAIL{RESET} {name}: {text}")
                print(f"       {exc}")
                if "--traceback" in sys.argv:
                    traceback.print_exc()
                failed += 1

    # the independence assertion every use case carries
    try:
        assert_independence_1()
        print(f"\n  {GREEN}PASS{RESET} independence: no other use case's resources present")
        passed += 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n  {RED}FAIL{RESET} independence: {exc}")
        failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


def _use_case_python() -> Path | None:
    for rel in ("src/.venv/bin/python", "src/.venv/Scripts/python.exe"):
        candidate = USE_CASE_DIR / rel
        if candidate.exists():
            return candidate
    return None


def _reexec_with_use_case_python() -> None:
    """boto3 lives in the use case's own venv, so run this file with that python.

    Without this, `python tests/smoke.py` fails on any interpreter that does not
    happen to have boto3 installed, which hides the real result behind an import error.
    """
    try:
        import boto3  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    if os.environ.get("AIA_SMOKE_REEXEC") == "1":
        raise AssertionError(
            "boto3 is not importable from the use case venv either. "
            "fix: cd src && uv sync  (or `pip install boto3`), then re-run"
        )

    python = _use_case_python()
    if python is None:
        raise AssertionError(
            "no virtualenv at src/.venv, and boto3 is not installed here. "
            "fix: cd src && uv sync, then re-run"
        )

    os.environ["AIA_SMOKE_REEXEC"] = "1"
    raise SystemExit(
        subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usecase", default=USE_CASE.replace("uc", ""))
    ap.add_argument("--traceback", action="store_true")
    args, _ = ap.parse_known_args()
    if args.usecase != USE_CASE.replace("uc", ""):
        sys.exit(f"this smoke test belongs to {USE_CASE}")

    try:
        _reexec_with_use_case_python()
    except AssertionError as exc:
        print(f"{RED}FAIL{RESET} smoke.py cannot start: {exc}")
        return 2

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
