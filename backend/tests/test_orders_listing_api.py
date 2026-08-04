from fastapi.testclient import TestClient
from app.main import app
from app.models import Customer, Product, Order, OrderItem

client = TestClient(app)


def test_list_orders_includes_customer_and_item_details(db):
    customer = Customer(name="Priya Enterprises")
    db.add(customer)
    db.commit()
    product = Product(name="Ambuja Cement", brand="Ambuja", category="Cement", unit="bag", hsn_code="2523", current_stock=100)
    db.add(product)
    db.commit()
    order = Order(customer_id=customer.id, source="manual", total_amount=3800)
    order.items.append(OrderItem(product_id=product.id, qty=10, unit_price=380))
    db.add(order)
    db.commit()

    response = client.get("/orders")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    listed = body[0]
    assert listed["customer_name"] == "Priya Enterprises"
    assert listed["source"] == "manual"
    assert listed["total_amount"] == 3800.0
    assert listed["items"] == [{"product_id": product.id, "product_name": "Ambuja Cement", "qty": 10, "unit_price": 380.0}]


def test_list_orders_is_newest_first(db):
    customer = Customer(name="Rohan Enterprises")
    db.add(customer)
    db.commit()
    older = Order(customer_id=customer.id, source="manual", total_amount=100)
    db.add(older)
    db.commit()
    newer = Order(customer_id=customer.id, source="manual", total_amount=200)
    db.add(newer)
    db.commit()

    response = client.get("/orders")
    ids = [o["id"] for o in response.json()]
    assert ids.index(newer.id) < ids.index(older.id)
