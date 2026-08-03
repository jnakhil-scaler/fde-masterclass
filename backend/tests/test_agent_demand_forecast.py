from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.agents.claude_client import has_real_api_key
from app.agents.demand_forecast import forecast_demand
from app.main import app
from app.models import Invoice, Product

pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")

client = TestClient(app)


def test_detects_monsoon_seasonality_for_cement():
    monthly_sales = {
        "2025-04": 300, "2025-05": 350, "2025-06": 520, "2025-07": 610,
        "2025-08": 400, "2026-04": 320, "2026-05": 360, "2026-06": 540,
    }
    result = forecast_demand(product_name="UltraTech Cement", current_stock=450, monthly_sales=monthly_sales)

    assert result["predicted_30_day_demand"] > 450
    assert "monsoon" in result["reasoning"].lower() or "season" in result["reasoning"].lower()
    assert result["reorder_qty"] > 0


def test_demand_forecast_endpoint_uses_invoice_history(db):
    product = Product(name="UltraTech Cement", brand="UltraTech", category="Cement", unit="bag", hsn_code="2523", current_stock=450)
    db.add(product)
    db.commit()

    for month, qty in [(4, 300), (5, 350), (6, 900), (7, 950)]:
        db.add(Invoice(product_id=product.id, date=datetime(2026, month, 15), amount=qty * 380, qty=qty))
    db.commit()

    response = client.get(f"/agents/demand-forecast/{product.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["predicted_30_day_demand"] > 0
