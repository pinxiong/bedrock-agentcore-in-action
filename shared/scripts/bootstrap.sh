#!/usr/bin/env bash
# bootstrap.sh: environment self-check for the whole series.
#
# Every check prints PASS / WARN / FAIL with the exact fix. Nothing is installed
# and nothing is changed; this script only reports.
#
#   ./shared/scripts/bootstrap.sh
#   ./shared/scripts/bootstrap.sh --usecase 05     # only that use case's extra requirements
#
# Exit code 0 means no FAIL. WARN does not block.

set -uo pipefail

REGION_EXPECTED="us-east-1"
MODEL_ID="${MODEL_ID:-us.anthropic.claude-sonnet-4-5-20250929-v1:0}"
USECASE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --usecase) USECASE="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument $1" >&2; exit 1 ;;
  esac
done

FAILS=0
pass() { printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAILS=$((FAILS + 1)); }

have() { command -v "$1" >/dev/null 2>&1; }

echo "AgentCore in Action: environment check"
echo

# ── toolchain ───────────────────────────────────────────────────────────────
echo "toolchain"

if have aws; then
  pass "aws cli $(aws --version 2>&1 | awk '{print $1}')"
else
  fail "aws cli not found            fix: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

if have node; then
  node_major="$(node -v | sed 's/^v//' | cut -d. -f1)"
  if [ "${node_major:-0}" -ge 20 ]; then
    pass "node $(node -v)"
  else
    fail "node $(node -v) is too old   fix: AgentCore CLI needs Node.js 20 or newer"
  fi
else
  fail "node not found               fix: install Node.js 20 or newer"
fi

if have python3; then
  py="$(python3 -V 2>&1 | awk '{print $2}')"
  case "$py" in
    3.1[0-3].*) pass "python $py (inside the CodeZip 3.10 to 3.13 range)" ;;
    3.9.*|3.8.*|3.[0-8].*) fail "python $py is too old   fix: CodeZip needs 3.10 to 3.13" ;;
    *) warn "python $py is outside the CodeZip 3.10 to 3.13 range; Container build may be required" ;;
  esac
else
  fail "python3 not found            fix: install Python 3.10 to 3.13"
fi

# ── the command-shadowing trap ──────────────────────────────────────────────
echo
echo "agentcore cli"

if have agentcore; then
  if agentcore --version >/dev/null 2>&1; then
    pass "agentcore $(agentcore --version 2>&1 | head -1)"
  else
    fail "agentcore exists but --version fails"
    fail "  most likely cause: the old Python package shadows the npm CLI"
    fail "  fix: pip uninstall bedrock-agentcore-starter-toolkit"
    fail "       then confirm 'command -v agentcore' points at the npm install"
  fi
else
  fail "agentcore not found          fix: npm install -g @aws/agentcore"
fi

if python3 -m pip show bedrock-agentcore-starter-toolkit >/dev/null 2>&1; then
  fail "python package bedrock-agentcore-starter-toolkit is installed and will shadow the npm CLI"
  fail "  fix: pip uninstall bedrock-agentcore-starter-toolkit"
fi

# ── identity, region, model access ──────────────────────────────────────────
echo
echo "aws environment"

if have aws; then
  account="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)"
  if [ -n "$account" ] && [ "$account" != "None" ]; then
    pass "credentials work, account $account"
  else
    fail "aws sts get-caller-identity failed   fix: check AWS_PROFILE and credentials"
  fi

  region="$(aws configure get region 2>/dev/null)"
  if [ "$region" = "$REGION_EXPECTED" ]; then
    pass "region is $REGION_EXPECTED"
  else
    warn "region is '${region:-unset}', the series targets $REGION_EXPECTED"
    warn "  why it matters: Registry is available in only 5 regions and Web Search needs us-east-1"
  fi

  if [ -n "$account" ] && [ "$account" != "None" ]; then
    found="$(aws bedrock list-foundation-models --region "$REGION_EXPECTED" \
      --query "modelSummaries[?modelId=='$MODEL_ID'].modelId | [0]" --output text 2>/dev/null)"
    if [ -n "$found" ] && [ "$found" != "None" ]; then
      pass "model $MODEL_ID is available"
    else
      warn "model $MODEL_ID not listed in $REGION_EXPECTED"
      warn "  fix: check model access, or set MODEL_ID to a model your account can call"
    fi
  fi
fi

# ── per-use-case extras ─────────────────────────────────────────────────────
if [ -n "$USECASE" ]; then
  echo
  echo "use case $USECASE extra requirements"
  case "$USECASE" in
    03|04)
      if have docker; then
        warn "docker present, but this use case does not need it (CodeZip path)"
      fi
      if have cdk; then pass "aws cdk available for inspecting generated stacks"
      else warn "cdk cli not found; only needed if you want to read the generated template"; fi
      ;;
    05)
      warn "Web Search requires us-east-1; confirm the region check above"
      ;;
    07)
      warn "Registry uses the agent-registry namespace, not bedrock-agentcore"
      warn "  policy to attach: AgentRegistryFullAccess"
      ;;
    08)
      warn "Payments needs a Coinbase CDP or Stripe (Privy) wallet account"
      warn "  fall back to sandbox/testnet if you do not have one"
      ;;
  esac
fi

echo
if [ "$FAILS" -eq 0 ]; then
  printf '\033[32mall checks passed\033[0m\n'
else
  printf '\033[31m%d check(s) failed\033[0m\n' "$FAILS"
fi
exit $((FAILS > 0 ? 1 : 0))
