from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.credit_risk import assess_credit_risk
from app.db import get_db
from app.models import Order, OrderItem, Customer
from app.routers.credit import compute_aging
from app.schemas import OrderIn

router = APIRouter(prefix="/orders", tags=["orders"])


def create_order_from_items(db: Session, customer: Customer, items: list[dict], source: str,
                             delivery_address: str = None, delivery_time: str = None) -> dict:
    """items: list of {product_id, qty, unit_price}. Returns the same response
    shape create_order's endpoint already returns, now including total_amount."""
    order = Order(customer_id=customer.id, source=source, delivery_address=delivery_address, delivery_time=delivery_time)
    total_amount = 0
    for item in items:
        order.items.append(OrderItem(product_id=item["product_id"], qty=item["qty"], unit_price=item["unit_price"]))
        total_amount += item["qty"] * item["unit_price"]
    order.total_amount = total_amount
    db.add(order)
    db.commit()
    db.refresh(order)

    aging = compute_aging(db, customer.id)
    try:
        risk = assess_credit_risk(customer.name, aging["total_outstanding"], aging["oldest_days_overdue"], total_amount)
        risk["total_exposure"] = aging["total_outstanding"] + total_amount  # deterministic, don't trust the model's echo
    except Exception as e:
        risk = {"risk_level": "unknown", "total_exposure": aging["total_outstanding"] + total_amount, "recommendation": f"Credit check unavailable: {e}"}

    return {"id": order.id, "customer_id": order.customer_id, "status": order.status, "source": order.source,
            "total_amount": float(total_amount), "credit_risk": risk}


@router.post("", status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    items = [{"product_id": i.product_id, "qty": i.qty, "unit_price": i.unit_price} for i in payload.items]
    return create_order_from_items(db, customer=customer, items=items, source=payload.source,
                                    delivery_address=payload.delivery_address, delivery_time=payload.delivery_time)


@router.get("")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [{"id": o.id, "customer_id": o.customer_id, "status": o.status, "source": o.source} for o in orders]
