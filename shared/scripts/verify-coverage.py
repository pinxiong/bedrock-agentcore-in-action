#!/usr/bin/env python3
"""verify-coverage.py

Reads docs/05-capability-map.yaml and enforces five classes of rules.

  [COVER]   every one of the 14 capabilities is `deep` in at least one use case
  [EVID]    a use case declaring `deep: [cap]` must carry, under
            usecases/<dir>/evidence/, a capture of the native command that
            proves it. There is no assertion script to grep any more
            (docs/09-article-spec.md §8 banned tests/smoke.py): the proof is the
            captured output of `agentcore ...` or `aws ...`, matched on evidence
            filenames and on the capability's own key strings.
  [COPY]    every use case folder stands alone when it is copied out. Enforced by
            reading the folder, never by executing anything inside it: nothing
            may point at a path outside the folder, the IaC contract must be
            self-contained and tagged, and the operational scripts the series
            banned (run.py, Makefile, tests/doctor.py, tests/smoke.py,
            tests/copy_check.py) must be absent. It exists because "copy any
            folder and it runs independently" was a promise in the README before
            it was a test.
  [INDEP]   (a) difficulty is declared, inside the scale bounds, and the sequence
                over the ladder is non-decreasing
            (b) every use case has its own agentcore/ directory and no cross-stack
                reference (ImportValue / remote_state / another use case's name)
            (c) the directory a use case deploys (codeLocation in
                agentcore/agentcore.json) never imports another use case
  [CMD]     every `agentcore ...` command, subcommand and flag written in a
            use case's `cli:` field exists in the installed CLI. This exists
            because the plan once carried commands that do not exist
            (`agentcore create --harness`, `agentcore add identity`). Probing
            uses the `Usage:` line, not the exit code: commander exits 0 even
            for an unknown command when `--help` is present, and falls back to
            printing the parent's help.

Exit code 0 = all checks pass, 1 = at least one FAIL.

Usage
  python3 shared/scripts/verify-coverage.py
  python3 shared/scripts/verify-coverage.py --usecase uc04
  python3 shared/scripts/verify-coverage.py --allow-missing-dirs   # during bootstrap
  python3 shared/scripts/verify-coverage.py --skip-cli             # no CLI on this machine
  python3 shared/scripts/verify-coverage.py --skip-copy            # do not inspect folders

Requires PyYAML:  pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.exit(
        "verify-coverage.py needs PyYAML.\n"
        "  pip install pyyaml\n"
        "  # or: uv pip install pyyaml"
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = "docs/05-capability-map.yaml"

CROSS_STACK_PATTERNS = [
    (r"\bImportValue\b", "CloudFormation ImportValue"),
    (r"\bimport_value\b", "CDK Fn.import_value"),
    (r"\bterraform_remote_state\b", "Terraform remote state"),
    (r"\bremote_state\b", "Terraform remote state"),
    (r"\bcdk\.Stack\.from_lookup\b", "CDK cross-stack lookup"),
]
IMPORT_PATTERNS = [
    r"^\s*from\s+usecases\b",
    r"^\s*import\s+usecases\b",
    r"^\s*from\s+\.\.\.",
]

# Vendored trees must never be scanned: a use case ships its own .venv for local
# development and its own node_modules for the generated CDK app, and the
# third-party code inside them is full of relative imports that look exactly
# like the thing I4 forbids.
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "cdk.out", ".cache"}
SKIP_SUFFIXES = {".png", ".svg", ".pdf", ".zip", ".lock", ".whl", ".so", ".pyc"}

# docs/09-article-spec.md §8: a use case folder ships no self-written
# operational scripts. The series teaches the agentcore CLI, so the reader never
# runs a wrapper, and a folder carrying one is a folder that cannot be copied
# out and understood on its own.
FORBIDDEN_IN_FOLDER = [
    "run.py",
    "Makefile",
    "tests/doctor.py",
    "tests/smoke.py",
    "tests/copy_check.py",
    "tests/resourcegroupstaggingapi_check.py",
]
REQUIRED_IN_FOLDER = [
    "README.md",
    "AGENTS.md",
    "agentcore/agentcore.json",
    "agentcore/aws-targets.json",
    "agentcore/.gitignore",
]
# A path that only resolves because the parent repository happens to be there.
ESCAPE_PATTERNS = [
    (r"(?<![\w.])\.\./", "a parent-directory hop"),
    (r"/Users/", "an absolute path from somebody's machine"),
    (r"shared/", "a repository-level shared tree"),
    (r"aia\.py", "the repository-level dispatcher"),
]
# A capture under evidence/ is terminal output, not an instruction: it routinely
# contains the machine's own paths, and scanning it would fail every use case
# that recorded a real run. The folder is still checked for what it ships.
EVIDENCE_DIR = "evidence"
# Trees that are not the use case's own writing and are never copied: the CLI's
# local state and logs, the CDK project it generates (whose TypeScript imports
# hop to a parent that never leaves the folder), and build output.
SCAN_SKIP_DIRS = SKIP_DIRS | {".cli", "dist", "cdk", ".pytest_cache", ".mypy_cache", ".idea"}

# Capability -> extra strings that count as proof of it. The default needles are
# derived from the capability id and name; these exist where the proof's filename
# would not carry the id itself, because a trace is what proves observability.
CAPABILITY_EVIDENCE_HINTS = {
    "runtime": ["endpoint", "invoke"],
    "observability": ["trace", "span", "cloudwatch", "otel"],
    "memory": ["memory record", "namespace"],
    "gateway": ["mcp", "target"],
    "identity": ["credential", "oauth", "jwt"],
    "code-interpreter": ["interpreter"],
    "browser": ["playwright", "session"],
    "web-search": ["websearch", "search"],
    "evaluations": ["evaluator", "evaluation"],
    "optimization": ["optimization", "optimize"],
    "payments": ["payment", "x402"],
    "policy": ["dogwood", "cedar", "denied"],
    "registry": ["registry"],
    "harness": ["harness"],
}
TEXT_SUFFIXES = {".txt", ".json", ".md", ".log", ".yaml", ".yml", ".env"}
MAX_EVIDENCE_BYTES = 2_000_000


def walk_files(root: Path, suffix: str | None = None) -> list[Path]:
    """Every file under root, minus vendor trees and binary artefacts."""
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        if suffix and path.suffix != suffix:
            continue
        found.append(path)
    return found


def other_use_case_tokens(other_dir: str) -> list[str]:
    """Strings that would prove one use case is wired to another one.

    Only distinctive tokens count. A bare directory name is not enough: the
    AgentCore config schema has a top level `payments` array, so matching the
    word "payments" would flag every project in this repository for the bonus
    use case. Numbered directory names and generated resource names are the
    only things that are unambiguous.
    """
    name = Path(other_dir).name
    tokens: list[str] = []
    match = re.match(r"^(\d{2})-", name)
    if not match:
        return tokens
    num = match.group(1)
    tokens += [name, f"aia_uc{num}", f"aiauc{num}"]
    return tokens


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.warns: list[str] = []
        self.passes: list[str] = []

    def fail(self, msg: str) -> None:
        self.fails.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    def ok(self, msg: str) -> None:
        self.passes.append(msg)

    def emit(self) -> int:
        for m in self.passes:
            print(f"  PASS  {m}")
        for m in self.warns:
            print(f"  WARN  {m}")
        for m in self.fails:
            print(f"  FAIL  {m}")
        print()
        print(
            f"{len(self.passes)} passed, {len(self.warns)} warned, "
            f"{len(self.fails)} failed"
        )
        return 1 if self.fails else 0


def load_map(root: Path) -> dict:
    path = root / MAP_FILE
    if not path.exists():
        sys.exit(f"capability map not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# [CMD] support: shell out to the installed CLI and cache its help text
# ---------------------------------------------------------------------------

CLI_TIMEOUT_S = 20
_HELP_CACHE: dict[tuple[str, ...], str | None] = {}


def cli_help(tokens: tuple[str, ...]) -> str | None:
    """Help text for `agentcore <tokens>`, or None when the CLI is not installed.

    Call with an empty tuple to probe for the binary itself.
    """
    if tokens in _HELP_CACHE:
        return _HELP_CACHE[tokens]
    try:
        proc = subprocess.run(
            ["agentcore", *tokens, "--help"],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
        )
        text: str | None = (proc.stdout or "") + (proc.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        text = None
    _HELP_CACHE[tokens] = text
    return text


def check_coverage(spec: dict, rep: Report) -> None:
    print("[COVER] every capability is deep-dived somewhere")
    declared_deep: set[str] = set()
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        declared_deep.update(uc.get("deep", []))

    missing = []
    for cap in spec["capabilities"]:
        cid = cap["id"]
        if cid in declared_deep:
            rep.ok(f"{cid} is deep-dived")
        else:
            missing.append(cid)
            rep.fail(f"{cid} is deep-dived nowhere")

    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        for cid in uc.get("deep", []):
            if cid not in {c["id"] for c in spec["capabilities"]} and cid not in {
                c["id"] for c in spec.get("cross_cutting", [])
            }:
                rep.fail(f"{uc['id']}: unknown capability id '{cid}' in deep list")
    if missing:
        print()
    print()


def capability_needles(cid: str, named: dict[str, dict]) -> list[str]:
    """Strings whose presence in an evidence capture counts as proof of `cid`.

    Deliberately loose rather than a schema: an evidence file is named after the
    command that produced it, so matching the capability id, its name and a few
    synonyms is what catches `10-traces-list.txt` proving observability.
    """
    entry = named.get(cid) or {}
    name = str(entry.get("name") or cid)
    raw = {
        cid,
        cid.replace("-", " "),
        cid.replace("-", "_"),
        cid.replace("-", ""),
        name.lower(),
        name.lower().replace(" ", "-"),
        name.lower().replace(" ", ""),
    }
    raw.update(CAPABILITY_EVIDENCE_HINTS.get(cid, []))
    return sorted({n for n in raw if len(n) >= 4})


def needle_hits(name: str, text: str, needles: list[str]) -> bool:
    """True when a needle matches the filename or the capture's contents."""
    flat = name.lower().replace("-", " ").replace("_", " ")
    lowered = text.lower()
    for needle in needles:
        spaced = needle.replace("-", " ").replace("_", " ")
        if spaced in flat:
            return True
        for form in {needle, spaced, needle.replace(" ", "-"), needle.replace(" ", "_")}:
            if form and form in lowered:
                return True
    return False


