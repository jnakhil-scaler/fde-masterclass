from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductIn(BaseModel):
    name: str
    brand: str
    category: str
    unit: str
    hsn_code: str
    current_stock: int = 0


class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CustomerIn(BaseModel):
    name: str
    phone: Optional[str] = None
    area: Optional[str] = None


class CustomerOut(CustomerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    area: Optional[str] = None


class SupplierIn(BaseModel):
    name: str
    contact: Optional[str] = None


class SupplierOut(SupplierIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class OrderItemIn(BaseModel):
    product_id: int
    qty: int
    unit_price: float


class OrderIn(BaseModel):
    customer_id: int
    source: str
    delivery_address: Optional[str] = None
    delivery_time: Optional[str] = None
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    status: str
    source: str
    credit_risk: Optional[dict] = None
