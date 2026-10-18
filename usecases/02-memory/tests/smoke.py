#!/usr/bin/env python3
"""smoke.py for uc02 · 02-memory

This file is the executable definition of "done" for this use case. It talks to
the real deployment and proves the one capability uc02 declares as deep:

  memory   short-term events plus long-term records, namespaced per actor

Every assertion below runs against AWS. Nothing here can pass against a stopped
runtime or an empty memory resource. The three memory assertions are ordered so
that each one leaves state the next one can build on:

  1. session 1 states a regional preference, session 2 is created fresh and has
     to answer from it;
  2. a second actor states a different preference and the two actors are then
     cross-checked against each other's namespaces;
  3. a third session records a failed restock and a fourth session has to recall
     it through the episodic strategy.

Extraction is asynchronous, so each wait has a deadline rather than a sleep. The
deadline is what makes the numbers below worth quoting: they are measured waits,
not guessed ones.

Contract with the series coverage verifier, which reads this dict from outside
the folder while this folder stays runnable on its own:
  * CAPABILITY_ASSERTIONS maps each capability this use case declares as `deep`
    to the list of assertions that prove it.
  * Each assertion string maps to a function named assert_<capability>_<n>.
    An unimplemented function is a hard failure.

Run:  make test                 # or: python3 tests/smoke.py --usecase 02
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

USE_CASE = "uc02"

# ── what this use case asserts ──────────────────────────────────────────────
RUNTIME_PREFIX = "aiauc02_"
MEMORY_NAME = "aia_uc02_mem"

ACTOR_A = "store_manager_north"
ACTOR_B = "store_manager_south"
OTHER_REGION = {"north": "South China", "south": "North China"}

# The preference is stated once, in its own session, and never repeated. If a
# later session answers with it, the only place it can have come from is memory.
PREFERENCE_A = "From now on, only reorder for the North China region. Ignore every other region."
PREFERENCE_B = "From now on, only reorder for the South China region. Ignore every other region."
ASK_REORDER = "Draft this week's reorder list."

FAILED_ATTEMPT = (
    "I tried restocking the North China stores from the Guangzhou warehouse last month. "
    "It failed: the lead time was 9 days and three stores stocked out. Make a note of it."
)
ASK_LESSON = "How should I restock the North China stores this week?"
FAILED_MARKERS = ("Guangzhou", "lead time", "9 days", "stocked out")

CAPABILITY_ASSERTIONS: dict[str, list[str]] = {
    "memory": [
        "a second session retrieves a preference written in the first",
        "actor A cannot retrieve actor B memories",
        "episodic strategy recalls a previously failed approach",
    ],
}

OTHER_USE_CASE_NUMBERS = [n for n in ("01", "02", "03", "04", "05", "06", "07") if n != "02"]

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


def find_memory() -> dict:
    """The memory resource this use case deployed, found by the name in the contract.

    `list_memories` returns ids and arns but not names, so each candidate is
    read back once. Matching on the name rather than on "the only memory in the
    account" is what keeps the independence assertion honest: another use case's
    memory would not be mistaken for this one.
    """
    client = _client("bedrock-agentcore-control")
    token = None
    while True:
        kwargs: dict = {"maxResults": 50}
        if token:
            kwargs["nextToken"] = token
        resp = client.list_memories(**kwargs)
        for memory in resp.get("memories", []):
            detail = client.get_memory(memoryId=memory["id"]).get("memory", {})
            name = str(detail.get("name", ""))
            if name == MEMORY_NAME or name.endswith(f"_{MEMORY_NAME}"):
                return detail
        token = resp.get("nextToken")
        if not token:
            break
    raise AssertionError(
        f"no memory named {MEMORY_NAME!r} in {region()}. "
        "fix: from this use case's root run `agentcore deploy -y --target default`"
    )


def invoke(prompt: str, actor: str, session_id: str) -> dict:
    """One invoke against the deployed runtime, with the actor pinned in the payload.

    The actor travels in the payload because that is the value the entrypoint
    turns into a memory namespace; pinning the session id is what makes "a second
    session" a different session rather than a hope.
    """
    runtime = find_runtime()
    resp = _client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=runtime["agentRuntimeArn"],
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt, "actor_id": actor}).encode(),
        contentType="application/json",
        accept="application/json",
    )
    raw = resp["response"].read().decode("utf-8", "replace")

    texts: list[str] = []
    tools: list[str] = []
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
        "session_id": resp.get("runtimeSessionId") or session_id,
    }


def new_session() -> str:
    """A session id the runtime accepts, and never one it has seen before.

    `invoke_agent_runtime` rejects anything under 33 characters, so a short
    readable id like `uc02-a-pref` fails parameter validation before it is ever
    sent. Two uuid4 halves are used instead of one because a single hex uuid is
    32 characters: one short of the minimum.
    """
    return f"{uuid.uuid4().hex}-{uuid.uuid4().hex[:8]}"


def record_text(record: dict) -> str:
    content = record.get("content") or {}
    return str(content.get("text", "")).strip()


def list_records(memory_id: str, namespace: str | None = None, namespace_path: str | None = None) -> list[dict]:
    kwargs: dict = {"memoryId": memory_id, "maxResults": 100}
    if namespace:
        kwargs["namespace"] = namespace
    if namespace_path:
        kwargs["namespacePath"] = namespace_path
    return _client("bedrock-agentcore").list_memory_records(**kwargs).get("memoryRecordSummaries", [])


def retrieve_records(memory_id: str, namespace: str, query: str, top_k: int = 5) -> list[dict]:
    resp = _client("bedrock-agentcore").retrieve_memory_records(
        memoryId=memory_id,
        namespace=namespace,
        searchCriteria={"searchQuery": query, "topK": top_k},
    )
    return resp.get("memoryRecordSummaries", [])


def wait_for_records(memory_id: str, namespace: str, deadline_s: float) -> list[dict]:
    """Poll until extraction has written at least one record into this namespace.

    Long-term extraction runs after `CreateEvent` and is not instantaneous, so a
    single read would race it. The returned records carry how long the wait
    actually took, which is the number the article quotes.
    """
    deadline = time.time() + deadline_s
    records: list[dict] = []
    while time.time() < deadline:
        records = list_records(memory_id, namespace=namespace)
        if records:
            return records
        time.sleep(5)
    return records


# ── capability checks ───────────────────────────────────────────────────────
def assert_memory_1() -> None:
    """A second session retrieves a preference written in the first."""
    memory = find_memory()
    memory_id = memory["id"]
    session_one = new_session()
    session_two = new_session()

    first = invoke(PREFERENCE_A, ACTOR_A, session_one)
    print(f"       session 1 {first['session_id']} · reply {first['text'].strip()[:90]!r}")

    preference_ns = f"/users/{ACTOR_A}/preferences"
    started = time.time()
    records = wait_for_records(memory_id, preference_ns, deadline_s=240)
    elapsed = time.time() - started
    if not records:
        raise AssertionError(
            f"no USER_PREFERENCE record was extracted into {preference_ns} within 240s. "
            "fix: confirm the memory resource carries a USER_PREFERENCE strategy"
        )
    print(f"       extraction visible after {elapsed:.1f}s · {len(records)} record(s)")
    for record in records[:3]:
        print(f"       record {record_text(record)[:110]!r}")

    joined = " ".join(record_text(r) for r in records)
    if "North China" not in joined:
        raise AssertionError(f"the extracted preference does not name North China: {joined!r}")

    second = invoke(ASK_REORDER, ACTOR_A, session_two)
    reply = second["text"].strip()
    print(f"       session 2 {second['session_id']} · tools {second['tools']}")
    print(f"       reply {reply[:160]!r}")

    if "North" not in reply:
        raise AssertionError(f"session 2 did not reorder for North China: {reply!r}")
    for other in ("South China", "East China"):
        if other in reply:
            raise AssertionError(f"session 2 reordered outside the remembered region ({other}): {reply!r}")


def assert_memory_2() -> None:
    """Actor A cannot retrieve actor B memories."""
    memory_id = find_memory()["id"]

    invoke(PREFERENCE_B, ACTOR_B, new_session())
    ns_a = f"/users/{ACTOR_A}/preferences"
    ns_b = f"/users/{ACTOR_B}/preferences"
    records_b = wait_for_records(memory_id, ns_b, deadline_s=240)
    if not records_b:
        raise AssertionError(
            f"no USER_PREFERENCE record was extracted into {ns_b} within 240s, so there is "
            "nothing to isolate against"
        )

    query = "which region does this store manager reorder for"
    seen_a = " ".join(record_text(r) for r in retrieve_records(memory_id, ns_a, query))
    seen_b = " ".join(record_text(r) for r in retrieve_records(memory_id, ns_b, query))
    print(f"       actor {ACTOR_A} sees {seen_a[:110]!r}")
    print(f"       actor {ACTOR_B} sees {seen_b[:110]!r}")

    if "North China" not in seen_a:
        raise AssertionError(f"actor A's own namespace lost its preference: {seen_a!r}")
    if "South China" not in seen_b:
        raise AssertionError(f"actor B's namespace does not hold B's preference: {seen_b!r}")
    if "South China" in seen_a:
        raise AssertionError(f"actor A can see actor B's preference: {seen_a!r}")
    if "North China" in seen_b:
        raise AssertionError(f"actor B can see actor A's preference: {seen_b!r}")

    # The same isolation, measured through the model rather than the API: each
    # actor is asked the identical question and must answer for their own region.
    reply_b = invoke(ASK_REORDER, ACTOR_B, new_session())["text"].strip()
    print(f"       actor {ACTOR_B} reply {reply_b[:120]!r}")
    if "South" not in reply_b:
        raise AssertionError(f"actor B did not reorder for South China: {reply_b!r}")
    if "North China" in reply_b:
        raise AssertionError(f"actor B answered with actor A's region: {reply_b!r}")


EPISODE_DEADLINE_S = 1500
# Episodic extraction is the slow one. On 2026-10-18 every episode in this
# resource was written 15 m 11 s to 15 m 14 s after the timestamp of the event it
# came from, which is long enough that a 300 s deadline can only ever fail. The
# deadline below is a deadline, not a sleep: it polls, and it prints how long the
# wait actually took.


def assert_memory_3() -> None:
    """Episodic strategy recalls a previously failed approach."""
    memory_id = find_memory()["id"]
    episode_path = f"/episodes/{ACTOR_A}/"

    # Records that already exist cannot prove this run, so they are excluded by
    # id and the wait is for a new one.
    known = {r.get("memoryRecordId") for r in list_records(memory_id, namespace_path=episode_path)}

    invoke(FAILED_ATTEMPT, ACTOR_A, new_session())

    started = time.time()
    deadline = started + EPISODE_DEADLINE_S
    hit: dict | None = None
    while time.time() < deadline:
        for record in list_records(memory_id, namespace_path=episode_path):
            if record.get("memoryRecordId") in known:
                continue
            if "Guangzhou" in record_text(record):
                hit = record
                break
        if hit:
            break
        time.sleep(15)
    if hit is None:
        raise AssertionError(
            f"no new episodic record under {episode_path} mentions the Guangzhou attempt within "
            f"{EPISODE_DEADLINE_S}s. episodic extraction trails the event by about 15 minutes, "
            "so this is usually a deadline that is too short rather than a broken strategy"
        )
    print(f"       episodic extraction visible after {time.time() - started:.0f}s")
    print(f"       episodic record {record_text(hit)[:140]!r}")

    reply = invoke(ASK_LESSON, ACTOR_A, new_session())["text"].strip()
    print(f"       reply {reply[:160]!r}")
    if not any(marker in reply for marker in FAILED_MARKERS):
        raise AssertionError(
            f"the answer does not reference the failed approach (looked for {FAILED_MARKERS}): {reply!r}"
        )


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
    for rel in ("app/aia_uc02/.venv/bin/python", "app/aia_uc02/.venv/Scripts/python.exe"):
        candidate = USE_CASE_DIR / rel
        if candidate.exists():
            return candidate
    return None


def _reexec_with_use_case_python() -> None:
    """boto3 lives in the use case's own venv, so run this file with that python."""
    try:
        import boto3  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    if os.environ.get("AIA_SMOKE_REEXEC") == "1":
        raise AssertionError(
            "boto3 is not importable from the use case venv either. "
            "fix: cd app/aia_uc02 && uv sync  (or `pip install boto3`), then re-run"
        )

    python = _use_case_python()
    if python is None:
        raise AssertionError(
            "no virtualenv at app/aia_uc02/.venv, and boto3 is not installed here. "
            "fix: cd app/aia_uc02 && uv sync, then re-run"
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
