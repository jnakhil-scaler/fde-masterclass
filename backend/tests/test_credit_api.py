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


def test_top_outstanding_customers_ranks_by_outstanding_desc(db):
    alpha = Customer(name="Alpha Traders")
    beta = Customer(name="Beta Traders")
    db.add_all([alpha, beta])
    db.commit()
    db.add(CreditLedger(customer_id=alpha.id, date=datetime.utcnow(), type="debit", amount=50000))
    db.add(CreditLedger(customer_id=beta.id, date=datetime.utcnow(), type="debit", amount=200000))
    db.commit()

    response = client.get("/credit/top-outstanding?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body[0] == {"customer_id": beta.id, "name": "Beta Traders", "outstanding": 200000.0}
    assert body[1] == {"customer_id": alpha.id, "name": "Alpha Traders", "outstanding": 50000.0}


def test_top_outstanding_customers_respects_limit(db):
    for i in range(3):
        customer = Customer(name=f"Customer {i}")
        db.add(customer)
        db.commit()
        db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="debit", amount=1000 * (i + 1)))
        db.commit()

    response = client.get("/credit/top-outstanding?limit=2")
    assert len(response.json()) == 2


def test_top_outstanding_customers_nets_credits_against_debits(db):
    customer = Customer(name="Gamma Traders")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="debit", amount=100000))
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="credit", amount=30000))
    db.commit()

    response = client.get("/credit/top-outstanding?limit=5")
    assert response.json()[0]["outstanding"] == 70000.0
