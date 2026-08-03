from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You parse Hinglish WhatsApp order messages from contractors for Gupta Building Materials.
Extract every item with its quantity and unit, the delivery address, and the delivery time. Common
abbreviations: 'sariya' = TMT steel bars, 'cem'/'cement' = cement, 'bhej do'/'bhijwa dena' = please deliver.
Quantities may appear before or after the item name."""

TOOL_SCHEMA = {
    "name": "extract_order",
    "description": "Extract a structured order from a raw WhatsApp message",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_hint": {"type": "string", "description": "e.g. 'TMT Sariya 10mm'"},
                        "qty": {"type": "number"},
                        "unit": {"type": "string"},
                    },
                    "required": ["product_hint", "qty", "unit"],
                },
            },
            "delivery_address": {"type": "string"},
            "delivery_time": {"type": "string"},
        },
        "required": ["items", "delivery_address", "delivery_time"],
    },
}


def parse_whatsapp_order(raw_text: str) -> dict:
    return call_with_tool(SYSTEM_PROMPT, raw_text, TOOL_SCHEMA)
