from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.credit_risk import assess_credit_risk
from app.db import get_db
from app.models import Order, OrderItem, Customer
from app.routers.credit import compute_aging
from app.schemas import OrderIn

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    order = Order(customer_id=payload.customer_id, source=payload.source,
                  delivery_address=payload.delivery_address, delivery_time=payload.delivery_time)
    for item in payload.items:
        order.items.append(OrderItem(product_id=item.product_id, qty=item.qty, unit_price=item.unit_price))
    db.add(order)
    db.commit()
    db.refresh(order)

    new_order_amount = sum(item.qty * item.unit_price for item in payload.items)
    customer = db.query(Customer).filter_by(id=payload.customer_id).first()
    aging = compute_aging(db, payload.customer_id)
    risk = assess_credit_risk(customer.name, aging["total_outstanding"], aging["oldest_days_overdue"], new_order_amount)
    risk["total_exposure"] = aging["total_outstanding"] + new_order_amount  # deterministic, don't trust the model's echo

    return {"id": order.id, "customer_id": order.customer_id, "status": order.status, "source": order.source, "credit_risk": risk}


@router.get("")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [{"id": o.id, "customer_id": o.customer_id, "status": o.status, "source": o.source} for o in orders]
