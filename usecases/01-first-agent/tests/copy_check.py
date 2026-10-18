#!/usr/bin/env python3
"""copy_check.py for uc01 · 01-first-agent

The executable definition of "this folder stands alone".

The series promises one thing louder than anything else: you can copy any
use case folder out of this repository, drop it anywhere, and it still runs.
That promise is easy to write in a README and easy to break in practice. This
file turns it into an assertion:

  1. the files a use case needs in order to run are present in the folder;
  2. no file in the folder points at a path outside the folder, so nothing
     breaks when the parent repository is not there;
  3. the IaC contract is self-contained and carries the tags that make
     cleanup auditable;
  4. the folder survives an actual copy: it is copied to a temporary directory
     with the same ignore rules a reader would use, both trees are compared,
     and the checks above are re-run on the copy.

Check 4 is the one that matters. Checks 1 to 3 reason about the tree; check 4
builds a second tree and looks at it.

Run:  make check          # from this folder, works on a copy of this folder
      python3 tests/copy_check.py
      python3 tests/copy_check.py --quiet     # summary only

Exit code 0 = the folder stands alone, 1 = at least one FAIL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
USE_CASE_DIR = HERE.parent
USE_CASE_NUMBER = "01"
PROJECT_TAG = "agentcore-in-action"

# Directories that a reader would not copy, either because they are rebuilt
# locally or because they are third-party trees. Everything else must travel.
VENDOR_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "cdk.out",
    ".cache",
    ".cli",
    "dist",
    # Captured output from a real run: terminal logs, traces, screenshots. It is
    # proof, not source, and it carries this machine's paths and your account
    # id, both of which would trip the escape scan below.
    "evidence",
}
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".whl", ".so", ".dylib", ".pyc", ".lock", ".woff", ".woff2",
}
# `uv.lock` is text but huge; it is checked for existence, not scanned.
UNSCANNED_NAMES = {"uv.lock", "package-lock.json"}

# The tokens are assembled from pieces on purpose: a scanner that contains the
# strings it looks for has to exempt itself, and an exemption is exactly the
# crack a real escape would later slip through. Assembled tokens keep the
# scanner honestly uniform over every file, including this one.
#
# The parent hop is a regex rather than a substring because a printed path
# shortened with an ellipsis contains the same three characters and is not a
# hop at all.
PARENT_HOP = re.compile(r"(?<![\w.])\.\./")
ESCAPE_TOKENS: list[tuple[str, str, bool]] = [
    (PARENT_HOP.pattern, "a parent-directory hop", True),
    ("".join(["/", "Users", "/"]), "an absolute path from somebody's machine", False),
    ("".join(["shared", "/"]), "a repository-level shared tree", False),
    ("".join(["aia", ".py"]), "the repository-level runner", False),
]
# The vendored CDK project is a self-contained TypeScript app; its own `bin/`
# and `test/` files import the stack through a parent hop that never leaves the
# folder. That hop is the one tolerated form, and only there.
VENDORED_TS_ROOTS = {("agentcore", "cdk")}

CAPABILITY_HINT = "cf. README section 2.3 (the independence contract)"


class Report:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.passed = 0
        self.failed = 0
        self.notes: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed += 1
        if not self.quiet:
            print(f"  PASS  {msg}")

    def fail(self, msg: str) -> None:
        self.failed += 1
        print(f"  FAIL  {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def heading(self, msg: str) -> None:
        if not self.quiet:
            print(f"\n{msg}")

    def finish(self) -> int:
        if self.notes and not self.quiet:
            print()
            for n in self.notes:
                print(f"  NOTE  {n}")
        print(f"\n{self.passed} passed, {self.failed} failed")
        if self.failed:
            print(f"\nfix hint: {CAPABILITY_HINT}")
        return 1 if self.failed else 0


# --------------------------------------------------------------------------- #
# the contract itself                                                          #
# --------------------------------------------------------------------------- #


def contract() -> dict:
    path = USE_CASE_DIR / "agentcore" / "agentcore.json"
    return json.loads(path.read_text(encoding="utf-8"))


def code_location(spec: dict) -> str:
    runtimes = spec.get("runtimes") or []
    if not runtimes:
        raise SystemExit("agentcore.json declares no runtime, so there is nothing to run")
    loc = runtimes[0].get("codeLocation")
    if not loc:
        raise SystemExit("runtimes[0] declares no codeLocation")
    return loc.rstrip("/")


def required_files(spec: dict) -> list[str]:
    loc = code_location(spec)
    return [
        "run.py",
        "Makefile",
        "README.md",
        "AGENTS.md",
        "agentcore/agentcore.json",
        "agentcore/aws-targets.json",
        "agentcore/.gitignore",
        "tests/smoke.py",
        "tests/copy_check.py",
        "tests/doctor.py",
        "tests/resourcegroupstaggingapi_check.py",
        f"{loc}/main.py",
        f"{loc}/pyproject.toml",
    ]


# --------------------------------------------------------------------------- #
# 1. the files that must travel                                                #
# --------------------------------------------------------------------------- #


def check_required(rep: Report, root: Path) -> None:
    rep.heading("[1] every file this use case needs is in the folder")
    required = required_files(contract())
    missing = [f for f in required if not (root / f).exists()]
    if missing:
        for f in missing:
            rep.fail(f"missing {f}")
    else:
        rep.ok(f"all {len(required)} required files present")

    # A folder still carrying `src/` or `iac/` is carrying a layout the official
    # CLI never produces, and two layouts means two sources of truth.
    stale = [s for s in ("src", "iac", "scripts", "diagrams") if (root / s).is_dir()]
    if stale:
        for s in stale:
            rep.fail(f"leftover directory {s}/ (the CLI layout has no {s}/)")
    else:
        rep.ok("no leftover directories from an older layout")

    # A lockfile is not needed to run: the CLI resolves dependencies itself when
    # it packages the app. It is needed to run the *same* thing twice, so its
    # absence is a note rather than a failure.
    lock = root / code_location(contract()) / "uv.lock"
    if lock.exists():
        rep.ok(f"{lock.relative_to(root)} present, so the dependency graph is pinned")
    else:
        rep.note(f"no {lock.relative_to(root)} yet. run `make sync` to pin the dependency graph")


# --------------------------------------------------------------------------- #
# 2. the two entry points agree, and neither holds the logic alone              #
# --------------------------------------------------------------------------- #


def check_entry_points(rep: Report, root: Path) -> None:
    """`run.py` is the entry point; the Makefile is a wrapper that must not drift.

    Two entry points over one job is how a folder ends up with a command that
    works under `make` and silently does something else under `python run.py`.
    The assertion is cheap: same target names, and every recipe forwards.
    """
    rep.heading("[2] the in-folder entry points agree")
    script = root / "run.py"
    if not script.exists():
        rep.fail("run.py is missing, so there is no cross-platform entry point")
        return

    proc = subprocess.run(
        [sys.executable, "run.py", "--list"], cwd=root, capture_output=True, text=True, timeout=60
    )
    if proc.returncode != 0:
        rep.fail(f"`run.py --list` failed (rc={proc.returncode}): {proc.stderr.strip()[:160]}")
        return
    script_targets = {line.strip() for line in proc.stdout.splitlines() if line.strip()}

    makefile = root / "Makefile"
    if not makefile.exists():
        rep.fail("Makefile is missing (expected as the `make` wrapper)")
        return
    text = makefile.read_text(encoding="utf-8")
    phony = re.search(r"^\.PHONY:(.*)$", text, re.M)
    make_targets = set(phony.group(1).split()) if phony else set()

    only_script = sorted(script_targets - make_targets)
    only_make = sorted(make_targets - script_targets)
    if only_script or only_make:
        if only_script:
            rep.fail(f"run.py targets with no make target: {', '.join(only_script)}")
        if only_make:
            rep.fail(f"make targets with no run.py target: {', '.join(only_make)}")
    else:
        rep.ok(f"both entry points expose the same {len(script_targets)} targets")

    # Every recipe must go through run.py. A make target that grows its own
    # implementation is the drift this check exists to catch.
    homemade = []
    current = None
    for line in text.splitlines():
        bare = line.split("##")[0].rstrip()
        match = re.match(r"^([a-z][a-z0-9-]*):\s*$", bare)
        if match:
            current = match.group(1)
            continue
        if current and line.startswith("\t"):
            if "run.py" not in line:
                homemade.append(f"{current}: {line.strip()[:60]}")
            current = None
    if homemade:
        for h in homemade:
            rep.fail(f"make target does not forward to run.py -> {h}")
    else:
        rep.ok("every make recipe forwards to run.py, so only one implementation exists")


# --------------------------------------------------------------------------- #
# 3. nothing points outside the folder                                          #
# --------------------------------------------------------------------------- #


def scannable_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(p in VENDOR_DIRS for p in parts[:-1]):
            continue
        if path.suffix in BINARY_SUFFIXES or path.name in UNSCANNED_NAMES:
            continue
        found.append(path)
    return sorted(found)


def relative_import_is_vendored(rel: Path) -> bool:
    """True when a parent hop is legitimate because the file is vendored."""
    parts = rel.parts
    return any(parts[: len(v)] == v for v in VENDORED_TS_ROOTS)


def check_escapes(rep: Report, root: Path, label: str) -> None:
    hits: list[str] = []
    scanned = 0
    for path in scannable_files(root):
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        vendored = relative_import_is_vendored(rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, what, tolerated_in_vendored in ESCAPE_TOKENS:
                if not re.search(pattern, line):
                    continue
                if tolerated_in_vendored and vendored:
                    continue
                hits.append(f"{rel}:{lineno}: {what} -> {line.strip()[:90]}")
    if hits:
        for h in hits:
            rep.fail(h)
    else:
        rep.ok(f"{label}: {scanned} files scanned, none points outside the folder")


# --------------------------------------------------------------------------- #
# 4. the IaC contract stands alone and is auditable                            #
# --------------------------------------------------------------------------- #


def check_contract(rep: Report) -> None:
    rep.heading("[4] the IaC contract is self-contained and tagged")
    spec = contract()

    tags = spec.get("tags") or {}
    want = {"Project": PROJECT_TAG, "UseCase": USE_CASE_NUMBER, "AutoDelete": "true"}
    wrong = {k: v for k, v in want.items() if tags.get(k) != v}
    if wrong:
        rep.fail(f"agentcore.json tags are wrong: expected {want}, got {tags}")
    else:
        rep.ok("project tags present: " + ", ".join(f"{k}={v}" for k, v in want.items()))

    loc = code_location(spec)
    target = (USE_CASE_DIR / loc).resolve()
    if Path(loc).is_absolute() or USE_CASE_DIR.resolve() not in target.parents:
        rep.fail(f"codeLocation {loc!r} does not resolve inside this folder")
    elif not target.is_dir():
        rep.fail(f"codeLocation {loc!r} does not exist")
    else:
        rep.ok(f"codeLocation {loc!r} resolves inside this folder")

    targets = json.loads((USE_CASE_DIR / "agentcore" / "aws-targets.json").read_text(encoding="utf-8"))
    if not targets or not targets[0].get("region"):
        rep.fail("aws-targets.json declares no region")
    else:
        rep.ok(f"deployment target: {targets[0]['region']} (target {targets[0].get('name')})")

    # Names have to be namespaced to this use case, because the UseCase tag is
    # what makes cleanup auditable and a shared name is what breaks it.
    spec_name = str(spec.get("name", ""))
    rt_name = str((spec.get("runtimes") or [{}])[0].get("name", ""))
    if spec_name != f"aiauc{USE_CASE_NUMBER}":
        rep.fail(f"project name {spec_name!r} should be 'aiauc{USE_CASE_NUMBER}'")
    elif rt_name != f"aia_uc{USE_CASE_NUMBER}":
        rep.fail(f"runtime name {rt_name!r} should be 'aia_uc{USE_CASE_NUMBER}'")
    else:
        rep.ok(f"names are namespaced to this use case: {spec_name} / {rt_name}")


# --------------------------------------------------------------------------- #
# 5. an actual copy, checked like the original                                  #
# --------------------------------------------------------------------------- #


def copy_folder(dest: Path) -> None:
    shutil.copytree(
        USE_CASE_DIR,
        dest,
        ignore=shutil.ignore_patterns(*sorted(VENDOR_DIRS)),
        symlinks=True,
    )


def check_real_copy(rep: Report) -> None:
    rep.heading("[5] the folder survives a real copy")
    with tempfile.TemporaryDirectory(prefix="aia-copy-") as tmp:
        dest = Path(tmp) / USE_CASE_DIR.name
        try:
            copy_folder(dest)
        except Exception as exc:  # noqa: BLE001
            rep.fail(f"copy failed: {exc.__class__.__name__}: {exc}")
            return
        rep.ok(f"copied to {dest}")

        before = {p.relative_to(USE_CASE_DIR).as_posix() for p in scannable_files(USE_CASE_DIR)}
        after = {p.relative_to(dest).as_posix() for p in scannable_files(dest)}
        if before == after:
            rep.ok(f"the copy carries all {len(after)} files, and nothing extra")
        else:
            for f in sorted(before - after):
                rep.fail(f"lost in the copy: {f}")
            for f in sorted(after - before):
                rep.fail(f"appeared only in the copy: {f}")

        check_escapes(rep, dest, "the copy")

        # The entry point has to answer with nothing but what is in the folder.
        env = {**os.environ, "AIA_IN_COPY": "1"}
        proc = subprocess.run(
            [sys.executable, "run.py", "help"], cwd=dest, capture_output=True, text=True,
            env=env, timeout=60,
        )
        if proc.returncode == 0 and "run.py" in proc.stdout:
            rep.ok("`run.py help` runs inside the copy")
        else:
            rep.fail(f"`run.py help` failed in the copy (rc={proc.returncode}): {proc.stderr.strip()[:200]}")

        # `make` is optional (Windows, slim images). When it is there, the shim
        # has to work too, so it is checked rather than assumed.
        if shutil.which("make") is None:
            rep.note("`make` is not on PATH here; the Makefile shim was not exercised")
        else:
            proc = subprocess.run(
                ["make", "help"], cwd=dest, capture_output=True, text=True, env=env, timeout=60
            )
            if proc.returncode == 0 and "run.py" in proc.stdout:
                rep.ok("`make help` runs inside the copy and forwards to run.py")
            else:
                rep.fail(f"`make help` failed in the copy (rc={proc.returncode}): {proc.stderr.strip()[:200]}")

        # And the copied folder must be able to re-assert its own independence,
        # which is the check you would run after copying it into your own repo.
        proc = subprocess.run(
            [sys.executable, "tests/copy_check.py", "--quiet"],
            cwd=dest,
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
        if proc.returncode == 0:
            rep.ok("the copy passes its own copy_check")
        else:
            rep.fail(f"the copy fails its own copy_check (rc={proc.returncode})")
            inner = [l.strip() for l in proc.stdout.splitlines() if l.strip().startswith("FAIL")]
            for line in inner[:5]:
                rep.fail(f"  inherited from the copy: {line}")
            if len(inner) > 5:
                rep.fail(f"  and {len(inner) - 5} more lines in the copy")


# --------------------------------------------------------------------------- #
# runner                                                                        #
# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="only print failures and the summary")
    ap.add_argument("--quick", action="store_true", help="skip the real-copy simulation (check 4)")
    args = ap.parse_args()

    nested = os.environ.get("AIA_IN_COPY") == "1"

    rep = Report(quiet=args.quiet)
    if not args.quiet:
        print(f"copy_check: {USE_CASE_DIR}")
        print(f"use case {USE_CASE_NUMBER} · nested run: {nested}")
    check_required(rep, USE_CASE_DIR)
    check_entry_points(rep, USE_CASE_DIR)
    rep.heading("[3] nothing points outside the folder")
    check_escapes(rep, USE_CASE_DIR, "the folder")
    check_contract(rep)
    if nested:
        rep.note("the real-copy simulation was skipped: this is already a copy")
    elif args.quick:
        rep.note("the real-copy simulation was skipped (--quick)")
    else:
        check_real_copy(rep)
    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
