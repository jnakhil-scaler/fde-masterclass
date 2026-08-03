from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You clean messy Indian building-materials inventory data for Gupta Building Materials.
Given one raw product name string exactly as it appears in a hand-maintained Excel sheet, return the
normalized product it refers to. Known brands include Ambuja, UltraTech, Asian Paints. Categories include
Cement, Steel, Pipes, Electrical, Paints, Hardware. HSN codes: Cement=2523, Steel=7213, Pipes=3917,
Electrical=8544, Paints=3208, Hardware=7318."""

TOOL_SCHEMA = {
    "name": "normalize_product",
    "description": "Return the normalized product for a raw inventory name",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Canonical product name, e.g. 'Ambuja Cement'"},
            "brand": {"type": "string"},
            "variant": {"type": "string", "description": "e.g. '50 KG Bag'"},
            "category": {"type": "string"},
            "hsn": {"type": "string"},
        },
        "required": ["name", "brand", "variant", "category", "hsn"],
    },
}


def clean_product_name(raw_name: str) -> dict:
    return call_with_tool(SYSTEM_PROMPT, f"Raw product name: {raw_name!r}", TOOL_SCHEMA)
