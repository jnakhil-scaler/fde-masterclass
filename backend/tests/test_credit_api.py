from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models import Customer, CreditLedger

client = TestClient(app)


def test_credit_ledger_returns_aging(db):
    customer = Customer(name="Sharma Contractor")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow() - timedelta(days=30), type="debit", amount=100000))
    db.commit()

    response = client.get(f"/credit/{customer.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["total_outstanding"] == 100000
    assert body["oldest_days_overdue"] >= 30


def test_get_credit_risk_for_nonexistent_customer_returns_404(db):
    response = client.get("/credit/999999/risk")
    assert response.status_code == 404
