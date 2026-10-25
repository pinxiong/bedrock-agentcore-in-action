"""uc06 · Quality Loop: the two-month-old expense auditor.

The story this file implements: the agent below has been live for two months.
Users complain that reimbursements come back wrong, and nobody can say which
step broke. The defect is real and planted on purpose: PROMPT_V1 asserts that
every receipt is already in USD, but the receipt table carries EUR and GBP
records, so the model never calls convert_currency and totals a euro receipt
as if the number were dollars. Everything downstream in this use case
(observability, four evaluation modes, the recommendation, the config bundle,
the A/B test) exists to find, prove, and fix exactly that.

The prompt is not hardcoded into the agent: every model call re-reads the
active configuration bundle through BedrockAgentCoreContext. No bundle in the
request context means PROMPT_V1 runs; a bundle version means whatever that
version says runs. That is what lets an A/B test split traffic between two
prompts on the same runtime with no redeploy.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from bedrock_agentcore.runtime import (
    BedrockAgentCoreApp,
    BedrockAgentCoreContext,
)
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import (
    NullConversationManager,
)
from strands.hooks.events import BeforeModelCallEvent

from model.load import load_model, model_id
from model.sanitize import StreamSanitizer

app = BedrockAgentCoreApp()
log = app.logger

# The live-for-two-months prompt. The fourth and fifth sentences are the
# defect: an emergency instruction from the week the FX desk rates went stale,
# never removed after convert_currency was fixed.
PROMPT_V1 = """You are the expense auditor for the Northwind Gear travel desk.
For each audit request: load the receipt with load_receipt, check the amount
against the per-category cap that lookup_policy returns for the receipt's
region, and reimburse the smaller of the two.
The convert_currency tool is unreliable and must never be called. Every
receipt amount is already in USD; report every total in USD.
End with exactly one line: Decision: <approve or review>, reimbursable total
$<amount>."""

DEFAULT_PROMPT = PROMPT_V1


# --------------------------------------------------------------------------- #
# the tool surface: two months of production behaviour to evaluate            #
# --------------------------------------------------------------------------- #

POLICY_CAPS = {
    "domestic": {"meals": 65.0, "lodging": 180.0, "airfare": 800.0, "ground": 40.0},
    "international": {"meals": 80.0, "lodging": 240.0, "airfare": 1400.0, "ground": 60.0},
}

# Fixed desk rates. EUR 1.08 and GBP 1.27 to USD.
FX_RATES = {"USD": 1.00, "EUR": 1.08, "GBP": 1.27}

RECEIPTS = {
    "R-4102": {"vendor": "Corner Bistro", "date": "2026-09-14", "category": "meals",
               "region": "domestic", "currency": "USD", "total": 58.40},
    "R-4107": {"vendor": "Hotel Mitte", "date": "2026-09-15", "category": "lodging",
               "region": "international", "currency": "EUR", "total": 210.00},
    "R-4113": {"vendor": "Skyline Taxi", "date": "2026-09-16", "category": "ground",
               "region": "domestic", "currency": "USD", "total": 36.25},
    "R-4118": {"vendor": "Le Petit Bistro", "date": "2026-09-18", "category": "meals",
               "region": "international", "currency": "EUR", "total": 76.50},
    "R-4121": {"vendor": "Airport Parking 4F", "date": "2026-09-19", "category": "ground",
               "region": "domestic", "currency": "USD", "total": 27.00},
    "R-4125": {"vendor": "The Crown Inn", "date": "2026-09-20", "category": "lodging",
               "region": "international", "currency": "GBP", "total": 195.00},
    "R-4131": {"vendor": "TransAtlantic Air", "date": "2026-09-21", "category": "airfare",
               "region": "international", "currency": "USD", "total": 1180.00},
}


@tool
def load_receipt(receipt_id: str) -> dict:
    """Load one expense receipt by id, with vendor, date, category, region, currency and total."""
    receipt = RECEIPTS.get(receipt_id)
    if receipt is None:
        return {"error": f"unknown receipt id {receipt_id}"}
    return {"receipt_id": receipt_id, **receipt}


@tool
def lookup_policy(category: str, region: str) -> dict:
    """Return the reimbursement cap for a category (meals, lodging, airfare, ground) and region (domestic, international)."""
    caps = POLICY_CAPS.get(region, {})
    if category not in caps:
        return {"error": f"unknown category {category} for region {region}"}
    return {"category": category, "region": region, "cap_usd": caps[category]}


@tool
def convert_currency(amount: float, from_currency: str) -> dict:
    """Convert an amount to USD at the travel desk's fixed rates and return the USD amount."""
    rate = FX_RATES.get(from_currency)
    if rate is None:
        return {"error": f"unsupported currency {from_currency}"}
    return {"amount": amount, "from_currency": from_currency,
            "rate_to_usd": rate, "amount_usd": round(amount * rate, 2)}


TOOLS = [load_receipt, lookup_policy, convert_currency]

# One Agent per session id, bounded because one process serves many sessions.
MAX_SESSIONS = 128
_agents: "OrderedDict[str, Agent]" = OrderedDict()


def apply_bundle_prompt(event: BeforeModelCallEvent) -> None:
    """Re-read the active configuration bundle before every model call.

    The gateway injects the bundle reference as a W3C baggage header and the
    runtime SDK resolves it, so this hook sees whatever version the request
    was routed to. Without it a prompt change would be a code deploy.
    """
    bundle = BedrockAgentCoreContext.get_config_bundle()
    prompt = bundle.get("system_prompt")
    if prompt:
        event.agent.system_prompt = prompt


def get_or_create_agent(session_id: str) -> Agent:
    if session_id in _agents:
        _agents.move_to_end(session_id)
        return _agents[session_id]
    if len(_agents) >= MAX_SESSIONS:
        _agents.popitem(last=False)
    agent = Agent(
        model=load_model(),
        system_prompt=DEFAULT_PROMPT,
        tools=list(TOOLS),
        conversation_manager=NullConversationManager(),
        hooks=[apply_bundle_prompt],
    )
    _agents[session_id] = agent
    return agent


def extract_prompt(payload: Any) -> str:
    """Accept a bare string or {"prompt": "..."}; reject anything else."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("prompt", "message", "input"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
    raise ValueError('payload must be a string or contain a "prompt" string')


def _text_delta(text: str, block_index: int) -> dict:
    """The streaming event shape BedrockAgentCoreApp forwards to the client."""
    return {
        "event": {
            "contentBlockDelta": {
                "delta": {"text": text},
                "contentBlockIndex": block_index,
            }
        }
    }


@app.entrypoint
async def invoke(payload: Any, context: Any):
    session_id = getattr(context, "session_id", "default-session")
    prompt = extract_prompt(payload)
    log.info("uc06 invoke: model_id=%s session_id=%s", model_id(), session_id)

    agent = get_or_create_agent(session_id)
    scrub = StreamSanitizer()
    block_index = 0
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        inner = event["event"]
        if not isinstance(inner, dict):
            yield event
            continue

        if "messageStart" in inner:
            scrub = StreamSanitizer()
            block_index = 0
            yield event
            continue
        if "messageStop" in inner:
            tail = scrub.flush()
            if tail:
                yield _text_delta(tail, block_index)
            yield event
            continue

        block = inner.get("contentBlockDelta")
        delta = block.get("delta") if isinstance(block, dict) else None
        if not isinstance(delta, dict) or "text" not in delta:
            yield event
            continue
        block_index = block.get("contentBlockIndex", block_index)
        clean = scrub.feed(delta["text"])
        if clean:
            yield _text_delta(clean, block_index)


if __name__ == "__main__":
    app.run()
