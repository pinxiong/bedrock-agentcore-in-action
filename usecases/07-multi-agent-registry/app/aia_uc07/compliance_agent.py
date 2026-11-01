"""uc07 compliance specialist: risk screening over A2A, fast and deep.

Two speeds on purpose. quick_risk_check answers in seconds and backs the
blocking A2A exchange. deep_scan runs five passes of 15 seconds each, which
is deliberately longer than the 60s ceiling of a synchronous HTTP read: it
exists so the orchestrator can demonstrate the A2A task lifecycle —
non-blocking accept, polling, streaming, and cancel. The scan sleeps in
one-second slices so a cancellation lands promptly instead of riding out a
long blocking sleep.
"""

from __future__ import annotations

import asyncio
import os

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from model.load import load_model

DEEP_SCAN_SECONDS = int(os.environ.get("DEEP_SCAN_SECONDS", "75"))
DEEP_SCAN_PASSES = 5

PASS_FINDINGS = [
    "pass 1 (data residency): no cross-border transfer clause found",
    "pass 2 (breach notice): 72-hour notification meets the 48-hour policy floor",
    "pass 3 (audit rights): no audit rights granted to the customer",
    "pass 4 (sub-processors): annex B lists 4 sub-processors, none vetted",
    "pass 5 (retention): retention period undefined after termination",
]


@tool
def quick_risk_check(contract_summary: str) -> str:
    """A fast compliance screen: pattern-match the brief against the top
    risk rules and return the hits in one line each."""
    hits = []
    lowered = contract_summary.lower()
    if "30 days notice" in lowered or "termination for convenience" in lowered:
        hits.append("termination for convenience under 60 days: policy requires 60")
    if "cap" in lowered and "liability" in lowered:
        hits.append("liability cap present: verify carve-outs for confidentiality breaches")
    if "silent" in lowered or "no audit" in lowered:
        hits.append("missing obligation (silence): subcontractor vetting or audit rights absent")
    if "72 hours" in lowered:
        hits.append("breach notice 72h: below the 48h policy floor, acceptable with sign-off")
    if not hits:
        hits.append("no policy rule hit on this brief")
    return "QUICK CHECK: " + "; ".join(hits)


@tool
async def deep_scan(contract_id: str) -> str:
    """The full five-pass compliance scan. Runs about 75 seconds; callers
    should use the A2A task lifecycle, never a blocking HTTP read."""
    per_pass = max(1, DEEP_SCAN_SECONDS // DEEP_SCAN_PASSES)
    findings = []
    for index in range(DEEP_SCAN_PASSES):
        for _ in range(per_pass):
            await asyncio.sleep(1)
        findings.append(PASS_FINDINGS[index])
    report = "\n".join(findings)
    return (
        f"DEEP SCAN COMPLETE for {contract_id} after {DEEP_SCAN_PASSES} passes "
        f"(~{DEEP_SCAN_SECONDS}s):\n{report}"
    )


SYSTEM_PROMPT = """You are the compliance specialist of a contract review desk.

Route by the caller's words:
- the message contains "deep scan": call deep_scan with the contract id and
  report what it returns, verbatim.
- anything else: call quick_risk_check with the brief you were given and
  expand each hit into one plain sentence.

Never invent contract content. End with the verdict line: ESCALATE if any
finding needs a human, CLEAR otherwise."""


agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=[quick_risk_check, deep_scan],
)

AGENT_CARD = AgentCard(
    name="aia_uc07_compliance",
    description="Compliance specialist: quick risk screens and long-running deep scans",
    url="http://localhost:9000/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text"],
    default_output_modes=["text"],
    skills=[
        AgentSkill(
            id="risk-screen",
            name="Risk screen",
            description="Fast pattern-based compliance screen of a contract brief",
            tags=["compliance", "risk"],
            examples=["Quick compliance screen of this brief"],
        ),
        AgentSkill(
            id="deep-scan",
            name="Deep scan",
            description="Five-pass deep compliance scan, about 75 seconds",
            tags=["compliance", "async", "long-running"],
            examples=["deep scan contract C-118"],
        ),
    ],
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent), agent_card=AGENT_CARD)
