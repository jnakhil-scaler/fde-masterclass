from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.demand_forecast import forecast_demand
from app.agents.order_parser import parse_whatsapp_order
from app.db import get_db
from app.models import Customer, Invoice, Product, SupplierRateCard
from app.product_matching import match_product_hint
from app.routers.orders import create_order_from_items

router = APIRouter(prefix="/agents", tags=["agents"])


class ParseOrderRequest(BaseModel):
    raw_text: str
    sender_phone: Optional[str] = None


@router.post("/parse-order")
def parse_order(payload: ParseOrderRequest, db: Session = Depends(get_db)):
    try:
        parsed = parse_whatsapp_order(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not parse the message: {e}")

    parsed["created_order"] = None

    if payload.sender_phone:
        customer = db.query(Customer).filter_by(phone=payload.sender_phone).first()
        if customer:
            products = db.query(Product).all()
            order_items = []
            for item in parsed.get("items", []):
                product = match_product_hint(item.get("product_hint", ""), products)
                if product:
                    rate = (
                        db.query(SupplierRateCard)
                        .filter(SupplierRateCard.product_id == product.id, SupplierRateCard.price.isnot(None))
                        .order_by(SupplierRateCard.price.asc())
                        .first()
                    )
                    unit_price = float(rate.price) if rate else 0.0
                    order_items.append({"product_id": product.id, "qty": item.get("qty", 1), "unit_price": unit_price})
            if order_items:
                parsed["created_order"] = create_order_from_items(
                    db, customer=customer, items=order_items, source="whatsapp",
                    delivery_address=parsed.get("delivery_address"), delivery_time=parsed.get("delivery_time"),
                )

    return parsed


@router.get("/demand-forecast/{product_id}")
def demand_forecast(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rows = db.query(Invoice.date, Invoice.qty).filter(Invoice.product_id == product_id).all()

    monthly = defaultdict(int)
    for invoice_date, qty in rows:
        # null qty treated as 0 sales, not excluded from the month's total --
        # acceptable simplification for demo scope, no null qty in seed data
        monthly[invoice_date.strftime("%Y-%m")] += qty or 0
    return forecast_demand(product.name, product.current_stock, dict(monthly))
