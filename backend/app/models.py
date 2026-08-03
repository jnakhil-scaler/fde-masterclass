from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20))
    hsn_code: Mapped[str] = mapped_column(String(20))
    current_stock: Mapped[int] = mapped_column(Integer, default=0)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    source: Mapped[str] = mapped_column(String(20))
    delivery_address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    delivery_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship(back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unknown")


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    date: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String(10))  # "debit" | "credit"
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class SupplierRateCard(Base):
    __tablename__ = "supplier_rate_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    unit: Mapped[str] = mapped_column(String(20))
    date: Mapped[datetime] = mapped_column(DateTime)
    discount_tier_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class WhatsappMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    parsed_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
