from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Supplier, SupplierRateCard
from app.schemas import SupplierIn, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierIn, db: Session = Depends(get_db)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()


@router.get("/rate-cards")
def list_rate_cards(db: Session = Depends(get_db)):
    cards = db.query(SupplierRateCard).all()
    return [{"supplier_id": c.supplier_id, "product_id": c.product_id,
             "price": float(c.price) if c.price is not None else None,
             "unit": c.unit, "date": c.date.isoformat(), "discount_tier_text": c.discount_tier_text} for c in cards]
