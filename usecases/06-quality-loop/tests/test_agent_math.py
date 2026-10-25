"""Unit tests for the uc06 agent's own Python. Offline, no AWS calls.

The planted defect lives in the prompt, not the code: convert_currency is
correct, the receipts table is honest, and PROMPT_V1 tells the model never to
call it. These tests pin the arithmetic the evaluation loop depends on.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "aia_uc06"))

from main import FX_RATES, PROMPT_V1, RECEIPTS, convert_currency, lookup_policy


def test_convert_currency_eur():
    out = convert_currency(210.00, "EUR")
    assert out["amount_usd"] == 226.80
    assert out["rate_to_usd"] == 1.08


def test_convert_currency_gbp():
    out = convert_currency(195.00, "GBP")
    assert out["amount_usd"] == 247.65


def test_convert_currency_usd_is_identity():
    out = convert_currency(58.40, "USD")
    assert out["amount_usd"] == 58.40


def test_convert_currency_rejects_unknown():
    assert "error" in convert_currency(10.0, "CHF")


def test_policy_caps_shape():
    for region in ("domestic", "international"):
        for category in ("meals", "lodging", "airfare", "ground"):
            out = lookup_policy(category, region)
            assert out["cap_usd"] > 0


def test_receipts_table_mixes_currencies():
    currencies = {r["currency"] for r in RECEIPTS.values()}
    assert currencies == {"USD", "EUR", "GBP"}


def test_prompt_v1_carries_the_defect():
    # the sentences that stop the model from ever calling convert_currency
    assert "must never be called" in PROMPT_V1
    assert "already in USD" in PROMPT_V1
