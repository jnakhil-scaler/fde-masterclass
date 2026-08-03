import pytest
from app.agents.claude_client import has_real_api_key
from app.agents.cleaning import clean_product_name

pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


def test_dedupes_three_ambuja_cement_variants():
    result_a = clean_product_name("ambuja cem. (50 KG)")
    result_b = clean_product_name("AMBUJA CEMENT 50KG")

    assert result_a["brand"] == "Ambuja"
    assert result_a["name"] == result_b["name"]
    assert result_a["category"] == "Cement"
    assert result_a["variant"] == "50 KG Bag"
