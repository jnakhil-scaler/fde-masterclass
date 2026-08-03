from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_suppliers(db):
    response = client.post("/suppliers", json={
        "name": "UltraTech Distributors", "contact": "9123456780",
    })
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "UltraTech Distributors"

    listed = client.get("/suppliers").json()
    assert any(s["name"] == "UltraTech Distributors" for s in listed)


def test_list_rate_cards_empty(db):
    response = client.get("/suppliers/rate-cards")
    assert response.status_code == 200
    assert response.json() == []
