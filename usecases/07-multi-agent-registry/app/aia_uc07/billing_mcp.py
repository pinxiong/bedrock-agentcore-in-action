"""uc07 billing MCP server: hosted on AgentCore Runtime as protocol MCP.

This server has no model and no agent loop; it is a plain MCP server whose
tools AgentCore hosts and fronts with IAM. It is also one of the two records
this use case publishes to the registry: a tool catalog entry for billing
and payment processing, which is what the semantic search assertion looks
up.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("aia_uc07_billing_mcp", host="0.0.0.0", stateless_http=True)

INVOICES = {
    "INV-2041": {"customer": "Northwind Gear", "amount_usd": 12800.00, "status": "open"},
    "INV-2042": {"customer": "Contoso Legal", "amount_usd": 4300.50, "status": "paid"},
    "INV-2043": {"customer": "Fabrikam Health", "amount_usd": 987.65, "status": "overdue"},
}

PAYMENTS = {
    "PAY-881": {"invoice": "INV-2042", "amount_usd": 4300.50, "state": "settled"},
    "PAY-882": {"invoice": "INV-2041", "amount_usd": 2000.00, "state": "processing"},
}


@mcp.tool()
def lookup_invoice(invoice_id: str) -> dict:
    """Look up an invoice by id (for example INV-2041)."""
    invoice = INVOICES.get(invoice_id.upper())
    if invoice is None:
        return {"error": f"unknown invoice {invoice_id}"}
    return {"invoice_id": invoice_id.upper(), **invoice}


@mcp.tool()
def payment_status(payment_id: str) -> dict:
    """Check the processing state of a payment by id (for example PAY-881)."""
    payment = PAYMENTS.get(payment_id.upper())
    if payment is None:
        return {"error": f"unknown payment {payment_id}"}
    return {"payment_id": payment_id.upper(), **payment}


@mcp.tool()
def refund_policy() -> str:
    """Return the standing refund policy text for billing agents."""
    return (
        "Refunds up to USD 500 are automatic within 30 days of settlement; "
        "anything larger routes to the billing manager with the invoice attached."
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
