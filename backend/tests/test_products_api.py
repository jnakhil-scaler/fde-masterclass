from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_products(db):
    response = client.post("/products", json={
        "name": "Ambuja Cement", "brand": "Ambuja", "category": "Cement",
        "unit": "bag", "hsn_code": "2523", "current_stock": 340,
    })
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Ambuja Cement"

    listed = client.get("/products").json()
    assert any(p["name"] == "Ambuja Cement" for p in listed)
