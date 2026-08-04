import pytest
from fastapi.testclient import TestClient

from app.agents.claude_client import has_real_api_key
from app.agents.order_parser import parse_whatsapp_order
from app.main import app
from app.models import Customer, Product

client = TestClient(app)
pytestmark = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


def test_parses_fixed_golden_path_message():
    text = "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site pe bhijwa dena"
    result = parse_whatsapp_order(text)

    item_names = [item["product_hint"].lower() for item in result["items"]]
    assert any("sariya" in name or "tmt" in name for name in item_names)
    assert any("pipe" in name for name in item_names)
    assert any("cement" in name or "ultratech" in name for name in item_names)
    assert "sharma" in result["delivery_address"].lower()


def test_parse_order_with_sender_phone_creates_real_order(db):
    customer = Customer(name="Test Sariya Buyer", phone="+919999999999")
    db.add(customer)
    product = Product(name="TMT Sariya 10mm", brand="Generic", category="Steel", unit="ton", hsn_code="7213", current_stock=10)
    db.add(product)
    db.commit()

    response = client.post("/agents/parse-order", json={
        "raw_text": "bhai 10mm sariya 2 ton kal subah bhej do",
        "sender_phone": "+919999999999",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["created_order"] is not None
    assert body["created_order"]["customer_id"] == customer.id
    assert body["created_order"]["total_amount"] >= 0
