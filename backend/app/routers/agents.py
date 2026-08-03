from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.demand_forecast import forecast_demand
from app.agents.order_parser import parse_whatsapp_order
from app.db import get_db
from app.models import Invoice, Product

router = APIRouter(prefix="/agents", tags=["agents"])


class ParseOrderRequest(BaseModel):
    raw_text: str


@router.post("/parse-order")
def parse_order(payload: ParseOrderRequest):
    return parse_whatsapp_order(payload.raw_text)


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
