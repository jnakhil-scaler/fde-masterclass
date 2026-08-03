import pytest
from app.agents.claude_client import has_real_api_key
from app.agents.order_parser import parse_whatsapp_order

pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


def test_parses_fixed_golden_path_message():
    text = "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site pe bhijwa dena"
    result = parse_whatsapp_order(text)

    item_names = [item["product_hint"].lower() for item in result["items"]]
    assert any("sariya" in name or "tmt" in name for name in item_names)
    assert any("pipe" in name for name in item_names)
    assert any("cement" in name or "ultratech" in name for name in item_names)
    assert "sharma" in result["delivery_address"].lower()
