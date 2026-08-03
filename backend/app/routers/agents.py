from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.order_parser import parse_whatsapp_order

router = APIRouter(prefix="/agents", tags=["agents"])


class ParseOrderRequest(BaseModel):
    raw_text: str


@router.post("/parse-order")
def parse_order(payload: ParseOrderRequest):
    return parse_whatsapp_order(payload.raw_text)
