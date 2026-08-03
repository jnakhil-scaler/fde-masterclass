from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_customers(db):
    response = client.post("/customers", json={
        "name": "Rajesh Kumar", "phone": "9876543210", "area": "Sector 12",
    })
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Rajesh Kumar"

    listed = client.get("/customers").json()
    assert any(c["name"] == "Rajesh Kumar" for c in listed)

    fetched = client.get(f"/customers/{created['id']}").json()
    assert fetched["name"] == "Rajesh Kumar"


def test_get_nonexistent_customer_returns_404(db):
    response = client.get("/customers/999999")
    assert response.status_code == 404