def evidence_files(evidence_dir: Path) -> list[Path]:
    return sorted(
        p for p in evidence_dir.rglob("*")
        if p.is_file() and p.suffix in TEXT_SUFFIXES and p.stat().st_size <= MAX_EVIDENCE_BYTES
    )


def covered_capabilities(evidence_dir: Path, needles_by_cap: dict[str, list[str]]) -> dict[str, str]:
    """capability id -> the evidence file that proves it.

    A filename is the stronger signal, so it is tried first over every file
    before any capture is opened: `11-memory-records.txt` proves memory, while
    the word "memory" inside a status dump proves only that memory exists.
    """
    files = evidence_files(evidence_dir)
    found: dict[str, str] = {}
    for path in files:
        for cid, needles in needles_by_cap.items():
            if cid in found:
                continue
            if needle_hits(path.name, "", needles):
                found[cid] = path.name
    for path in files:
        if len(found) == len(needles_by_cap):
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for cid, needles in needles_by_cap.items():
            if cid in found:
                continue
            if needle_hits(path.name, text, needles):
                found[cid] = path.name
    return found


def check_evidence(root: Path, spec: dict, only: str | None, allow_missing: bool, rep: Report) -> None:
    print("[EVID] every declared deep capability is proven by a capture under evidence/")
    named = {c["id"]: c for c in spec.get("capabilities", []) + spec.get("cross_cutting", [])}
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        if only and uc["id"] != only:
            continue
        deep = set(uc.get("deep", []))
        if not deep:
            continue
        needles_by_cap = {cid: capability_needles(cid, named) for cid in deep}

        uc_dir = root / uc["dir"]
        if not uc_dir.exists():
            msg = f"{uc['id']}: directory {uc['dir']} does not exist yet"
            rep.warn(msg + " (allowed during bootstrap)") if allow_missing else rep.fail(msg)
            continue

        evidence_dir = uc_dir / EVIDENCE_DIR
        if not evidence_dir.is_dir():
            msg = f"{uc['id']}: no {uc['dir']}/{EVIDENCE_DIR}/ directory, so nothing proves {', '.join(sorted(deep))}"
            rep.warn(msg + " (allowed during bootstrap)") if allow_missing else rep.fail(msg)
            continue

        found = covered_capabilities(evidence_dir, needles_by_cap)
        gap = sorted(set(needles_by_cap) - set(found))
        if gap:
            rep.fail(
                f"{uc['id']}: declared deep but no capture under {EVIDENCE_DIR}/ proves it: "
                f"{', '.join(gap)}. save the output of the native command that proves "
                f"each one, e.g. agentcore status | agentcore invoke | agentcore traces list"
            )
        else:
            detail = ", ".join(f"{cid} <- {found[cid]}" for cid in sorted(found))
            rep.ok(f"{uc['id']}: all {len(deep)} deep capabilities are proven ({detail})")
    print()


