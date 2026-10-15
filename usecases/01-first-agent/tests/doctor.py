#!/usr/bin/env python3
"""doctor.py for uc01 · 01-first-agent

The environment self-check for this use case, and deliberately self-contained:
it reads only this folder, uses only the standard library, and needs no
repository around it.

Every check states what it looked for and how to fix a failure, because the
whole value of a doctor script is the fix line.

Run:  make doctor
      python3 tests/doctor.py
      python3 tests/doctor.py --offline     # skip the three calls that need AWS

Exit code 0 = ready to deploy, 2 = at least one blocking problem.
Warnings never block: a warning means "this will still work, but know why".
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
USE_CASE_DIR = HERE.parent
USE_CASE_NUMBER = "01"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Doctor:
    def __init__(self) -> None:
        self.failed = 0
        self.warned = 0
        self.passed = 0

    def pass_(self, msg: str) -> None:
        self.passed += 1
        print(f"  {GREEN}PASS{RESET}  {msg}")

    def fail(self, msg: str, fix: str) -> None:
        self.failed += 1
        print(f"  {RED}FAIL{RESET}  {msg}")
        print(f"        fix: {fix}")

    def warn(self, msg: str, fix: str = "") -> None:
        self.warned += 1
        print(f"  {YELLOW}WARN{RESET}  {msg}")
        if fix:
            print(f"        note: {fix}")


def capture(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def contract() -> dict:
    return json.loads((USE_CASE_DIR / "agentcore" / "agentcore.json").read_text(encoding="utf-8"))


def target() -> dict:
    targets = json.loads((USE_CASE_DIR / "agentcore" / "aws-targets.json").read_text(encoding="utf-8"))
    return targets[0]


def runtime() -> dict:
    return (contract().get("runtimes") or [{}])[0]


def env_var(spec: dict, name: str, fallback: str = "") -> str:
    for entry in spec.get("envVars") or []:
        if entry.get("name") == name:
            return str(entry.get("value", ""))
    return fallback


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="skip the checks that call AWS")
    args = ap.parse_args()

    spec, tgt, rt = contract(), target(), runtime()
    region = tgt.get("region", "us-east-1")
    account = str(tgt.get("account", ""))
    model = env_var(rt, "MODEL_ID", "deepseek.v3.2")
    code_location = (rt.get("codeLocation") or "").rstrip("/")
    doc = Doctor()

    print(f"doctor · use case {USE_CASE_NUMBER} · {USE_CASE_DIR}")
    print()

    print("toolchain")
    py = ".".join(str(v) for v in sys.version_info[:3])
    minor = sys.version_info[1]
    if 10 <= minor <= 14:
        doc.pass_(f"python {py} (inside the CodeZip 3.10 to 3.14 range)")
    else:
        doc.fail(f"python {py} is outside the CodeZip range", "use Python 3.10 to 3.14")

    rc, out = capture(["node", "-v"])
    if rc == 0:
        major = int(out.lstrip("v").split(".")[0]) if out.lstrip("v")[0].isdigit() else 0
        if major >= 20:
            doc.pass_(f"node {out}")
        else:
            doc.fail(f"node {out} is too old", "the AgentCore CLI needs Node.js 20 or newer")
    else:
        doc.fail("node not found", "install Node.js 20 or newer")

    rc, out = capture(["aws", "--version"])
    doc.pass_(f"aws cli {out.split()[0]}") if rc == 0 else doc.fail(
        "aws cli not found", "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    )

    rc, uv = capture(["uv", "--version"]) if shutil.which("uv") else (127, "")
    if rc == 0 and uv:
        doc.pass_(f"{uv.split()[0]} {uv.split()[1]} (builds the app environment)")
    else:
        doc.warn("uv not found", "only needed to build the app venv; `make sync` uses it")

    print()
    print("agentcore cli")
    rc, out = capture(["agentcore", "--version"])
    if rc == 0 and out:
        doc.pass_(f"agentcore {out.splitlines()[0]}")
    elif out:
        doc.fail("agentcore exists but --version fails", "pip uninstall bedrock-agentcore-starter-toolkit")
        doc.warn("the old Python package shadows the npm CLI", "then confirm `agentcore` is the npm one")
    else:
        doc.fail("agentcore not found", "npm install -g @aws/agentcore")

    rc, _ = capture([sys.executable, "-m", "pip", "show", "bedrock-agentcore-starter-toolkit"])
    if rc == 0:
        doc.fail(
            "the python package bedrock-agentcore-starter-toolkit is installed",
            "pip uninstall bedrock-agentcore-starter-toolkit",
        )

    print()
    print("this folder")
    loc = USE_CASE_DIR / code_location
    if code_location and loc.is_dir():
        doc.pass_(f"codeLocation {code_location!r} exists")
    else:
        doc.fail(f"codeLocation {code_location!r} is missing", "restore the folder, or fix agentcore.json")
    venv = loc / ".venv"
    if venv.exists():
        doc.pass_(f"app environment present at {code_location}/.venv")
    else:
        doc.warn(
            "no .venv yet, so `make test` will ask you to build it",
            f"cd {code_location} && uv sync",
        )
    for name in ("run.py", "Makefile", "AGENTS.md", "tests/smoke.py", "tests/copy_check.py"):
        if (USE_CASE_DIR / name).exists():
            doc.pass_(f"{name} present")
        else:
            doc.fail(f"{name} is missing", "this folder is not self-contained; restore it")

    print()
    print("aws environment")
    if args.offline:
        doc.warn("--offline was passed", "the credential, region and model checks were skipped")
    else:
        rc, got = capture(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"])
        if rc == 0 and got and got != "None":
            if account and got != account:
                doc.warn(
                    f"credentials are for account {got}, but aws-targets.json names {account}",
                    "edit agentcore/aws-targets.json, or switch profile",
                )
            else:
                doc.pass_(f"credentials work, account {got}")
        else:
            doc.fail("aws sts get-caller-identity failed", "check AWS_PROFILE and your credentials")

        rc, got = capture(["aws", "configure", "get", "region"])
        if rc == 0 and got == region:
            doc.pass_(f"region is {region}")
        else:
            doc.warn(
                f"your default region is '{got or 'unset'}', this use case deploys to {region}",
                "the CLI reads agentcore/aws-targets.json, so the deployment region is unaffected",
            )

        rc, found = capture(
            [
                "aws", "bedrock", "list-foundation-models", "--region", region,
                "--query", f"modelSummaries[?modelId=='{model}'].modelId | [0]",
                "--output", "text",
            ]
        )
        if rc == 0 and found and found != "None":
            doc.pass_(f"model {model} is available in {region}")
        else:
            doc.warn(
                f"model {model} is not listed in {region}",
                "either it is only reachable through an inference profile, or access is not granted",
            )

    print()
    print(f"{doc.passed} passed, {doc.warned} warned, {doc.failed} failed")
    if doc.failed:
        print(f"\n{DIM}next: fix the FAIL lines above, then run `make deploy`{RESET}")
        return 2
    print(f"{DIM}next: make deploy{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
