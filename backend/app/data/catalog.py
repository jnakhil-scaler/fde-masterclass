"""Shared source of truth for the Gupta Traders product catalog.

Both the synthetic data generator (app/data/generate_data.py) and the
cleaning agent's system prompt (app/agents/cleaning.py) need the same
brand/category/HSN facts. Keeping them here means a change to one is a
change to both, instead of the agent prompt silently drifting out of
sync with whatever generate_data.py actually produces.
"""

PRODUCT_CATALOG = [
    ("Ambuja Cement", "Cement", "bag", 50, "2523"),
    ("UltraTech Cement", "Cement", "bag", 50, "2523"),
    ("TMT Sariya 10mm", "Steel", "ton", 1, "7213"),
    ("TMT Sariya 12mm", "Steel", "ton", 1, "7213"),
    ("PVC Pipe 1 inch", "Pipes", "piece", 1, "3917"),
    ("GI Wire", "Electrical", "coil", 1, "8544"),
    ("Asian Paints Emulsion", "Paints", "litre", 1, "3208"),
]

KNOWN_BRANDS = ["Ambuja", "UltraTech", "Asian Paints"]
KNOWN_CATEGORIES = ["Cement", "Steel", "Pipes", "Electrical", "Paints", "Hardware"]
HSN_BY_CATEGORY = {
    "Cement": "2523",
    "Steel": "7213",
    "Pipes": "3917",
    "Electrical": "8544",
    "Paints": "3208",
    "Hardware": "7318",
}