def check_independence(root: Path, spec: dict, only: str | None, allow_missing: bool, rep: Report) -> None:
    print("[INDEP] (a) difficulty ladder, (b) own iac stack, (c) own source tree")

    # (a) difficulty
    scale = spec["difficulty_scale"]
    ladder = [uc for uc in spec.get("usecases", [])]
    seq: list[tuple[str, int]] = []
    for uc in ladder:
        d = uc.get("difficulty")
        if not isinstance(d, int) or f"D{d}" not in scale:
            rep.fail(f"{uc['id']}: difficulty '{d}' is outside the declared scale")
            continue
        seq.append((uc["id"], d))
        bound = scale[f"D{d}"].get("minutes_max")
        if bound is not None and uc.get("minutes", 0) > bound:
            rep.fail(
                f"{uc['id']}: declared D{d} but minutes={uc.get('minutes')} exceeds "
                f"the D{d} bound of {bound}"
            )
    for (id_a, a), (id_b, b) in zip(seq, seq[1:]):
        if b < a:
            rep.fail(f"difficulty regresses from {id_a} (D{a}) to {id_b} (D{b})")
    if seq and all(a <= b for (_, a), (_, b) in zip(seq, seq[1:])):
        rep.ok(f"difficulty sequence is non-decreasing: {[d for _, d in seq]}")
    for uc in spec.get("bonus", []):
        if not uc.get("outside_ladder"):
            rep.fail(f"{uc['id']}: bonus entries must set outside_ladder: true")

    # (b) and (c)
    all_dirs = [uc["dir"] for uc in spec.get("usecases", []) + spec.get("bonus", [])]
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        if only and uc["id"] != only:
            continue
        uc_dir = root / uc["dir"]
        if not uc_dir.exists():
            msg = f"{uc['id']}: directory {uc['dir']} does not exist yet"
            rep.warn(msg + " (allowed during bootstrap)") if allow_missing else rep.fail(msg)
            continue

        iac = uc_dir / "agentcore"
        if not iac.exists():
            rep.fail(f"{uc['id']}: no agentcore/ directory (violates I3)")
        else:
            hits = []
            for f in walk_files(iac):
                text = f.read_text(encoding="utf-8", errors="ignore")
                for pattern, label in CROSS_STACK_PATTERNS:
                    if re.search(pattern, text):
                        hits.append(f"{f.name}: {label}")
                for other in all_dirs:
                    if other == uc["dir"]:
                        continue
                    for token in other_use_case_tokens(other):
                        if token in text:
                            hits.append(f"{f.name}: references {token}")
                            break
            if hits:
                rep.fail(f"{uc['id']}: cross-stack reference -> {'; '.join(hits)}")
            else:
                rep.ok(f"{uc['id']}: agentcore/ is self-contained")

        # I4 lives on the codeLocation directory, not on a hard-coded src/.
        # The official layout is app/<AgentName>/; a BYO project can point the
        # same field anywhere. Read it from the contract so both paths pass.
        contract = iac / "agentcore.json"
        code_location = None
        if contract.exists():
            try:
                project_spec = json.loads(contract.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                rep.fail(f"{uc['id']}: agentcore/agentcore.json is not valid JSON ({exc})")
                project_spec = {}
            runtimes = project_spec.get("runtimes") or []
            if runtimes:
                code_location = runtimes[0].get("codeLocation")
                if not code_location:
                    rep.fail(f"{uc['id']}: runtimes[0] declares no codeLocation")
            else:
                rep.warn(f"{uc['id']}: contract declares no runtime yet, so I4 has nothing to check")
        if code_location:
            src = uc_dir / code_location
            if not src.is_dir():
                rep.fail(f"{uc['id']}: codeLocation '{code_location}' does not exist (violates I4)")
            else:
                hits = []
                for f in walk_files(src, suffix=".py"):
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for pattern in IMPORT_PATTERNS:
                        if re.search(pattern, text, re.M):
                            hits.append(f"{f.name}: {pattern}")
                    for other in all_dirs:
                        if other == uc["dir"]:
                            continue
                        mod = Path(other).name.replace("-", "_")
                        if re.search(rf"^\s*(from|import)\s+{re.escape(mod)}\b", text, re.M):
                            hits.append(f"{f.name}: imports {other}")
                if hits:
                    rep.fail(f"{uc['id']}: cross-use-case import -> {'; '.join(hits)}")
                else:
                    rep.ok(f"{uc['id']}: {code_location} does not import another use case")
    print()


def check_commands(spec: dict, only: str | None, skip: bool, rep: Report) -> None:
    print("[CMD] every `agentcore ...` written in a cli: field exists in the installed CLI")

    if skip:
        rep.warn("skipped (--skip-cli)")
        print()
        return

    if cli_help(()) is None:
        rep.warn("`agentcore` not on PATH: skipped (install it, or pass --skip-cli)")
        print()
        return

    checked = 0
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        if only and uc["id"] != only:
            continue
        cli = uc.get("cli")
        if not cli:
            continue

        problems: list[str] = []
        for raw in re.split(r"&&|;|\n", cli):
            raw = raw.strip()
            if "agentcore" not in raw:
                continue
            tokens = raw.split("agentcore", 1)[1].split("#", 1)[0].split()
            if not tokens:
                continue

            cmd = tokens[0]
            sub = tokens[1] if len(tokens) > 1 and not tokens[1].startswith("-") else None
            scope = (cmd,) if sub is None else (cmd, sub)
            text = cli_help(scope)
            if text is None:
                break

            # A real command echoes its own path on the Usage line; an unknown one
            # prints the parent's help instead.
            want = "agentcore " + " ".join(scope)
            if not re.search(rf"^Usage:\s+{re.escape(want)}\b", text, re.M):
                problems.append(f"`agentcore {' '.join(scope)}` does not exist")
                continue

            for flag in (t for t in tokens if t.startswith("-")):
                if not re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", text):
                    problems.append(f"`agentcore {' '.join(scope)}` has no {flag}")

        if problems:
            for p in problems:
                rep.fail(f"{uc['id']}: {p}")
        else:
            rep.ok(f"{uc['id']}: every command in cli: exists ({cli})")
        checked += 1

    if not checked:
        rep.warn("no cli: fields to check")
    print()


def scannable_files(root: Path) -> list[Path]:
    """Text files under root that instruct the reader, minus vendor trees.

    evidence/ is excluded: it holds captured output, and a capture of a real run
    is full of paths that are not instructions to follow. So is the CLI's own
    state under agentcore/.cli and the CDK project it generates.
    """
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(p in SCAN_SKIP_DIRS or p == EVIDENCE_DIR for p in parts[:-1]):
            continue
        if path.suffix in SKIP_SUFFIXES or path.suffix == ".lock":
            continue
        found.append(path)
    return sorted(found)


def check_escapes(uc_dir: Path) -> list[str]:
    """Lines in the folder that only resolve because the repository is there."""
    hits: list[str] = []
    for path in scannable_files(uc_dir):
        rel = path.relative_to(uc_dir)
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in ESCAPE_PATTERNS:
                if re.search(pattern, line):
                    hits.append(f"{rel}:{lineno}: {label} -> {line.strip()[:90]}")
    return hits


def check_standalone_folder(root: Path, uc: dict, rep: Report) -> bool:
    """Read one use case folder and decide whether it stands alone.

    No subprocess, no import, nothing executed: the folder is inspected as data.
    """
    uc_dir = root / uc["dir"]
    num = uc["id"].replace("uc", "").replace("bonus-", "")
    ok = True

    banned = [f for f in FORBIDDEN_IN_FOLDER if (uc_dir / f).exists()]
    if banned:
        ok = False
        rep.fail(
            f"{uc['id']}: ships an operational script the series banned "
            f"(docs/09-article-spec.md §8): {', '.join(banned)}"
        )

    spec = {}
    contract = uc_dir / "agentcore" / "agentcore.json"
    if contract.exists():
        try:
            spec = json.loads(contract.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            spec = {}
    code_location = (spec.get("runtimes") or [{}])[0].get("codeLocation")
    if code_location:
        code_location = str(code_location).rstrip("/")

    required = list(REQUIRED_IN_FOLDER)
    if code_location:
        required += [f"{code_location}/main.py", f"{code_location}/pyproject.toml"]
    missing = [f for f in required if not (uc_dir / f).exists()]
    if missing:
        ok = False
        rep.fail(f"{uc['id']}: missing {', '.join(missing)}")

    hits = check_escapes(uc_dir)
    if hits:
        ok = False
        rep.fail(f"{uc['id']}: the folder points outside itself")
        for h in hits[:8]:
            rep.fail(f"  {h}")
        if len(hits) > 8:
            rep.fail(f"  and {len(hits) - 8} more line(s)")
    if ok:
        rep.ok(f"{uc['id']}: the folder stands alone ({len(scannable_files(uc_dir))} files read)")

    # Tags and the deployment target: they are what make cleanup auditable and
    # what stops a use case from deploying into another one's account.
    #
    # `agentcore remove all -y` empties the contract, tags included, which is the
    # documented end of a use case's run (docs/09-article-spec.md section 8). An
    # emptied contract is therefore a state to restore, not a violation.
    emptied = not spec.get("runtimes")
    tags = spec.get("tags") or {}
    want = {"Project": "agentcore-in-action", "UseCase": num, "AutoDelete": "true"}
    wrong = {k: v for k, v in want.items() if tags.get(k) != v}
    if wrong:
        if emptied:
            rep.warn(
                f"{uc['id']}: agentcore.json has been emptied by `agentcore remove all` "
                f"(expected {want}, got {tags}). restore it from git before deploying again"
            )
        else:
            ok = False
            rep.fail(f"{uc['id']}: agentcore.json tags are wrong: expected {want}, got {tags}")

    targets_file = uc_dir / "agentcore" / "aws-targets.json"
    if targets_file.exists():
        try:
            targets = json.loads(targets_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            targets = []
        if not targets or not targets[0].get("region"):
            if emptied:
                rep.warn(
                    f"{uc['id']}: aws-targets.json has been emptied by `agentcore remove all`. "
                    f"restore it from git before deploying again"
                )
            else:
                ok = False
                rep.fail(f"{uc['id']}: aws-targets.json declares no region")

    return ok


def check_copy(root: Path, spec: dict, only: str | None, allow_missing: bool, skip: bool, rep: Report) -> None:
    print("[COPY] every use case folder stands alone when it is copied out")

    if skip:
        rep.warn("skipped (--skip-copy)")
        print()
        return

    checked = 0
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        if only and uc["id"] != only:
            continue
        uc_dir = root / uc["dir"]
        if not uc_dir.exists():
            msg = f"{uc['id']}: directory {uc['dir']} does not exist yet"
            rep.warn(msg + " (allowed during bootstrap)") if allow_missing else rep.fail(msg)
            continue
        check_standalone_folder(root, uc, rep)
        checked += 1

    if not checked:
        rep.warn("no use case folder to inspect yet")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this repo)")
    ap.add_argument("--usecase", help="check a single use case, e.g. uc04")
    ap.add_argument(
        "--allow-missing-dirs",
        action="store_true",
        help="treat not-yet-implemented use case directories as warnings, not failures",
    )
    ap.add_argument(
        "--skip-cli",
        action="store_true",
        help="skip the [CMD] check (for machines without the agentcore CLI)",
    )
    ap.add_argument(
        "--skip-copy",
        action="store_true",
        help="skip the [COPY] check (it reads every use case folder in full)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    spec = load_map(root)
    print(f"verifying {root / MAP_FILE}")
    print(f"structure: {spec['meta'].get('structure')}")
    print()

    rep = Report()
    if not args.usecase:
        check_coverage(spec, rep)
    check_evidence(root, spec, args.usecase, args.allow_missing_dirs, rep)
    check_copy(root, spec, args.usecase, args.allow_missing_dirs, args.skip_copy, rep)
    check_independence(root, spec, args.usecase, args.allow_missing_dirs, rep)
    check_commands(spec, args.usecase, args.skip_cli, rep)
    return rep.emit()


if __name__ == "__main__":
    raise SystemExit(main())
