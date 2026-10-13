#!/usr/bin/env bash
# new-usecase.sh: scaffold a new, self-contained use case skeleton.
#
# Why this exists: independent use cases each need their own copy of a baseline
# agent, an IaC stack and a smoke test. Copying that by hand seven times is how
# skeletons drift apart. This script authors the duplicate exactly once.
#
# Usage
#   ./shared/scripts/new-usecase.sh 08-your-idea --difficulty 5 --title "Your Idea"
#   ./shared/scripts/new-usecase.sh 08-your-idea --difficulty 5 --capabilities registry,runtime --dry-run
#
# The new use case is created under usecases/ unless --out is given. After
# scaffolding, `make test` fails on purpose until every declared capability has an
# implemented assertion, so a skeleton can never masquerade as a finished use case.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATES="$REPO_ROOT/shared/templates"
BASELINE="$TEMPLATES/baseline-agent"
MAP_FILE="$REPO_ROOT/docs/05-capability-map.yaml"
MODEL_ID_DEFAULT="us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SLUG=""
DIFFICULTY=""
TITLE=""
CAPABILITIES=""
OUT_DIR="$REPO_ROOT/usecases"
DRY_RUN=0

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --difficulty)   DIFFICULTY="${2:-}"; shift 2 ;;
    --title)        TITLE="${2:-}"; shift 2 ;;
    --capabilities) CAPABILITIES="${2:-}"; shift 2 ;;
    --out)          OUT_DIR="${2:-}"; shift 2 ;;
    --dry-run)      DRY_RUN=1; shift ;;
    -h|--help)      sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*)             die "unknown flag $1" ;;
    *)              [ -z "$SLUG" ] || die "unexpected argument $1"; SLUG="$1"; shift ;;
  esac
done

# ── validate ────────────────────────────────────────────────────────────────
[ -n "$SLUG" ]       || die "usage: new-usecase.sh <NN-slug> --difficulty <1-5> [--title ...] [--capabilities a,b]"
[ -n "$DIFFICULTY" ] || die "--difficulty is required (1 to 5)"
case "$SLUG" in
  [0-9][0-9]-[a-z0-9]*) ;;
  *) die "slug must look like 08-your-idea (two digits, dash, lowercase)" ;;
esac
case "$DIFFICULTY" in
  1|2|3|4|5) ;;
  *) die "--difficulty must be 1 to 5" ;;
esac

UC_NUM="${SLUG%%-*}"
UC_ID="uc${UC_NUM}"
[ -n "$TITLE" ] || TITLE="$(printf '%s' "${SLUG#*-}" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2); print}')"

TARGET="$OUT_DIR/$SLUG"
[ -e "$TARGET" ] && die "$TARGET already exists"

# ── resolve capabilities: explicit flag, else read the capability map ───────
if [ -z "$CAPABILITIES" ]; then
  [ -f "$MAP_FILE" ] || die "capability map not found at $MAP_FILE"
  set +e
  CAPABILITIES="$(python3 - "$MAP_FILE" "$UC_ID" <<'PY'
import sys
try:
    import yaml
except ModuleNotFoundError:
    sys.exit(3)
path, uc_id = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    spec = yaml.safe_load(fh)
for uc in spec.get("usecases", []) + spec.get("bonus", []):
    if uc["id"] == uc_id:
        print(",".join(uc.get("deep", [])))
        break
PY
)"
  rc=$?
  set -e
  if [ "$rc" -eq 3 ]; then
    die "cannot read the capability map: PyYAML is unavailable.
       fix: pip install pyyaml   (verify-coverage.py needs it too)
       or: pass the capabilities yourself, e.g. --capabilities registry,runtime"
  elif [ "$rc" -ne 0 ]; then
    die "could not read $MAP_FILE (python3 exit $rc)"
  fi
  if [ -n "$CAPABILITIES" ]; then
    printf 'using capabilities declared in the map for %s: %s\n' "$UC_ID" "$CAPABILITIES"
  else
    die "$UC_ID has no entry in $MAP_FILE; add one first, or pass --capabilities"
  fi
fi

