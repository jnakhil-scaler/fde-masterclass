from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CreditLedger

router = APIRouter(prefix="/credit", tags=["credit"])


def compute_aging(db: Session, customer_id: int) -> dict:
    entries = db.query(CreditLedger).filter_by(customer_id=customer_id).all()
    outstanding = sum(float(e.amount) for e in entries if e.type == "debit") - sum(float(e.amount) for e in entries if e.type == "credit")
    oldest_days = max((datetime.utcnow() - e.date).days for e in entries) if entries else 0
    return {"total_outstanding": outstanding, "oldest_days_overdue": oldest_days}


@router.get("/{customer_id}")
def get_credit_ledger(customer_id: int, db: Session = Depends(get_db)):
    return compute_aging(db, customer_id)


@router.get("/{customer_id}/risk")
def get_credit_risk(customer_id: int, new_order_amount: float = 0, db: Session = Depends(get_db)):
    from app.agents.credit_risk import assess_credit_risk
    from app.models import Customer

    customer = db.query(Customer).filter_by(id=customer_id).first()
    aging = compute_aging(db, customer_id)
    risk = assess_credit_risk(customer.name, aging["total_outstanding"], aging["oldest_days_overdue"], new_order_amount)
    risk["total_exposure"] = aging["total_outstanding"] + new_order_amount  # deterministic, don't trust the model's echo
    return risk
