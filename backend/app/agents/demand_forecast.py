from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You forecast 30-day demand for a building-materials distributor in Indore, India.
Given a product's monthly sales history and current stock, detect seasonal patterns (e.g. cement demand
rises before monsoon, paint demand rises around Diwali) and recommend a reorder quantity to avoid a
stockout in the next 30 days."""

TOOL_SCHEMA = {
    "name": "forecast",
    "description": "Forecast 30-day demand and recommend a reorder quantity",
    "input_schema": {
        "type": "object",
        "properties": {
            "predicted_30_day_demand": {"type": "number"},
            "reorder_qty": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["predicted_30_day_demand", "reorder_qty", "reasoning"],
    },
}


def forecast_demand(product_name: str, current_stock: int, monthly_sales: dict) -> dict:
    history_lines = "\n".join(f"{month}: {qty}" for month, qty in sorted(monthly_sales.items()))
    user_message = f"Product: {product_name}\nCurrent stock: {current_stock}\nMonthly sales history:\n{history_lines}"
    return call_with_tool(SYSTEM_PROMPT, user_message, TOOL_SCHEMA)
