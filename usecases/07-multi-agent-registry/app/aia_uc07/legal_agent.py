"""uc07 legal specialist: a contract clause agent served over A2A.

One Strands agent behind the A2A protocol. Its tool is a small clause
library; the model's job is to compare a contract brief against the
reference wording and name what needs redrafting. serve_a2a wraps the
executor in the AgentCore A2A service contract (port 9000, agent card at
/.well-known/agent.json inside the runtime).
"""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent, tool
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from model.load import load_model

CLAUSE_LIBRARY = {
    "liability": "Reference: liability is capped at 12 months of fees, and the cap does not "
    "apply to confidentiality breaches or willful misconduct.",
    "termination": "Reference: termination for convenience requires 60 days notice and "
    "payment for work performed up to the termination date.",
    "payment": "Reference: invoices are payable within 30 days; late amounts accrue 1.5% "
    "per month; no set-off without written agreement.",
    "confidentiality": "Reference: confidentiality obligations survive for 5 years after "
    "termination and cover pricing, roadmaps and customer lists.",
    "subcontracting": "Reference: subcontractors need prior written approval and remain "
    "the contractor's responsibility as if the work were its own.",
}


@tool
def lookup_clause_library(clause_type: str) -> str:
    """Return the reference wording for a standard contract clause type.

    Args:
        clause_type: one of liability, termination, payment, confidentiality,
            subcontracting.
    """
    return CLAUSE_LIBRARY.get(
        clause_type.lower().strip(), f"no reference clause on file for {clause_type}"
    )


SYSTEM_PROMPT = """You are the legal clause specialist of a contract review desk.

Given a contract brief, work clause by clause. For each clause that matters,
call lookup_clause_library for its reference wording, compare, and say in one
sentence whether the clause needs redrafting and why. Always check liability,
termination and subcontracting. End with a numbered list of the clauses that
need redrafting. Be terse; the orchestrator quotes you verbatim."""


agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=[lookup_clause_library],
)

AGENT_CARD = AgentCard(
    name="aia_uc07_legal",
    description="Contract clause specialist: compares clauses against the reference library",
    url="http://localhost:9000/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text"],
    default_output_modes=["text"],
    skills=[
        AgentSkill(
            id="clause-review",
            name="Clause review",
            description="Compare contract clauses against the reference clause library",
            tags=["legal", "contract", "clause"],
            examples=["Review the liability and termination clauses of this brief"],
        )
    ],
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent), agent_card=AGENT_CARD)
