import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.claude_client import has_real_api_key
from app.models import Customer, Product, CreditLedger
from datetime import datetime, timedelta

client = TestClient(app)
pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


def test_creating_order_for_overdue_customer_returns_risk_flag(db):
    customer = Customer(name="Vinod Builders")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow() - timedelta(days=82), type="debit", amount=410000))
    db.commit()

    product = Product(name="TMT Sariya 10mm", brand="Generic", category="Steel", unit="ton", hsn_code="7213", current_stock=10)
    db.add(product)
    db.commit()

    response = client.post("/orders", json={
        "customer_id": customer.id, "source": "whatsapp",
        "items": [{"product_id": product.id, "qty": 2, "unit_price": 175000}],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["credit_risk"]["risk_level"] in ("medium", "high")
    # total_exposure is now deterministically overwritten (overdue + new_order_amount),
    # so this is guaranteed correct rather than dependent on model behavior.
    assert body["credit_risk"]["total_exposure"] == 760000  # 410000 + 2*175000
