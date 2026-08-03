import pytest
from app.agents.claude_client import has_real_api_key
from app.agents.credit_risk import assess_credit_risk

pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


def test_flags_high_risk_for_vinod_builders_golden_path():
    result = assess_credit_risk(
        customer_name="Vinod Builders",
        overdue_amount=410000,
        overdue_days=82,
        new_order_amount=350000,
    )
    assert result["risk_level"] == "high"
    assert result["total_exposure"] == 760000
    assert "advance" in result["recommendation"].lower() or "cash" in result["recommendation"].lower()


def test_low_risk_for_customer_with_no_overdue():
    result = assess_credit_risk(
        customer_name="Sharma Contractor",
        overdue_amount=0,
        overdue_days=0,
        new_order_amount=50000,
    )
    assert result["risk_level"] == "low"
