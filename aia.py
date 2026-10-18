#!/usr/bin/env python3
"""aia.py: the single dispatcher for the AgentCore in Action series.

One file, standard library only (PyYAML optional, needed by `list`, `new` and
`verify`). Runs identically on macOS, Linux and Windows: no Make, no bash, no
WSL. Every command takes ONE use case number on purpose -- nothing here deploys
more than one use case at a time.

Every use case is deployed and torn down with the AgentCore CLI itself: `up`
is `agentcore deploy`, `status` is `agentcore status`, `down` is
`agentcore remove all -y` followed by the reconciling `agentcore deploy`.
Nothing here wraps those commands in a script of our own, because the series
teaches the CLI, not a wrapper (docs/09-article-spec.md section 8).

Usage:
  python aia.py doctor [--usecase NN]     environment self-check, reports only
  python aia.py up NN                     deploy exactly one use case
  python aia.py down NN                   destroy exactly one use case
  python aia.py status NN                 what is deployed for that use case
  python aia.py check NN                  does that use case's folder stand alone?
  python aia.py verify-all                coverage + independence, whole repo
  python aia.py list                      the difficulty ladder, from the map
  python aia.py cost [NN]                 tagged resources for one or all use cases
  python aia.py new 08-your-idea --difficulty 5 [--title T] [--capabilities a,b]
                                          scaffold a new self-contained use case

There is no `test` target. A capability is proven by the captured output of a
native command under usecases/NN-slug/evidence/, not by an assertion script,
and verify-coverage.py is what checks that the capture exists.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
REGION = "us-east-1"
PROJECT_TAG = "agentcore-in-action"
# Anthropic and OpenAI models are refused from some countries and territories.
# DeepSeek answers from anywhere, so it is the series default.
DEFAULT_MODEL_ID = "deepseek.v3.2"
MAP_FILE = REPO_ROOT / "docs" / "05-capability-map.yaml"
TEMPLATES = REPO_ROOT / "shared" / "templates"
BASELINE = TEMPLATES / "baseline-agent"

# --------------------------------------------------------------------------- #
# small helpers                                                               #
# --------------------------------------------------------------------------- #


class Report:
    """Shared PASS/WARN/FAIL printer for doctor and the command wrappers."""

    def __init__(self) -> None:
        self.fails = 0
        self.warns = 0

    def ok(self, msg: str) -> None:
        print(f"  PASS  {msg}")

    def warn(self, msg: str) -> None:
        self.warns += 1
        print(f"  WARN  {msg}")

    def fail(self, msg: str) -> None:
        self.fails += 1
        print(f"  FAIL  {msg}")

    def finish(self) -> int:
        print()
        if self.fails == 0:
            print("all checks passed")
            return 0
        print(f"{self.fails} check(s) failed")
        return 1


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command cross-platform (no shell)."""
    # flush=True: without it the child's output overtakes this line whenever
    # stdout is a pipe, and the log reads as if the command ran after its output.
    print(f"  $ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=cwd, check=check)


def capture(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, ""
    return p.returncode, (p.stdout or "").strip()


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def die(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_map() -> dict:
    try:
        import yaml  # noqa: PLC0415
    except ModuleNotFoundError:
        die(
            "PyYAML is required to read docs/05-capability-map.yaml.\n"
            "       fix: pip install pyyaml   (or: uv pip install pyyaml)"
        )
    if not MAP_FILE.exists():
        die(f"capability map not found at {MAP_FILE}")
    import yaml  # noqa: PLC0415

    with MAP_FILE.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def all_usecases(spec: dict) -> list[dict]:
    return spec.get("usecases", []) + spec.get("bonus", [])


def find_uc_dir(num: str) -> Path:
    """Resolve '05' to usecases/05-research-agent; also accepts a slug suffix."""
    for base in (REPO_ROOT / "usecases", REPO_ROOT / "bonus"):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            if d.name.startswith(f"{num}-") or d.name == num or d.name.endswith(f"-{num}"):
                return d
    die(
        f"no use case directory matches '{num}' under usecases/ or bonus/ "
        "(not scaffolded yet? create it with: python aia.py new <NN-slug> --difficulty N)"
    )


def uc_number(uc_dir: Path) -> str:
    m = re.match(r"^(\d+)-", uc_dir.name)
    if m:
        return m.group(1)
    # bonus dirs: key off the declared id in the capability map
    spec = load_map()
    for uc in all_usecases(spec):
        if uc.get("dir", "").endswith(uc_dir.name):
            return uc["id"].replace("uc", "").replace("bonus-", "")
    die(f"cannot determine the use case number for {uc_dir}")


def agentcore_project(uc_dir: Path) -> Path | None:
    """Return the CLI project spec (agentcore/agentcore.json), or None.

    Two facts the wrappers below depend on:

      * the spec lives in an agentcore/ directory next to the project root, so
        the path to test is uc_dir/agentcore/agentcore.json, not uc_dir/agentcore.json;
      * the deployment region comes from agentcore/aws-targets.json, so the CLI
        takes no --region flag. Commands run from uc_dir, not from uc_dir/agentcore.
    """
    spec = uc_dir / "agentcore" / "agentcore.json"
    return spec if spec.exists() else None


# --------------------------------------------------------------------------- #
# aia doctor  (was bootstrap.sh)                                              #
# --------------------------------------------------------------------------- #


def cmd_doctor(args: argparse.Namespace) -> int:
    rep = Report()
    usecase = args.usecase
    print("AgentCore in Action: environment check")
    print()

    print("toolchain")
    rc, out = capture(["aws", "--version"])
    if rc == 0:
        rep.ok(f"aws cli {out.split()[0]}")
    else:
        rep.fail("aws cli not found            fix: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")

    rc, out = capture(["node", "-v"])
    if rc == 0:
        major = int(out.lstrip("v").split(".")[0])
        if major >= 20:
            rep.ok(f"node {out}")
        else:
            rep.fail(f"node {out} is too old   fix: the AgentCore CLI needs Node.js 20 or newer")
    else:
        rep.fail("node not found               fix: install Node.js 20 or newer")

    py = ".".join(str(v) for v in sys.version_info[:3])
    m = re.match(r"^3\.(\d+)\.", py)
    minor = int(m.group(1)) if m else 0
    if 10 <= minor <= 13:
        rep.ok(f"python {py} (inside the CodeZip 3.10 to 3.13 range)")
    elif minor < 10:
        rep.fail(f"python {py} is too old   fix: CodeZip needs 3.10 to 3.13")
    else:
        rep.warn(f"python {py} is outside the CodeZip 3.10 to 3.13 range; a Container build may be required")

    try:
        import yaml  # noqa: F401,PLC0415

        rep.ok("pyyaml available (needed by aia list/new and verify-coverage.py)")
    except ModuleNotFoundError:
        rep.fail("pyyaml not installed         fix: pip install pyyaml")

    if have("docker"):
        rep.warn("docker present, but the series uses the CodeZip path and does not need it")

    print()
    print("agentcore cli")
    rc, out = capture(["agentcore", "--version"])
    if rc == 0 and out:
        rep.ok(f"agentcore {out.splitlines()[0]}")
    elif rc != 127 and out:
        rep.fail("agentcore exists but --version fails")
        rep.fail("  most likely cause: the old Python package shadows the npm CLI")
        rep.fail("  fix: pip uninstall bedrock-agentcore-starter-toolkit")
        rep.fail("       then confirm 'agentcore' resolves to the npm install")
    else:
        rep.fail("agentcore not found          fix: npm install -g @aws/agentcore")

    pip = [sys.executable, "-m", "pip"]
    rc, _ = capture([*pip, "show", "bedrock-agentcore-starter-toolkit"])
    if rc == 0:
        rep.fail("python package bedrock-agentcore-starter-toolkit is installed and will shadow the npm CLI")
        rep.fail("  fix: pip uninstall bedrock-agentcore-starter-toolkit")

    print()
    print("aws environment")
    rc, account = capture(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"])
    if rc == 0 and account and account != "None":
        rep.ok(f"credentials work, account {account}")
    else:
        rep.fail("aws sts get-caller-identity failed   fix: check AWS_PROFILE and credentials")

    rc, region = capture(["aws", "configure", "get", "region"])
    if rc == 0 and region == REGION:
        rep.ok(f"region is {REGION}")
    else:
        rep.warn(f"region is '{region or 'unset'}', the series targets {REGION}")
        rep.warn("  why it matters: Registry is available in only 5 regions and Web Search needs us-east-1")

    if account and account != "None":
        rc, found = capture(
            [
                "aws", "bedrock", "list-foundation-models", "--region", REGION,
                "--query", f"modelSummaries[?modelId=='{args.model}'].modelId | [0]",
                "--output", "text",
            ]
        )
        if rc == 0 and found and found != "None":
            rep.ok(f"model {args.model} is available")
        else:
            rep.warn(f"model {args.model} not listed in {REGION}")
            rep.warn("  fix: check model access, or pass --model with a model your account can call")

    if usecase:
        print()
        print(f"use case {usecase} extra requirements")
        extras = {
            "03": ["cdk cli not found is fine; it is only needed to read generated templates"],
            "05": ["Web Search requires us-east-1; confirm the region check above"],
            "07": [
                "Registry uses the agent-registry namespace, not bedrock-agentcore",
                "policy to attach: AgentRegistryFullAccess",
            ],
            "08": [
                "Payments needs a Coinbase CDP or Stripe (Privy) wallet account",
                "fall back to sandbox/testnet if you do not have one",
            ],
        }
        for msg in extras.get(usecase, []):
            rep.warn(msg)

    return rep.finish()


# --------------------------------------------------------------------------- #
# aia up / down / test / status / verify                                      #
# --------------------------------------------------------------------------- #


def cmd_up(args: argparse.Namespace) -> int:
    uc_dir = find_uc_dir(args.usecase)
    num = uc_number(uc_dir)
    print(f">> deploying use case {num}; this must work standalone")
    if not agentcore_project(uc_dir):
        die(f"{uc_dir} has no agentcore/agentcore.json; nothing to deploy")
    # No --region here: the CLI reads the target region from agentcore/aws-targets.json.
    # -y / --target default keeps it non-interactive, so the same command works in CI.
    run(["agentcore", "deploy", "-y", "--target", "default"], cwd=uc_dir)
    return cmd_status(args)


def cmd_down(args: argparse.Namespace) -> int:
    uc_dir = find_uc_dir(args.usecase)
    num = uc_number(uc_dir)
    print(f">> destroying use case {num} only")
    if not agentcore_project(uc_dir):
        print(f"  nothing agentcore-managed in {uc_dir} (no agentcore/agentcore.json)")
        return 0
    # `remove all -y` empties the local spec, then `deploy` reconciles the stack
    # down. -y is not optional: without it the CLI asks for confirmation and
    # aborts with "requires an interactive terminal" in any non-interactive
    # shell, which is every CI run and every captured teardown.
    # It rewrites agentcore/agentcore.json, so restore it from git afterwards if
    # you intend to deploy the use case again.
    run(["agentcore", "remove", "all", "-y"], cwd=uc_dir, check=False)
    run(["agentcore", "deploy", "-y", "--target", "default"], cwd=uc_dir, check=False)
    print(">> now check the cleanup list in the use case README (Cleanup section) by hand")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    uc_dir = find_uc_dir(args.usecase)
    if agentcore_project(uc_dir):
        run(["agentcore", "status"], cwd=uc_dir, check=False)
    else:
        print(f"  nothing agentcore-managed in {uc_dir} (no agentcore/agentcore.json)")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Does this use case's folder stand alone if it were copied out?

    The check lives in verify-coverage.py ([COPY], [INDEP], [EVID]) and reads the
    folder as data. Re-implementing it here would create a second source of
    truth for what "standalone" means.
    """
    uc_dir = find_uc_dir(args.usecase)
    return run(
        [sys.executable, "shared/scripts/verify-coverage.py", "--usecase", f"uc{uc_number(uc_dir)}"],
        cwd=REPO_ROOT,
        check=False,
    ).returncode


def cmd_verify_all(_args: argparse.Namespace) -> int:
    run([sys.executable, "shared/scripts/verify-coverage.py", "--allow-missing-dirs"], cwd=REPO_ROOT)
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    spec = load_map()
    print(f"  {'id':<16}{'diff':<6}{'time':>8}  {'cost':>5}  dir")
    for uc in all_usecases(spec):
        print(
            f"  {uc['id']:<16}D{uc['difficulty']:<5}{uc['minutes']:>6} min"
            f"  ${uc['cost_usd']:>4}  {uc['dir']}"
        )
    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    filters = [
        "--tag-filters", f"Key=Project,Values={PROJECT_TAG}",
        "--query", "ResourceTagMappingList[].ResourceARN",
        "--output", "text",
    ]
    if args.usecase:
        filters = [
            "--tag-filters", f"Key=Project,Values={PROJECT_TAG}", f"Key=UseCase,Values={args.usecase}",
            "--query", "ResourceTagMappingList[].ResourceARN",
            "--output", "text",
        ]
    cmd = ["aws", "resourcegroupstaggingapi", "get-resources", "--region", REGION, *filters]
    rc, out = capture(cmd)
    if rc != 0:
        die("resourcegroupstaggingapi get-resources failed; check credentials and region")
    arns = sorted(set(out.split()))
    label = f"use case {args.usecase}" if args.usecase else "all use cases"
    print(f">> {len(arns)} tagged resource(s) for {label}")
    for arn in arns:
        print(f"  {arn}")
    print(">> for the money itself, check Cost Explorer grouped by tag Project")
    return 0


# --------------------------------------------------------------------------- #
# aia new  (was new-usecase.sh)                                               #
# --------------------------------------------------------------------------- #


def render(text: str, subs: dict[str, str]) -> str:
    for key, value in subs.items():
        text = text.replace(key, value)
    return text


def detect_account() -> str:
    """Account id for agentcore/aws-targets.json; the schema wants exactly 12 digits."""
    try:
        out = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            capture_output=True, text=True, timeout=30,
        )
        account = out.stdout.strip()
        if re.fullmatch(r"\d{12}", account):
            return account
    except Exception:  # noqa: BLE001 - any failure just means "fill it in yourself"
        pass
    print("  WARN  could not read the account id; aws-targets.json holds 000000000000, edit it")
    return "000000000000"


def cmd_new(args: argparse.Namespace) -> int:
    slug, difficulty = args.slug, args.difficulty
    if not re.fullmatch(r"\d{2}-[a-z0-9][a-z0-9-]*", slug):
        die("slug must look like 08-your-idea (two digits, dash, lowercase)")
    if difficulty not in {"1", "2", "3", "4", "5"}:
        die("--difficulty must be 1 to 5")

    uc_num = slug.split("-")[0]
    uc_id = f"uc{uc_num}"
    title = args.title or " ".join(w.capitalize() for w in slug.split("-")[1:])
    out_dir = Path(args.out) if args.out else REPO_ROOT / "usecases"
    target = out_dir / slug
    if target.exists():
        die(f"{target} already exists")

    # capabilities: explicit flag wins, otherwise read the map
    capabilities = [c.strip() for c in args.capabilities.split(",") if c.strip()] if args.capabilities else None
    if capabilities is None:
        spec = load_map()
        for uc in all_usecases(spec):
            if uc["id"] == uc_id:
                capabilities = list(uc.get("deep", []))
                break
        if not capabilities:
            die(f"{uc_id} has no entry in {MAP_FILE}; add one first, or pass --capabilities")
        print(f"using capabilities declared in the map for {uc_id}: {','.join(capabilities)}")
    if not capabilities:
        die("no usable capabilities given")

    print(f"scaffolding {target}")
    print(f"  id            {uc_id}")
    print(f"  title         {title}")
    print(f"  difficulty    D{difficulty}")
    print(f"  capabilities  {','.join(capabilities)}")
    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    subs = {
        "{{UC_ID}}": uc_id,
        "{{UC_NUM}}": uc_num,
        "{{UC_SLUG}}": slug,
        "{{UC_TITLE}}": title,
        "{{DIFFICULTY}}": difficulty,
        "{{MODEL_ID}}": args.model,
        "{{AGENT_NAME}}": f"aia_{uc_id}",
        "{{PROJECT_NAME}}": f"aia{uc_id}",
        "{{AWS_ACCOUNT_ID}}": detect_account(),
    }
    agent_dir = f"app/{subs['{{AGENT_NAME}}']}"
    # evidence/ is where the captures of the native commands go; it is part of
    # the contract, so it is created even while it is still empty.
    for sub in (agent_dir, f"{agent_dir}/model", "tests", "agentcore", "evidence", "raw"):
        (target / sub).mkdir(parents=True, exist_ok=True)

    # Agent code first. The agent code sits in app/<AgentName>/, which is the
    # layout `agentcore create` itself produces and the directory that
    # `codeLocation` points at. The template keeps the literal {{AGENT_NAME}}
    # in the path; only the rendered copy carries the real name.
    for rel in ("main.py", "model/__init__.py", "model/load.py", "model/sanitize.py",
                "pyproject.toml"):
        src = BASELINE / "app" / "{{AGENT_NAME}}" / rel
        (target / agent_dir / rel).write_text(render(src.read_text(encoding="utf-8"), subs), encoding="utf-8")

    # IaC source of truth: the contract, the targets, and the gitignore the CLI
    # writes next to them. The gitignore is not optional: without it a use case
    # would commit agentcore/.env.local and the CLI's local state.
    for rel in ("agentcore/agentcore.json", "agentcore/aws-targets.json", "agentcore/.gitignore"):
        src = BASELINE / rel
        (target / rel).write_text(render(src.read_text(encoding="utf-8"), subs), encoding="utf-8")

    # tests/ carries only the agent's own unit tests (pytest-style, offline). The
    # series ships no operational scripts: no run.py, no Makefile, no smoke or
    # copy_check (docs/09-article-spec.md section 8). What proves a capability is
    # the captured output of a native command under evidence/.
    for src in sorted((BASELINE / "tests").glob("*.py")):
        (target / "tests" / src.name).write_text(render(src.read_text(encoding="utf-8"), subs), encoding="utf-8")

    (target / "AGENTS.md").write_text(
        render((BASELINE / "AGENTS.md").read_text(encoding="utf-8"), subs), encoding="utf-8"
    )

    doc_tpl = TEMPLATES / "usecase-doc.template.md"
    doc = render(doc_tpl.read_text(encoding="utf-8"), subs).replace("0X", uc_num)
    (target / "README.md").write_text(doc, encoding="utf-8")

    article_tpl = TEMPLATES / "article.template.md"
    if article_tpl.exists():
        (target / "article.md").write_text(render(article_tpl.read_text(encoding="utf-8"), subs), encoding="utf-8")

    (target / ".env.example").write_text(
        f"# {uc_id} - {title}: placeholders only. Never commit real values.\n"
        f"AWS_REGION={REGION}\n"
        f"MODEL_ID={args.model}\n"
        "# AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:<account>:runtime/<id>\n",
        encoding="utf-8",
    )

    # raw/: teaching-only boto3 sidecar. The official samples keep two routes apart
    # on purpose (CLI in getting-started, boto3 in 01-features). This series can ship
    # both in one use case: the CLI route stays deployable, the API route stays visible.
    # Nothing here is imported or packaged, so the folder still stands alone without it.
    (target / "raw" / "README.md").write_text(
        f"""# raw/ · boto3 sidecar ({uc_id})

Not part of the deployment. Nothing here is imported by `app/{subs['{{AGENT_NAME}}']}/`
and nothing here is packaged by `agentcore deploy`. It exists so a reader can see
what the CLI did for them.

| Script | Client | What it shows |
|---|---|---|
| `control_plane.py` | `bedrock-agentcore-control` | list and read back the resources `agentcore` just created |
| `data_plane.py` | `bedrock-agentcore` | call `invoke_agent_runtime` directly and print the raw SSE stream |

Both scripts are optional. If you do not write them, delete this directory:
the independence check only requires what the use case needs in order to run.
""",
        encoding="utf-8",
    )

    caps = ", ".join(capabilities)
    print(
        f"""
done. next:

  1. build the app environment, which also writes the lockfile that makes the
     folder reproducible:
       cd usecases/{slug} && uv sync
  2. deploy it:
       cd usecases/{slug} && agentcore deploy -y --target default
     agentcore/agentcore.json is the source of truth; the CDK app under
     agentcore/cdk/ is generated by the CLI. If agentcore/cdk/ is missing,
     run `agentcore create` once in a scratch directory and copy it in.
  3. prove every capability in [{caps}] with a native command and save the
     capture under evidence/, e.g.
       agentcore status            -> evidence/NN-status.txt
       agentcore invoke --prompt   -> evidence/NN-invoke.txt
       agentcore traces list       -> evidence/NN-traces.txt
  4. tear it down (remove all empties the spec, deploy reconciles the stack
     down; restore agentcore/agentcore.json from git before deploying again):
       agentcore remove all -y && agentcore deploy -y --target default
  5. write the operations doc in README.md: every step needs
     command / expected output / how to verify / what to do if it fails
  6. add or update this block in docs/05-capability-map.yaml, then run:
       python aia.py check {uc_num}

  - id: {uc_id}
    dir: usecases/{slug}
    title: {title}
    difficulty: {difficulty}
    official:
      group: <one of the eight groups in docs/08-official-alignment.md>
      category: <conversational-agents | workflow-automation-agents | coding-assistants>
      vertical: <business vertical, e.g. Retail / E-commerce>
      samples:
        - <NN-layer/NN-group/NN-sample/ in awslabs/agentcore-samples>
    standalone: true
    knowledge_prereqs: []
    cli: <the agentcore commands this use case needs; verify-coverage.py checks they exist>
    deep: [{caps}]
    incidental: []
    assertions:
      - TODO
    cost_usd: 0
    minutes: 0
"""
    )
    return 0


# --------------------------------------------------------------------------- #
# entry point                                                                 #
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aia",
        description="AgentCore in Action dispatcher. One use case per command, by design.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="environment self-check, installs nothing")
    p.add_argument("--usecase", help="also print that use case's extra requirements")
    p.add_argument("--model", default=DEFAULT_MODEL_ID)
    p.set_defaults(func=cmd_doctor)

    for name, fn, help_txt in [
        ("up", cmd_up, "deploy exactly one use case"),
        ("down", cmd_down, "destroy exactly one use case"),
        ("check", cmd_check, "does that use case's folder stand alone if copied out?"),
        ("status", cmd_status, "what is deployed for one use case"),
    ]:
        p = sub.add_parser(name, help=help_txt)
        p.add_argument("usecase", help="use case number, e.g. 05")
        p.set_defaults(func=fn)

    p = sub.add_parser("verify-all", help="coverage + independence for the whole repo")
    p.set_defaults(func=cmd_verify_all)

    p = sub.add_parser("list", help="difficulty ladder from the capability map")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("cost", help="tagged resources for one or all use cases")
    p.add_argument("usecase", nargs="?", help="use case number, e.g. 05")
    p.set_defaults(func=cmd_cost)

    p = sub.add_parser("new", help="scaffold a new self-contained use case")
    p.add_argument("slug", help="08-your-idea")
    p.add_argument("--difficulty", required=True, help="1 to 5")
    p.add_argument("--title", help="defaults to the title-cased slug")
    p.add_argument("--capabilities", help="comma-separated; defaults to the map's deep list")
    p.add_argument("--out", help="target parent directory, defaults to usecases/")
    p.add_argument("--model", default=DEFAULT_MODEL_ID)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_new)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