# ── render the CAPABILITY_ASSERTIONS block ──────────────────────────────────
ASSERT_BLOCK=""
IFS=',' read -r -a CAP_ARRAY <<< "$CAPABILITIES"
for cap in "${CAP_ARRAY[@]}"; do
  cap_trimmed="$(printf '%s' "$cap" | tr -d '[:space:]')"
  [ -n "$cap_trimmed" ] || continue
  ASSERT_BLOCK+="    \"${cap_trimmed}\": ["$'\n'
  ASSERT_BLOCK+="        \"TODO: state what proves ${cap_trimmed} works in this use case\","$'\n'
  ASSERT_BLOCK+="    ],"$'\n'
done
[ -n "$ASSERT_BLOCK" ] || die "no usable capabilities given"

printf 'scaffolding %s\n' "$TARGET"
printf '  id            %s\n' "$UC_ID"
printf '  title         %s\n' "$TITLE"
printf '  difficulty    D%s\n' "$DIFFICULTY"
printf '  capabilities  %s\n' "$CAPABILITIES"

if [ "$DRY_RUN" -eq 1 ]; then
  printf '\n--dry-run: nothing written\n'
  exit 0
fi

# ── copy the baseline ───────────────────────────────────────────────────────
mkdir -p "$TARGET"/{src,tests,iac,diagrams,scripts}
cp "$BASELINE"/tests/*.py "$TARGET/tests/"
: > "$TARGET/iac/.gitkeep"

render() {  # render <template> <dest>
  sed -e "s|{{UC_ID}}|$UC_ID|g" \
      -e "s|{{UC_NUM}}|$UC_NUM|g" \
      -e "s|{{UC_SLUG}}|$SLUG|g" \
      -e "s|{{UC_TITLE}}|$TITLE|g" \
      -e "s|{{DIFFICULTY}}|$DIFFICULTY|g" \
      -e "s|{{MODEL_ID}}|$MODEL_ID_DEFAULT|g" \
      "$1" > "$2"
}

render "$BASELINE/src/main.py"    "$TARGET/src/main.py"
render "$BASELINE/pyproject.toml" "$TARGET/pyproject.toml"

# smoke.py carries a multi-line dictionary, so substitute the scalar
# placeholders first and then splice the capability block in with awk.
render "$BASELINE/tests/smoke.py" "$TARGET/tests/.smoke.tmp"
printf '%s' "$ASSERT_BLOCK" > "$TARGET/tests/.assert_block"
awk 'NR==FNR { blk = blk $0 ORS; next }
     /^\{\{CAPABILITY_ASSERTIONS\}\}$/ { printf "%s", blk; next }
     { print }' "$TARGET/tests/.assert_block" "$TARGET/tests/.smoke.tmp" > "$TARGET/tests/smoke.py"
rm -f "$TARGET/tests/.smoke.tmp" "$TARGET/tests/.assert_block"

# ── docs, Makefile, env ─────────────────────────────────────────────────────
sed -e "s|{{UC_ID}}|$UC_ID|g" \
    -e "s|{{UC_NUM}}|$UC_NUM|g" \
    -e "s|{{UC_TITLE}}|$TITLE|g" \
    -e "s|{{DIFFICULTY}}|$DIFFICULTY|g" \
    -e "s|0X|$UC_NUM|g" \
    "$TEMPLATES/usecase-doc.template.md" > "$TARGET/README.md"

if [ -f "$TEMPLATES/article.template.md" ]; then
  render "$TEMPLATES/article.template.md" "$TARGET/article.md"
fi

if [ -f "$TEMPLATES/usecase-Makefile.template" ]; then
  render "$TEMPLATES/usecase-Makefile.template" "$TARGET/Makefile"
fi

cat > "$TARGET/.env.example" <<EOF
# $UC_ID · $TITLE: placeholders only. Never commit real values.
AWS_REGION=us-east-1
MODEL_ID=$MODEL_ID_DEFAULT
# AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:<account>:runtime/<id>
EOF

cat <<EOF

done. next:

  1. implement the capability assertions in tests/smoke.py
     (it fails on purpose until each one is implemented)
  2. write the operations doc in README.md: twelve sections, every step needs
     command / expected output / how to verify / what to do if it fails
  3. add or update this block in docs/05-capability-map.yaml, then run:
       python3 shared/scripts/verify-coverage.py --usecase $UC_ID

  - id: $UC_ID
    dir: usecases/$SLUG
    title: $TITLE
    difficulty: $DIFFICULTY
    standalone: true
    knowledge_prereqs: []
    deep: [$(printf '%s' "$CAPABILITIES" | sed 's/,/, /g')]
    incidental: []
    assertions:
      - TODO
    cost_usd: 0
    minutes: 0
EOF
