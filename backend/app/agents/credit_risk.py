from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You are a credit risk analyst for Gupta Building Materials, an Indore MSME distributor.
Given a customer's overdue amount, days overdue, and a new incoming order amount, assess the risk of
extending further credit and recommend an action (e.g. dispatch as usual, require advance payment,
cash-on-delivery only). Risk thresholds: total exposure above ₹5,00,000 or over 60 days overdue is
elevated risk."""

TOOL_SCHEMA = {
    "name": "assess_risk",
    "description": "Assess credit risk for a new order",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "total_exposure": {"type": "number"},
            "recommendation": {"type": "string"},
        },
        "required": ["risk_level", "total_exposure", "recommendation"],
    },
}


def assess_credit_risk(customer_name: str, overdue_amount: float, overdue_days: int, new_order_amount: float) -> dict:
    user_message = (
        f"Customer: {customer_name}\n"
        f"Overdue amount: ₹{overdue_amount:,.0f}\n"
        f"Days overdue: {overdue_days}\n"
        f"New order amount: ₹{new_order_amount:,.0f}\n"
        f"Total exposure if dispatched: ₹{overdue_amount + new_order_amount:,.0f}"
    )
    return call_with_tool(SYSTEM_PROMPT, user_message, TOOL_SCHEMA)
