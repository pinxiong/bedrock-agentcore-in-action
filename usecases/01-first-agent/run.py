#!/usr/bin/env python3
"""run.py for uc01 · 01-first-agent

Every operation this use case needs, run from inside this folder. This is the
entry point that makes the folder stand alone: nothing here reads a path outside
the directory, so copying the directory anywhere gives you a working project.

    python3 run.py doctor      # is this machine and this folder ready?
    python3 run.py deploy      # deploy it
    python3 run.py test        # assert the deployed capabilities
    python3 run.py down        # destroy it
    python3 run.py --list      # everything else

A `Makefile` sits next to this file and forwards to these same targets, because
`make check` reads better than `python3 run.py check`. It holds no logic of its
own on purpose: two entry points that both implement the steps would drift, and
`tests/copy_check.py` asserts that the two target lists match.

Why Python and not a shell script: the series promises the same commands on
macOS, Linux and Windows. `python3 run.py` is the only form that holds there.

Use `--dry-run` to see the commands without running them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

USE_CASE_DIR = Path(__file__).resolve().parent
USE_CASE_NUMBER = "01"
APP_DIR = "app/aia_uc01"
DEFAULT_TARGET = "default"
DEFAULT_PROMPT = "What is 21 plus 21? Use the tool."

DRY_RUN = False


# --------------------------------------------------------------------------- #
# plumbing                                                                     #
# --------------------------------------------------------------------------- #


def shell(cmd: list[str], cwd: Path | None = None) -> int:
    """Run a command with this folder as the working directory."""
    where = cwd or USE_CASE_DIR
    printable = " ".join(cmd)
    if DRY_RUN:
        print(f"  [{where.name}] {printable}")
        return 0
    print(f">> {printable}", flush=True)
    try:
        return subprocess.call(cmd, cwd=where)
    except FileNotFoundError:
        print(f"   not found: {cmd[0]}")
        return 127


def python_step(relative: str, *extra: str) -> int:
    return shell([sys.executable, relative, *extra])


def uv_sync() -> int:
    if shutil.which("uv") is None:
        print("   uv is not on PATH. install it, or run: pip install -r requirements")
        return 127
    return shell(["uv", "sync"], cwd=USE_CASE_DIR / APP_DIR)


# --------------------------------------------------------------------------- #
# targets                                                                      #
# --------------------------------------------------------------------------- #


def t_help(_args: argparse.Namespace) -> int:
    print(f"{USE_CASE_NUMBER} · First Agent — targets")
    print()
    width = max(len(name) for name in TARGETS)
    for name, (summary, _fn) in TARGETS.items():
        print(f"  python3 run.py {name.ljust(width)}  {summary}")
    print()
    print(f'  python3 run.py invoke --prompt "..."     ask a different question')
    print("  python3 run.py <target> --dry-run        print the commands, run nothing")
    return 0


def t_doctor(_args: argparse.Namespace) -> int:
    return python_step("tests/doctor.py")


def t_check(args: argparse.Namespace) -> int:
    extra = ["--quick"] if getattr(args, "quick", False) else []
    return python_step("tests/copy_check.py", *extra)


def t_sync(_args: argparse.Namespace) -> int:
    return uv_sync()


def t_unit(_args: argparse.Namespace) -> int:
    venv = USE_CASE_DIR / APP_DIR / ".venv"
    interpreter = next(
        (p for p in (venv / "bin" / "python", venv / "Scripts" / "python.exe") if p.exists()),
        None,
    )
    if interpreter is None:
        print(f"   no environment at {APP_DIR}/.venv. run it first: python3 run.py sync")
        return 2
    return shell([str(interpreter), "tests/test_sanitize.py"])


def t_test(_args: argparse.Namespace) -> int:
    return python_step("tests/smoke.py", "--usecase", USE_CASE_NUMBER)


def t_verify(args: argparse.Namespace) -> int:
    for step in (t_check, t_test):
        rc = step(args)
        if rc != 0:
            return rc
    return 0


def t_dev(_args: argparse.Namespace) -> int:
    return shell(["agentcore", "dev", "-l"])


def t_deploy(args: argparse.Namespace) -> int:
    return shell(["agentcore", "deploy", "-y", "--target", args.target_name])


def t_status(args: argparse.Namespace) -> int:
    return shell(["agentcore", "status"])


def t_invoke(args: argparse.Namespace) -> int:
    prompt = args.prompt or os.environ.get("AIA_PROMPT") or DEFAULT_PROMPT
    return shell(["agentcore", "invoke", "--prompt", prompt])


def t_traces(_args: argparse.Namespace) -> int:
    return shell(["agentcore", "traces", "list"])


def t_logs(_args: argparse.Namespace) -> int:
    return shell(["agentcore", "logs"])


def t_down(args: argparse.Namespace) -> int:
    # `remove all` empties the local contract; the deploy that follows is what
    # reconciles the stack to nothing. Order matters and both must run.
    rc = shell(["agentcore", "remove", "all"])
    if rc != 0:
        print("   `agentcore remove all` failed; stopping before the reconciling deploy")
        return rc
    rc = shell(["agentcore", "deploy", "-y", "--target", args.target_name])
    print(">> now walk the Cleanup checklist in README section 10")
    print(">> agentcore.json was rewritten; restore it before deploying again")
    return rc


def t_clean(_args: argparse.Namespace) -> int:
    removed = []
    for rel in ("agentcore/cdk/cdk.out", "agentcore/cache", "agentcore/.cache"):
        path = USE_CASE_DIR / rel
        if path.exists():
            if DRY_RUN:
                print(f"  [{USE_CASE_DIR.name}] rm -rf {rel}")
            else:
                shutil.rmtree(path, ignore_errors=True)
                removed.append(rel)
    if not DRY_RUN:
        print(f"removed {', '.join(removed) if removed else 'nothing'}; AWS was not touched")
    return 0


TARGETS: dict[str, tuple[str, object]] = {
    "check": ("assert this folder stands alone, by copying it", t_check),
    "doctor": ("check the toolchain, credentials and this folder", t_doctor),
    "sync": ("build the app environment from the lockfile", t_sync),
    "unit": ("run the offline unit tests, no AWS involved", t_unit),
    "test": ("run the capability assertions against the deployment", t_test),
    "verify": ("check + test, in that order", t_verify),
    "dev": ("run the agent locally, a real model, no deployment", t_dev),
    "deploy": ("deploy this use case on its own", t_deploy),
    "status": ("show the deployment state", t_status),
    "invoke": ("call the deployed agent", t_invoke),
    "traces": ("list recent traces", t_traces),
    "logs": ("tail the runtime logs", t_logs),
    "down": ("destroy only this use case", t_down),
    "clean": ("remove local build residue, never touches AWS", t_clean),
    "help": ("show this list", t_help),
}


# --------------------------------------------------------------------------- #
# runner                                                                       #
# --------------------------------------------------------------------------- #


def main() -> int:
    global DRY_RUN
    ap = argparse.ArgumentParser(
        prog="run.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("target", nargs="?", default="help", choices=[*TARGETS, "all"])
    ap.add_argument("--prompt", help=f"for invoke (default: {DEFAULT_PROMPT!r})")
    ap.add_argument("--target", dest="target_name", default=DEFAULT_TARGET, help="deployment target name")
    ap.add_argument("--quick", action="store_true", help="for check: skip the real-copy simulation")
    ap.add_argument("--dry-run", action="store_true", help="print the commands, run nothing")
    ap.add_argument("--list", action="store_true", help="print the target names only, one per line")
    args = ap.parse_args()

    if args.list:
        for name in TARGETS:
            print(name)
        return 0

    DRY_RUN = args.dry_run
    if args.target == "all":
        targets = [n for n in TARGETS if n not in {"help", "all"}]
    else:
        targets = [args.target]

    for name in targets:
        if len(targets) > 1:
            print(f"\n=== {name} ===")
        rc = TARGETS[name][1](args)  # type: ignore[operator]
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
