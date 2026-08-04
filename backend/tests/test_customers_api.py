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


def test_patch_customer_updates_phone(db):
    created = client.post("/customers", json={"name": "Meena Traders"}).json()
    assert created["phone"] is None

    response = client.patch(f"/customers/{created['id']}", json={"phone": "9998887776"})
    assert response.status_code == 200
    assert response.json()["phone"] == "9998887776"

    fetched = client.get(f"/customers/{created['id']}").json()
    assert fetched["phone"] == "9998887776"


def test_patch_customer_leaves_unspecified_fields_untouched(db):
    created = client.post("/customers", json={"name": "Rakesh Traders", "area": "Rau"}).json()

    response = client.patch(f"/customers/{created['id']}", json={"phone": "9112233445"})
    assert response.status_code == 200
    assert response.json()["area"] == "Rau"


def test_patch_nonexistent_customer_returns_404(db):
    response = client.patch("/customers/999999", json={"phone": "9998887776"})
    assert response.status_code == 404
