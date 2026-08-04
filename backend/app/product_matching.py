import difflib
from typing import Optional

from app.models import Product


def match_product_hint(hint: str, products: list[Product]) -> Optional[Product]:
    """Match a parsed product_hint string (e.g. 'TMT Sariya 10mm') to a real
    Product by exact/substring match first, falling back to fuzzy matching.
    No AI call -- product_hint is already fairly clean text from Agent 2, and
    an extra LLM call per item isn't worth the cost/latency for this."""
    if not hint:
        return None
    hint_lower = hint.lower().strip()
    for p in products:
        name_lower = p.name.lower()
        if name_lower == hint_lower or hint_lower in name_lower or name_lower in hint_lower:
            return p
    names = [p.name for p in products]
    close = difflib.get_close_matches(hint, names, n=1, cutoff=0.5)
    if close:
        return next((p for p in products if p.name == close[0]), None)
    return None
