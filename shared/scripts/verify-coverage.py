#!/usr/bin/env python3
"""verify-coverage.py

Reads docs/05-capability-map.yaml and enforces three classes of rules.

  [COVER]   every one of the 14 capabilities is `deep` in at least one use case
  [EVID]    a use case declaring `deep: [cap]` must assert that capability in
            usecases/<dir>/tests/smoke.py via a CAPABILITY_ASSERTIONS dict
  [INDEP]   (a) difficulty is declared, inside the scale bounds, and the sequence
                over the ladder is non-decreasing
            (b) every use case has its own agentcore/ directory and no cross-stack
                reference (ImportValue / remote_state / another use case's name)
            (c) the directory a use case deploys (codeLocation in
                agentcore/agentcore.json) never imports another use case

Exit code 0 = all checks pass, 1 = at least one FAIL.

Usage
  python3 shared/scripts/verify-coverage.py
  python3 shared/scripts/verify-coverage.py --usecase uc04
  python3 shared/scripts/verify-coverage.py --allow-missing-dirs   # during bootstrap

Requires PyYAML:  pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import re
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


def smoke_assertions(root: Path, uc: dict) -> tuple[set[str], str | None]:
    """Return the capability ids asserted in smoke.py, or an error string."""
    path = root / uc["dir"] / "tests" / "smoke.py"
    if not path.exists():
        return set(), f"missing {path.relative_to(root)}"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"CAPABILITY_ASSERTIONS\s*[:=][^=]*?=\s*\{", text)
    if not match:
        # tolerate a bare annotation without initialiser
        if "CAPABILITY_ASSERTIONS" not in text:
            return set(), (
                f"{path.relative_to(root)} has no CAPABILITY_ASSERTIONS dict"
            )
        return set(), None
    # collect the top-level keys of the dict literal
    depth = 0
    body_start = match.end() - 1
    for idx in range(body_start, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                body = text[body_start + 1 : idx]
                break
    else:
        return set(), f"{path.relative_to(root)}: unbalanced CAPABILITY_ASSERTIONS dict"
    keys = set(re.findall(r'^\s{0,8}["\']([a-z0-9\-]+)["\']\s*:', body, re.M))
    return keys, None


def check_evidence(root: Path, spec: dict, only: str | None, allow_missing: bool, rep: Report) -> None:
    print("[EVID] every declared deep capability is asserted in smoke.py")
    for uc in spec.get("usecases", []) + spec.get("bonus", []):
        if only and uc["id"] != only:
            continue
        deep = set(uc.get("deep", []))
        asserted, err = smoke_assertions(root, uc)
        if err:
            if allow_missing:
                rep.warn(f"{uc['id']}: {err} (allowed during bootstrap)")
            else:
                rep.fail(f"{uc['id']}: {err}")
            continue
        gap = sorted(deep - asserted)
        if gap:
            rep.fail(
                f"{uc['id']}: declared deep but not asserted in smoke.py: {', '.join(gap)}"
            )
        else:
            rep.ok(f"{uc['id']}: all {len(deep)} deep capabilities are asserted")
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this repo)")
    ap.add_argument("--usecase", help="check a single use case, e.g. uc04")
    ap.add_argument(
        "--allow-missing-dirs",
        action="store_true",
        help="treat not-yet-implemented use case directories as warnings, not failures",
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
    check_independence(root, spec, args.usecase, args.allow_missing_dirs, rep)
    return rep.emit()


if __name__ == "__main__":
    raise SystemExit(main())
