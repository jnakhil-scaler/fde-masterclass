# Gupta Building Materials — FDE Masterclass Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Gupta Building Materials demo — 5 messy datasets, unified Postgres schema, FastAPI backend, React dashboard, and 4 Claude-powered agents — deployed to Railway and rehearsed today, ready for a live 3-hour masterclass tomorrow, plus the presenter's lecture script.

**Architecture:** A single FastAPI service serves both the REST API and the built React static files, backed by Railway Postgres. Data flows raw files → deterministic cleanup → Agent 1 (ambiguous cases) → Postgres → REST API → React dashboard, with Agents 2–4 invoked live from specific endpoints.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Postgres (psycopg), Pandas + Faker (data generation), Anthropic Python SDK (Claude API, structured tool-use output), pytest + httpx (backend tests), React (Vite), Railway (deploy).

Spec: `docs/superpowers/specs/2026-08-03-gupta-traders-fde-demo-design.md` — read it before starting; every §-reference below points there.

---

## File Structure

```
backend/
  app/
    main.py               # FastAPI app, mounts routers + serves React build
    db.py                 # SQLAlchemy engine/session, DATABASE_URL from env
    models.py              # All ORM models (§4.3)
    schemas.py             # Pydantic request/response schemas
    routers/
      products.py
      customers.py
      suppliers.py
      orders.py
      credit.py
      agents.py            # /agents/parse-order, /agents/demand-forecast
    agents/
      claude_client.py      # shared Anthropic client + helper for tool-use calls
      cleaning.py           # Agent 1
      order_parser.py       # Agent 2
      credit_risk.py        # Agent 3
      demand_forecast.py    # Agent 4
    data/
      generate_data.py      # produces the 5 raw messy files (§4.1, §4.2)
      ingest.py              # the 5-step raw-to-Postgres pipeline (§4.4)
      raw/                   # generated files land here (gitignored)
  tests/
    conftest.py
    test_generate_data.py
    test_ingest.py
    test_models.py
    test_products_api.py
    test_orders_api.py
    test_credit_api.py
    test_agent_cleaning.py
    test_agent_order_parser.py
    test_agent_credit_risk.py
    test_agent_demand_forecast.py
  requirements.txt
  railway.json
frontend/
  src/
    main.jsx
    api.js                 # fetch wrapper for the backend
    App.jsx
    pages/
      Overview.jsx
      Orders.jsx
      Customers.jsx
      Suppliers.jsx
  package.json
  vite.config.js
docs/
  superpowers/specs/2026-08-03-gupta-traders-fde-demo-design.md   # existing
  superpowers/plans/2026-08-03-gupta-traders-fde-demo-plan.md      # this file
  lecture-script.md       # final deliverable (§11), written in the last task
```

Each backend router owns one REST resource; each agent is one file with one function signature; the frontend has one file per dashboard view. Files that change together (a router and its Pydantic schemas) still live in separate `routers/` vs `schemas.py` because schemas are shared across routers — splitting by technical layer here matches how small this backend actually is (single schemas.py is ~150 lines total, not worth per-router duplication).

---

## Task 0: Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Create: `backend/.env.example`
- Create: `.gitignore`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Create the backend directory and virtualenv**

```bash
mkdir -p backend/app/routers backend/app/agents backend/app/data/raw backend/tests
cd backend && python3 -m venv .venv && source .venv/bin/activate
```

- [ ] **Step 2: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
psycopg[binary]==3.2.2
pydantic==2.9.2
pandas==2.2.3
faker==28.4.1
openpyxl==3.1.5
anthropic==0.34.2
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

Run: `pip install -r requirements.txt`
Expected: all packages install cleanly.

- [ ] **Step 3: Write `backend/app/db.py`**

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/gupta_traders")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Write the failing test for the app boots**

```python
# backend/tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'` (or import error, since `main.py` doesn't exist yet)

- [ ] **Step 6: Write minimal `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Gupta Building Materials API")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 8: Write `.gitignore` and `.env.example`**

```
# .gitignore
backend/.venv/
backend/app/data/raw/
__pycache__/
*.pyc
.env
frontend/node_modules/
frontend/dist/
```

```
# backend/.env.example
DATABASE_URL=postgresql+psycopg://localhost/gupta_traders
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/app/__init__.py backend/app/db.py backend/app/main.py backend/tests/test_main.py backend/.env.example .gitignore
git commit -m "feat: scaffold FastAPI backend with health check"
```

---

## Task 1: Data Generation Script (§4.1, §4.2)

**Files:**
- Create: `backend/app/data/generate_data.py`
- Test: `backend/tests/test_generate_data.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_generate_data.py
import json
import pandas as pd
from app.data.generate_data import generate_all, OUTPUT_DIR


def test_generates_all_five_files():
    generate_all(seed=42)
    assert (OUTPUT_DIR / "stock_register.xlsx").exists()
    assert (OUTPUT_DIR / "tally_export.csv").exists()
    assert (OUTPUT_DIR / "khata_ledger.csv").exists()
    assert (OUTPUT_DIR / "whatsapp_orders.json").exists()
    assert (OUTPUT_DIR / "supplier_rates.csv").exists()


def test_stock_register_has_name_variants_for_ambuja_cement():
    generate_all(seed=42)
    sheets = pd.read_excel(OUTPUT_DIR / "stock_register.xlsx", sheet_name=None)
    all_rows = pd.concat(sheets.values())
    ambuja_variants = all_rows[all_rows["product_name"].str.contains("mbuja", case=False, na=False)]
    assert ambuja_variants["product_name"].nunique() >= 3


def test_khata_ledger_includes_vinod_builders_golden_path():
    generate_all(seed=42)
    df = pd.read_csv(OUTPUT_DIR / "khata_ledger.csv")
    vinod_rows = df[df["customer_name"] == "Vinod Builders"]
    assert len(vinod_rows) > 0
    assert vinod_rows["amount_text"].str.contains("4.1L|4,10,000", regex=True).any()


def test_whatsapp_orders_includes_fixed_golden_path_message():
    generate_all(seed=42)
    messages = json.loads((OUTPUT_DIR / "whatsapp_orders.json").read_text())
    texts = [m["raw_text"] for m in messages]
    assert any("10mm sariya 2 ton" in t for t in texts)


def test_tally_export_has_monsoon_cement_spike():
    generate_all(seed=42)
    df = pd.read_csv(OUTPUT_DIR / "tally_export.csv")
    cement = df[df["product_name"].str.contains("Cement", na=False)].copy()
    cement["date"] = pd.to_datetime(cement["date"], format="mixed", dayfirst=True)
    monsoon_avg = cement[cement["date"].dt.month.isin([4, 5, 6, 7])]["qty"].mean()
    off_season_avg = cement[~cement["date"].dt.month.isin([4, 5, 6, 7])]["qty"].mean()
    assert monsoon_avg > off_season_avg * 1.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_generate_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.data.generate_data'`

- [ ] **Step 3: Write `backend/app/data/generate_data.py`**

```python
import json
from pathlib import Path
import random

import pandas as pd
from faker import Faker

OUTPUT_DIR = Path(__file__).parent / "raw"

PRODUCT_CATALOG = [
    ("Ambuja Cement", "Cement", "bag", 50, "2523"),
    ("UltraTech Cement", "Cement", "bag", 50, "2523"),
    ("TMT Sariya 10mm", "Steel", "ton", 1, "7213"),
    ("TMT Sariya 12mm", "Steel", "ton", 1, "7213"),
    ("PVC Pipe 1 inch", "Pipes", "piece", 1, "3917"),
    ("GI Wire", "Electrical", "coil", 1, "8544"),
    ("Asian Paints Emulsion", "Paints", "litre", 1, "3208"),
]

NAME_VARIANT_TEMPLATES = [
    "{brand} {kg}kg",
    "{lower} ({kg} KG)",
    "{upper} {kg}KG",
]


def _name_variants(brand: str, kg: int = 50):
    return [
        NAME_VARIANT_TEMPLATES[0].format(brand=brand, kg=kg),
        NAME_VARIANT_TEMPLATES[1].format(lower=brand.lower()[:9] + ".", kg=kg),
        NAME_VARIANT_TEMPLATES[2].format(upper=brand.upper(), kg=kg),
    ]


def _generate_stock_register(fake: Faker, rng: random.Random) -> pd.DataFrame:
    rows = []
    for name, category, unit, _, hsn in PRODUCT_CATALOG:
        variants = _name_variants(name) if category == "Cement" else [name]
        for variant in variants:
            rows.append({
                "product_name": variant,
                "category": category,
                "unit": rng.choice([unit, unit + "s", unit.upper(), "BGS" if unit == "bag" else unit]),
                "qty": rng.choice([rng.randint(10, 500), -rng.randint(1, 20)]),
                "hsn_code": hsn,
            })
    # pad out to ~500 SKUs with generic hardware items
    for _ in range(500 - len(rows)):
        rows.append({
            "product_name": fake.word().title() + " " + rng.choice(["Bolt", "Nut", "Hinge", "Clamp"]),
            "category": "Hardware",
            "unit": rng.choice(["piece", "pieces", "PCS"]),
            "qty": rng.randint(0, 300),
            "hsn_code": "7318",
        })
    df = pd.DataFrame(rows)
    n = len(df)
    split = n // 3
    return {
        "Sheet1": df.iloc[:split],
        "Sheet2": df.iloc[split:2 * split],
        "Sheet3": df.iloc[2 * split:],
    }


MONSOON_MONTHS = {4, 5, 6, 7}  # April-July: cement demand spike (§4.2)


def _generate_tally_export(fake: Faker, rng: random.Random) -> pd.DataFrame:
    """Produces 2 years of invoices. Each invoice is itemized to one product (a simplification of
    the real brief's non-itemized Tally export) so Agent 4 has real per-product monthly history to
    detect seasonality against — see §4.2's monsoon-seasonality golden path."""
    date_formats = ["%d/%m/%y", "%d-%b-%Y"]
    rows = []
    for _ in range(3000):
        date = fake.date_between(start_date="-2y", end_date="today")
        is_cement = rng.random() < 0.4
        product_name = rng.choice(["Ambuja Cement", "UltraTech Cement"]) if is_cement else rng.choice(
            [p[0] for p in PRODUCT_CATALOG if p[1] != "Cement"]
        )
        base_qty = rng.randint(20, 80)
        qty = base_qty * 3 if (is_cement and date.month in MONSOON_MONTHS) else base_qty
        rows.append({
            "date": date.strftime(rng.choice(date_formats)),
            "customer": rng.choice(["CASH", fake.company()]),
            "product_name": product_name,
            "qty": qty,
            "amount": f"₹{qty * rng.randint(340, 420):,}",
            "gst_number": None if rng.random() < 0.3 else fake.bothify("22#####?#?#?#Z#"),
        })
    return pd.DataFrame(rows)


def _generate_khata_ledger(fake: Faker, rng: random.Random) -> pd.DataFrame:
    rows = []
    customers = [fake.name() + " Contractor" for _ in range(339)] + ["Vinod Builders"]
    for customer in customers:
        entries = 1 if customer != "Vinod Builders" else 3
        for _ in range(entries):
            if customer == "Vinod Builders":
                rows.append({
                    "customer_name": customer,
                    "date_text": "12 May",
                    "amount_text": "4.1L overdue",
                    "note": "bola hai jaldi de dega",
                })
            else:
                rows.append({
                    "customer_name": customer,
                    "date_text": fake.date_this_year().strftime("%d %b"),
                    "amount_text": rng.choice([f"{rng.randint(10,90)}k liya", f"{rng.randint(1,9)}.{rng.randint(0,9)}L"]),
                    "note": rng.choice(["baaki agle mahine", "poora paid", ""]),
                })
    return pd.DataFrame(rows)


def _generate_whatsapp_orders(fake: Faker, rng: random.Random) -> list[dict]:
    messages = [{
        "id": 1,
        "raw_text": "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site pe bhijwa dena",
        "timestamp": "2026-08-01T18:22:00",
    }]
    for i in range(2, 201):
        messages.append({
            "id": i,
            "raw_text": f"{fake.first_name()} bhai {rng.randint(5,100)} bag cem chahiye kal tak",
            "timestamp": fake.date_time_this_year().isoformat(),
        })
    return messages


def _generate_supplier_rates(fake: Faker, rng: random.Random) -> pd.DataFrame:
    rows = []
    for s in range(1, 13):
        supplier = f"Supplier {s}"
        for name, _, unit, _, _ in PRODUCT_CATALOG:
            rows.append({
                "supplier_name": supplier,
                "product_name": name,
                "price": rng.choice([f"{rng.randint(300,450)}/bag", "call for rate"]),
                "unit": unit,
                "as_of_date": fake.date_between(start_date="-6M", end_date="today").isoformat(),
                "discount_text": rng.choice(["", "5% above 500 bags", "2% cash discount"]),
            })
    return pd.DataFrame(rows)


def generate_all(seed: int = 42):
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_DIR / "stock_register.xlsx") as writer:
        for sheet_name, sheet_df in _generate_stock_register(fake, rng).items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    _generate_tally_export(fake, rng).to_csv(OUTPUT_DIR / "tally_export.csv", index=False)
    _generate_khata_ledger(fake, rng).to_csv(OUTPUT_DIR / "khata_ledger.csv", index=False)
    (OUTPUT_DIR / "whatsapp_orders.json").write_text(json.dumps(_generate_whatsapp_orders(fake, rng), indent=2))
    _generate_supplier_rates(fake, rng).to_csv(OUTPUT_DIR / "supplier_rates.csv", index=False)


if __name__ == "__main__":
    generate_all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_generate_data.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/generate_data.py backend/tests/test_generate_data.py
git commit -m "feat: generate 5 raw messy datasets with seeded golden-path records"
```

---

## Task 2: Unified Postgres Schema (§4.3)

**Files:**
- Create: `backend/app/models.py`
- Test: `backend/tests/test_models.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: Write `backend/tests/conftest.py`** (test DB fixture, used by every backend test from here on)

```python
import os
os.environ["DATABASE_URL"] = "postgresql+psycopg://localhost/gupta_traders_test"

import pytest
from app.db import Base, engine, SessionLocal


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()
```

Run: `createdb gupta_traders_test` (one-time, requires local Postgres running)

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_models.py
from app.models import Product, Customer, Order, OrderItem, Invoice, CreditLedger, Supplier, SupplierRateCard, WhatsappMessage


def test_can_create_product_and_query_it(db):
    product = Product(name="Ambuja Cement", brand="Ambuja", category="Cement", unit="bag", hsn_code="2523", current_stock=340)
    db.add(product)
    db.commit()

    fetched = db.query(Product).filter_by(name="Ambuja Cement").first()
    assert fetched.current_stock == 340


def test_order_links_to_customer_and_items(db):
    customer = Customer(name="Vinod Builders", phone="9000000000", area="Indore")
    db.add(customer)
    db.commit()

    product = Product(name="TMT Sariya 10mm", brand="Generic", category="Steel", unit="ton", hsn_code="7213", current_stock=10)
    db.add(product)
    db.commit()

    order = Order(customer_id=customer.id, source="whatsapp", delivery_address="Sharma site", delivery_time="tomorrow morning")
    order.items.append(OrderItem(product_id=product.id, qty=2, unit_price=45000))
    db.add(order)
    db.commit()

    fetched = db.query(Order).filter_by(customer_id=customer.id).first()
    assert len(fetched.items) == 1
    assert fetched.items[0].qty == 2


def test_whatsapp_message_stores_raw_metadata_as_jsonb(db):
    msg = WhatsappMessage(raw_text="bhai 50 bag cem chahiye", raw_metadata={"is_voice_note": False})
    db.add(msg)
    db.commit()

    fetched = db.query(WhatsappMessage).first()
    assert fetched.raw_metadata["is_voice_note"] is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 4: Write `backend/app/models.py`**

```python
from datetime import datetime

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
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    area: Mapped[str] = mapped_column(String(100), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    source: Mapped[str] = mapped_column(String(20))
    delivery_address: Mapped[str] = mapped_column(String(300), nullable=True)
    delivery_time: Mapped[str] = mapped_column(String(100), nullable=True)

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
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    gst_number: Mapped[str] = mapped_column(String(20), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unknown")


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    date: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String(10))  # "debit" | "credit"
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    note: Mapped[str] = mapped_column(Text, nullable=True)
    source_raw: Mapped[str] = mapped_column(Text, nullable=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    contact: Mapped[str] = mapped_column(String(100), nullable=True)


class SupplierRateCard(Base):
    __tablename__ = "supplier_rate_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    unit: Mapped[str] = mapped_column(String(20))
    date: Mapped[datetime] = mapped_column(DateTime)
    discount_tier_text: Mapped[str] = mapped_column(String(200), nullable=True)


class WhatsappMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    parsed_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py backend/tests/conftest.py
git commit -m "feat: add unified Postgres schema (products, orders, credit, suppliers, whatsapp)"
```

---

## Task 3: Ingestion Pipeline — Deterministic Steps (§4.4, steps 1/2/4/5)

Agent 1 (step 3, ambiguous-case resolution) is deliberately excluded from this task and built next in Task 4 — this task covers only the deterministic, non-AI parts of the pipeline so it can be tested without hitting the Claude API.

**Files:**
- Create: `backend/app/data/ingest.py`
- Test: `backend/tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_ingest.py
from app.data.generate_data import generate_all
from app.data.ingest import extract, clean_tally_dates_and_amounts, clean_khata_entries
from app.models import Invoice, CreditLedger


def test_extract_reads_all_five_raw_files():
    generate_all(seed=42)
    raw = extract()
    assert set(raw.keys()) == {"stock", "tally", "khata", "whatsapp", "rates"}
    assert len(raw["tally"]) == 3000


def test_clean_tally_normalizes_dates_and_strips_currency_symbols():
    generate_all(seed=42)
    raw = extract()
    cleaned = clean_tally_dates_and_amounts(raw["tally"])
    assert cleaned["amount"].dtype.kind == "f"
    assert cleaned["date"].dtype.kind == "M"  # datetime64


def test_clean_khata_parses_lakh_shorthand_to_numeric_amount():
    generate_all(seed=42)
    raw = extract()
    cleaned = clean_khata_entries(raw["khata"])
    vinod = cleaned[cleaned["customer_name"] == "Vinod Builders"]
    assert (vinod["amount"] == 410000).any()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.data.ingest'`

- [ ] **Step 3: Write `backend/app/data/ingest.py`** (extract + deterministic cleanup only; load/verify added in Task 5 once Agent 1 exists)

```python
import json
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parent / "raw"


def extract() -> dict:
    """Step 1 (§4.4): read each raw file into a DataFrame, unchanged."""
    stock_sheets = pd.read_excel(RAW_DIR / "stock_register.xlsx", sheet_name=None)
    stock = pd.concat(stock_sheets.values(), ignore_index=True)
    tally = pd.read_csv(RAW_DIR / "tally_export.csv")
    khata = pd.read_csv(RAW_DIR / "khata_ledger.csv")
    whatsapp = json.loads((RAW_DIR / "whatsapp_orders.json").read_text())
    rates = pd.read_csv(RAW_DIR / "supplier_rates.csv")
    return {"stock": stock, "tally": tally, "khata": khata, "whatsapp": whatsapp, "rates": rates}


def clean_tally_dates_and_amounts(tally: pd.DataFrame) -> pd.DataFrame:
    """Step 2 (§4.4): parse mixed date formats, strip currency symbols."""
    df = tally.copy()

    def parse_date(value: str):
        for fmt in ("%d/%m/%y", "%d-%b-%Y"):
            try:
                return pd.to_datetime(value, format=fmt)
            except ValueError:
                continue
        return pd.NaT

    df["date"] = df["date"].apply(parse_date)
    df["amount"] = (
        df["amount"].astype(str).str.replace("₹", "", regex=False).str.replace(",", "", regex=False).astype(float)
    )
    return df


_LAKH_RE = re.compile(r"([\d.]+)\s*L", re.IGNORECASE)
_K_RE = re.compile(r"([\d.]+)\s*k", re.IGNORECASE)


def _parse_amount_text(text: str) -> float | None:
    if not isinstance(text, str):
        return None
    lakh_match = _LAKH_RE.search(text)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000
    k_match = _K_RE.search(text)
    if k_match:
        return float(k_match.group(1)) * 1_000
    return None


def clean_khata_entries(khata: pd.DataFrame) -> pd.DataFrame:
    """Step 2 (§4.4): parse Hindi-English lakh/thousand shorthand into numeric amounts."""
    df = khata.copy()
    df["amount"] = df["amount_text"].apply(_parse_amount_text)
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_ingest.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/ingest.py backend/tests/test_ingest.py
git commit -m "feat: add deterministic ingestion cleanup for tally and khata data"
```

---

## Task 4: Shared Claude Client + Agent 1 (Data Cleaning) (§7.1)

**Files:**
- Create: `backend/app/agents/claude_client.py`
- Create: `backend/app/agents/cleaning.py`
- Test: `backend/tests/test_agent_cleaning.py`

This is the first task that calls the real Claude API — per §9 of the spec, agents are tested against real responses, not mocked. Requires `ANTHROPIC_API_KEY` set in the environment before running these tests.

- [ ] **Step 1: Write `backend/app/agents/claude_client.py`**

```python
import os

from anthropic import Anthropic

_client = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def call_with_tool(system: str, user_message: str, tool_schema: dict) -> dict:
    """Send a single-tool request and return the tool_use input dict."""
    client = get_client()
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Claude did not return a tool_use block")
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_agent_cleaning.py
import os
import pytest
from app.agents.cleaning import clean_product_name

pytestmark = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


def test_dedupes_three_ambuja_cement_variants():
    result_a = clean_product_name("ambuja cem. (50 KG)")
    result_b = clean_product_name("AMBUJA CEMENT 50KG")

    assert result_a["brand"] == "Ambuja"
    assert result_a["name"] == result_b["name"]
    assert result_a["category"] == "Cement"
    assert result_a["variant"] == "50 KG Bag"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_cleaning.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.cleaning'`

- [ ] **Step 4: Write `backend/app/agents/cleaning.py`**

```python
from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You clean messy Indian building-materials inventory data for Gupta Building Materials.
Given one raw product name string exactly as it appears in a hand-maintained Excel sheet, return the
normalized product it refers to. Known brands include Ambuja, UltraTech, Asian Paints. Categories include
Cement, Steel, Pipes, Electrical, Paints, Hardware. HSN codes: Cement=2523, Steel=7213, Pipes=3917,
Electrical=8544, Paints=3208, Hardware=7318."""

TOOL_SCHEMA = {
    "name": "normalize_product",
    "description": "Return the normalized product for a raw inventory name",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Canonical product name, e.g. 'Ambuja Cement'"},
            "brand": {"type": "string"},
            "variant": {"type": "string", "description": "e.g. '50 KG Bag'"},
            "category": {"type": "string"},
            "hsn": {"type": "string"},
        },
        "required": ["name", "brand", "variant", "category", "hsn"],
    },
}


def clean_product_name(raw_name: str) -> dict:
    return call_with_tool(SYSTEM_PROMPT, f"Raw product name: {raw_name!r}", TOOL_SCHEMA)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_agent_cleaning.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/claude_client.py backend/app/agents/cleaning.py backend/tests/test_agent_cleaning.py
git commit -m "feat: add Agent 1 (product name cleaning) via Claude structured tool use"
```

---

## Task 5: Complete Ingestion Pipeline — Agent 1 Integration, Load, Verify (§4.4, steps 3/4/5)

**Files:**
- Modify: `backend/app/data/ingest.py`
- Modify: `backend/tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
# add to backend/tests/test_ingest.py
import os
import pytest
from app.data.ingest import resolve_ambiguous_products, load, verify
from app.models import Product

pytestmark_agent = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


@pytestmark_agent
def test_resolve_ambiguous_products_collapses_name_variants():
    generate_all(seed=42)
    raw = extract()
    catalog = resolve_ambiguous_products(raw["stock"])
    ambuja_rows = [p for p in catalog if p["brand"] == "Ambuja"]
    assert len(ambuja_rows) == 1


def test_load_and_verify_populate_postgres(db):
    generate_all(seed=42)
    raw = extract()
    catalog = [{"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523"}]
    stats = load(db, catalog=catalog, tally=clean_tally_dates_and_amounts(raw["tally"]), khata=clean_khata_entries(raw["khata"]),
                 whatsapp=raw["whatsapp"], rates=raw["rates"])
    report = verify(db)
    assert report["products"] == stats["products"]
    assert db.query(Product).count() > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_ingest.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_ambiguous_products'`

- [ ] **Step 3: Add to `backend/app/data/ingest.py`**

```python
from app.agents.cleaning import clean_product_name
from app.models import Product, Customer, Supplier, SupplierRateCard, Invoice, CreditLedger, WhatsappMessage


def resolve_ambiguous_products(stock: pd.DataFrame) -> list[dict]:
    """Step 3 (§4.4): hand ambiguous product names to Agent 1, dedupe by (name, variant)."""
    seen = {}
    for raw_name in stock["product_name"].unique():
        cleaned = clean_product_name(raw_name)
        key = (cleaned["name"], cleaned["variant"])
        seen[key] = cleaned
    return list(seen.values())


def load(db, catalog: list[dict], tally: pd.DataFrame, khata: pd.DataFrame, whatsapp: list[dict], rates: pd.DataFrame) -> dict:
    """Step 4 (§4.4): insert into Postgres in dependency order."""
    products = []
    products_by_name = {}
    for entry in catalog:
        product = Product(name=entry["name"], brand=entry["brand"], category=entry["category"], unit="bag", hsn_code=entry["hsn"], current_stock=0)
        db.add(product)
        products.append(product)
        products_by_name[entry["name"]] = product
    db.flush()

    customers_by_name = {}
    for name in khata["customer_name"].unique():
        customer = Customer(name=name)
        db.add(customer)
        customers_by_name[name] = customer
    db.flush()

    for _, row in khata.iterrows():
        db.add(CreditLedger(
            customer_id=customers_by_name[row["customer_name"]].id,
            date=pd.Timestamp.now(),
            type="debit",
            amount=row["amount"] or 0,
            note=row.get("note"),
            source_raw=f"{row['date_text']} {row['amount_text']}",
        ))

    for _, row in tally.iterrows():
        matched_product = products_by_name.get(row.get("product_name"))
        db.add(Invoice(
            date=row["date"], amount=row["amount"], gst_number=row.get("gst_number"), payment_status="unknown",
            product_id=matched_product.id if matched_product else None,
            qty=row.get("qty"),
        ))

    for msg in whatsapp:
        db.add(WhatsappMessage(raw_text=msg["raw_text"], received_at=pd.Timestamp(msg["timestamp"])))

    suppliers_by_name = {}
    for name in rates["supplier_name"].unique():
        supplier = Supplier(name=name)
        db.add(supplier)
        suppliers_by_name[name] = supplier
    db.flush()

    db.commit()
    return {"products": len(products), "customers": len(customers_by_name), "invoices": len(tally), "whatsapp": len(whatsapp)}


def verify(db) -> dict:
    """Step 5 (§4.4): row-count check against Postgres, printed live during the walkthrough."""
    return {
        "products": db.query(Product).count(),
        "customers": db.query(Customer).count(),
        "invoices": db.query(Invoice).count(),
        "credit_entries": db.query(CreditLedger).count(),
        "whatsapp_messages": db.query(WhatsappMessage).count(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_ingest.py -v`
Expected: PASS

- [ ] **Step 5: Add a runnable CLI entrypoint at the bottom of `backend/app/data/ingest.py`** (this is what gets run live in class per §4.4/§11)

```python
if __name__ == "__main__":
    from app.db import SessionLocal

    print("Step 1/5: extract...")
    raw = extract()
    print(f"  → stock: {len(raw['stock'])} rows, tally: {len(raw['tally'])} rows, khata: {len(raw['khata'])} rows")

    print("Step 2/5: deterministic cleanup...")
    tally_clean = clean_tally_dates_and_amounts(raw["tally"])
    khata_clean = clean_khata_entries(raw["khata"])

    print("Step 3/5: resolving ambiguous product names via Agent 1...")
    catalog = resolve_ambiguous_products(raw["stock"])
    print(f"  → {raw['stock']['product_name'].nunique()} raw names collapsed to {len(catalog)} products")

    print("Step 4/5: loading into Postgres...")
    db = SessionLocal()
    stats = load(db, catalog=catalog, tally=tally_clean, khata=khata_clean, whatsapp=raw["whatsapp"], rates=raw["rates"])
    print(f"  → loaded {stats}")

    print("Step 5/5: verifying...")
    print(f"  → {verify(db)}")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/data/ingest.py backend/tests/test_ingest.py
git commit -m "feat: complete ingestion pipeline with Agent 1 resolution, load, and verify steps"
```

---

## Task 6: Pydantic Schemas + Products/Customers/Suppliers CRUD Endpoints (§5)

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/products.py`
- Create: `backend/app/routers/customers.py`
- Create: `backend/app/routers/suppliers.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_products_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_products_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_products():
    response = client.post("/products", json={
        "name": "Ambuja Cement", "brand": "Ambuja", "category": "Cement",
        "unit": "bag", "hsn_code": "2523", "current_stock": 340,
    })
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Ambuja Cement"

    listed = client.get("/products").json()
    assert any(p["name"] == "Ambuja Cement" for p in listed)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_products_api.py -v`
Expected: FAIL — `404 Not Found` (route doesn't exist yet)

- [ ] **Step 3: Write `backend/app/schemas.py`**

```python
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
    phone: str | None = None
    area: str | None = None


class CustomerOut(CustomerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SupplierIn(BaseModel):
    name: str
    contact: str | None = None


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
    delivery_address: str | None = None
    delivery_time: str | None = None
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    status: str
    source: str
    credit_risk: dict | None = None
```

- [ ] **Step 4: Write `backend/app/routers/products.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Product
from app.schemas import ProductIn, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()
```

- [ ] **Step 5: Write `backend/app/routers/customers.py`** (same pattern as products)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer
from app.schemas import CustomerIn, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return db.query(Customer).filter_by(id=customer_id).first()
```

- [ ] **Step 6: Write `backend/app/routers/suppliers.py`** (same pattern, plus rate cards read)

```python
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
    return [{"supplier_id": c.supplier_id, "product_id": c.product_id, "price": float(c.price) if c.price else None,
             "unit": c.unit, "date": c.date.isoformat(), "discount_tier_text": c.discount_tier_text} for c in cards]
```

- [ ] **Step 7: Wire routers into `backend/app/main.py`**

```python
from fastapi import FastAPI

from app.routers import products, customers, suppliers

app = FastAPI(title="Gupta Building Materials API")

app.include_router(products.router)
app.include_router(customers.router)
app.include_router(suppliers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && pytest tests/test_products_api.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/products.py backend/app/routers/customers.py backend/app/routers/suppliers.py backend/app/main.py backend/tests/test_products_api.py
git commit -m "feat: add products, customers, suppliers CRUD endpoints"
```

---

## Task 7: Agent 3 (Credit Risk Analyzer) (§7.3)

**Files:**
- Create: `backend/app/agents/credit_risk.py`
- Test: `backend/tests/test_agent_credit_risk.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_agent_credit_risk.py
import os
import pytest
from app.agents.credit_risk import assess_credit_risk

pytestmark = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


def test_flags_high_risk_for_vinod_builders_golden_path():
    result = assess_credit_risk(
        customer_name="Vinod Builders",
        overdue_amount=410000,
        overdue_days=82,
        new_order_amount=350000,
    )
    assert result["risk_level"] == "high"
    assert result["total_exposure"] == 760000
    assert "advance" in result["recommendation"].lower() or "cash" in result["recommendation"].lower()


def test_low_risk_for_customer_with_no_overdue():
    result = assess_credit_risk(
        customer_name="Sharma Contractor",
        overdue_amount=0,
        overdue_days=0,
        new_order_amount=50000,
    )
    assert result["risk_level"] == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_credit_risk.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.credit_risk'`

- [ ] **Step 3: Write `backend/app/agents/credit_risk.py`**

```python
from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You are a credit risk analyst for Gupta Building Materials, an Indore MSME distributor.
Given a customer's overdue amount, days overdue, and a new incoming order amount, assess the risk of
extending further credit and recommend an action (e.g. dispatch as usual, require advance payment,
cash-on-delivery only). Risk thresholds: total exposure above ₹5,00,000 or over 60 days overdue is
elevated risk."""

TOOL_SCHEMA = {
    "name": "assess_risk",
    "description": "Assess credit risk for a new order",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "total_exposure": {"type": "number"},
            "recommendation": {"type": "string"},
        },
        "required": ["risk_level", "total_exposure", "recommendation"],
    },
}


def assess_credit_risk(customer_name: str, overdue_amount: float, overdue_days: int, new_order_amount: float) -> dict:
    user_message = (
        f"Customer: {customer_name}\n"
        f"Overdue amount: ₹{overdue_amount:,.0f}\n"
        f"Days overdue: {overdue_days}\n"
        f"New order amount: ₹{new_order_amount:,.0f}\n"
        f"Total exposure if dispatched: ₹{overdue_amount + new_order_amount:,.0f}"
    )
    return call_with_tool(SYSTEM_PROMPT, user_message, TOOL_SCHEMA)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_agent_credit_risk.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/credit_risk.py backend/tests/test_agent_credit_risk.py
git commit -m "feat: add Agent 3 (credit risk analyzer) via Claude structured tool use"
```

---

## Task 8: Orders + Credit Endpoints, Wiring Agent 3 into Order Creation (§5)

**Files:**
- Create: `backend/app/routers/orders.py`
- Create: `backend/app/routers/credit.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_orders_api.py`
- Test: `backend/tests/test_credit_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_orders_api.py
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Customer, Product, CreditLedger
from datetime import datetime, timedelta

client = TestClient(app)
pytestmark = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


def test_creating_order_for_overdue_customer_returns_risk_flag(db):
    customer = Customer(name="Vinod Builders")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow() - timedelta(days=82), type="debit", amount=410000))
    db.commit()

    product = Product(name="TMT Sariya 10mm", brand="Generic", category="Steel", unit="ton", hsn_code="7213", current_stock=10)
    db.add(product)
    db.commit()

    response = client.post("/orders", json={
        "customer_id": customer.id, "source": "whatsapp",
        "items": [{"product_id": product.id, "qty": 2, "unit_price": 175000}],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["credit_risk"]["risk_level"] in ("medium", "high")
```

```python
# backend/tests/test_credit_api.py
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models import Customer, CreditLedger

client = TestClient(app)


def test_credit_ledger_returns_aging(db):
    customer = Customer(name="Sharma Contractor")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow() - timedelta(days=30), type="debit", amount=100000))
    db.commit()

    response = client.get(f"/credit/{customer.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["total_outstanding"] == 100000
    assert body["oldest_days_overdue"] >= 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_orders_api.py tests/test_credit_api.py -v`
Expected: FAIL — `404 Not Found`

- [ ] **Step 3: Write `backend/app/routers/credit.py`**

```python
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
    return assess_credit_risk(customer.name, aging["total_outstanding"], aging["oldest_days_overdue"], new_order_amount)
```

- [ ] **Step 4: Write `backend/app/routers/orders.py`**

```python
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

    return {"id": order.id, "customer_id": order.customer_id, "status": order.status, "source": order.source, "credit_risk": risk}


@router.get("")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [{"id": o.id, "customer_id": o.customer_id, "status": o.status, "source": o.source} for o in orders]
```

- [ ] **Step 5: Wire into `backend/app/main.py`**

```python
from app.routers import products, customers, suppliers, orders, credit

app.include_router(orders.router)
app.include_router(credit.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_orders_api.py tests/test_credit_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/orders.py backend/app/routers/credit.py backend/app/main.py backend/tests/test_orders_api.py backend/tests/test_credit_api.py
git commit -m "feat: add orders + credit endpoints, wire Agent 3 credit-risk check into order creation"
```

---

## Task 9: Agent 2 (WhatsApp Order Parser) + `/agents/parse-order` Endpoint (§7.2)

**Files:**
- Create: `backend/app/agents/order_parser.py`
- Create: `backend/app/routers/agents.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_agent_order_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_agent_order_parser.py
import os
import pytest
from app.agents.order_parser import parse_whatsapp_order

pytestmark = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


def test_parses_fixed_golden_path_message():
    text = "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site pe bhijwa dena"
    result = parse_whatsapp_order(text)

    item_names = [item["product_hint"].lower() for item in result["items"]]
    assert any("sariya" in name or "tmt" in name for name in item_names)
    assert any("pipe" in name for name in item_names)
    assert any("cement" in name or "ultratech" in name for name in item_names)
    assert "sharma" in result["delivery_address"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_order_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.order_parser'`

- [ ] **Step 3: Write `backend/app/agents/order_parser.py`**

```python
from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You parse Hinglish WhatsApp order messages from contractors for Gupta Building Materials.
Extract every item with its quantity and unit, the delivery address, and the delivery time. Common
abbreviations: 'sariya' = TMT steel bars, 'cem'/'cement' = cement, 'bhej do'/'bhijwa dena' = please deliver.
Quantities may appear before or after the item name."""

TOOL_SCHEMA = {
    "name": "extract_order",
    "description": "Extract a structured order from a raw WhatsApp message",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_hint": {"type": "string", "description": "e.g. 'TMT Sariya 10mm'"},
                        "qty": {"type": "number"},
                        "unit": {"type": "string"},
                    },
                    "required": ["product_hint", "qty", "unit"],
                },
            },
            "delivery_address": {"type": "string"},
            "delivery_time": {"type": "string"},
        },
        "required": ["items", "delivery_address", "delivery_time"],
    },
}


def parse_whatsapp_order(raw_text: str) -> dict:
    return call_with_tool(SYSTEM_PROMPT, raw_text, TOOL_SCHEMA)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_agent_order_parser.py -v`
Expected: PASS

- [ ] **Step 5: Write `backend/app/routers/agents.py`** (parse-order endpoint; demand-forecast route added in Task 10)

```python
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.order_parser import parse_whatsapp_order

router = APIRouter(prefix="/agents", tags=["agents"])


class ParseOrderRequest(BaseModel):
    raw_text: str


@router.post("/parse-order")
def parse_order(payload: ParseOrderRequest):
    return parse_whatsapp_order(payload.raw_text)
```

- [ ] **Step 6: Wire into `backend/app/main.py`**

```python
from app.routers import products, customers, suppliers, orders, credit, agents

app.include_router(agents.router)
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/order_parser.py backend/app/routers/agents.py backend/app/main.py backend/tests/test_agent_order_parser.py
git commit -m "feat: add Agent 2 (WhatsApp order parser) and /agents/parse-order endpoint"
```

---

## Task 10: Agent 4 (Demand Forecast) + `/agents/demand-forecast` Endpoint (§7.4)

**Files:**
- Create: `backend/app/agents/demand_forecast.py`
- Modify: `backend/app/routers/agents.py`
- Test: `backend/tests/test_agent_demand_forecast.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_agent_demand_forecast.py
import os
import pytest
from app.agents.demand_forecast import forecast_demand

pytestmark = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


def test_detects_monsoon_seasonality_for_cement():
    monthly_sales = {
        "2025-04": 300, "2025-05": 350, "2025-06": 520, "2025-07": 610,
        "2025-08": 400, "2026-04": 320, "2026-05": 360, "2026-06": 540,
    }
    result = forecast_demand(product_name="UltraTech Cement", current_stock=450, monthly_sales=monthly_sales)

    assert result["predicted_30_day_demand"] > 450
    assert "monsoon" in result["reasoning"].lower() or "season" in result["reasoning"].lower()
    assert result["reorder_qty"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_demand_forecast.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.demand_forecast'`

- [ ] **Step 3: Write `backend/app/agents/demand_forecast.py`**

```python
from app.agents.claude_client import call_with_tool

SYSTEM_PROMPT = """You forecast 30-day demand for a building-materials distributor in Indore, India.
Given a product's monthly sales history and current stock, detect seasonal patterns (e.g. cement demand
rises before monsoon, paint demand rises around Diwali) and recommend a reorder quantity to avoid a
stockout in the next 30 days."""

TOOL_SCHEMA = {
    "name": "forecast",
    "description": "Forecast 30-day demand and recommend a reorder quantity",
    "input_schema": {
        "type": "object",
        "properties": {
            "predicted_30_day_demand": {"type": "number"},
            "reorder_qty": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["predicted_30_day_demand", "reorder_qty", "reasoning"],
    },
}


def forecast_demand(product_name: str, current_stock: int, monthly_sales: dict) -> dict:
    history_lines = "\n".join(f"{month}: {qty}" for month, qty in sorted(monthly_sales.items()))
    user_message = f"Product: {product_name}\nCurrent stock: {current_stock}\nMonthly sales history:\n{history_lines}"
    return call_with_tool(SYSTEM_PROMPT, user_message, TOOL_SCHEMA)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_agent_demand_forecast.py -v`
Expected: PASS

- [ ] **Step 5: Add the endpoint to `backend/app/routers/agents.py`**

Monthly history is read from `Invoice` (the 2-year Tally history loaded in Task 5), not from `Order`/`OrderItem` — those only ever contain orders placed live during rehearsal or class, and would never have the 2 years of seasonal history the forecast needs to detect anything (§4.2).

```python
from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.demand_forecast import forecast_demand
from app.db import get_db
from app.models import Product, Invoice
from collections import defaultdict


@router.get("/demand-forecast/{product_id}")
def demand_forecast(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=product_id).first()
    rows = db.query(Invoice.date, Invoice.qty).filter(Invoice.product_id == product_id).all()

    monthly = defaultdict(int)
    for invoice_date, qty in rows:
        monthly[invoice_date.strftime("%Y-%m")] += qty or 0
    return forecast_demand(product.name, product.current_stock, dict(monthly))
```

- [ ] **Step 6: Add a test confirming the endpoint reads seasonal history correctly**

```python
# add to backend/tests/test_agent_demand_forecast.py
import os
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.models import Product, Invoice

client = TestClient(app)
pytestmark_api = pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="requires real API key")


@pytestmark_api
def test_demand_forecast_endpoint_uses_invoice_history(db):
    product = Product(name="UltraTech Cement", brand="UltraTech", category="Cement", unit="bag", hsn_code="2523", current_stock=450)
    db.add(product)
    db.commit()

    for month, qty in [(4, 300), (5, 350), (6, 900), (7, 950)]:
        db.add(Invoice(product_id=product.id, date=datetime(2026, month, 15), amount=qty * 380, qty=qty))
    db.commit()

    response = client.get(f"/agents/demand-forecast/{product.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["predicted_30_day_demand"] > 0
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && export ANTHROPIC_API_KEY=<your key> && pytest tests/test_agent_demand_forecast.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/agents/demand_forecast.py backend/app/routers/agents.py backend/tests/test_agent_demand_forecast.py
git commit -m "feat: add Agent 4 (demand forecast) and /agents/demand-forecast endpoint"
```

---

## Task 11: Frontend Scaffolding (§6)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/api.js`
- Create: `frontend/src/App.jsx`
- Test: `frontend/src/App.test.jsx`

No React Router — with only 4 tabs and no deep-linking requirement for a live demo, a simple tab-state `App.jsx` is simpler than adding a router dependency (YAGNI).

- [ ] **Step 1: Scaffold the Vite project**

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Write `frontend/vite.config.js`**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
})
```

```js
// frontend/src/setupTests.js
import '@testing-library/jest-dom'
```

- [ ] **Step 3: Write `frontend/src/api.js`**

```js
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(`Request to ${path} failed: ${response.status}`)
  return response.json()
}

export const api = {
  getProducts: () => request('/products'),
  getOrders: () => request('/orders'),
  getSuppliers: () => request('/suppliers'),
  getRateCards: () => request('/suppliers/rate-cards'),
  getCredit: (customerId) => request(`/credit/${customerId}`),
  parseOrder: (rawText) => request('/agents/parse-order', { method: 'POST', body: JSON.stringify({ raw_text: rawText }) }),
}
```

- [ ] **Step 4: Write the failing test for `App.jsx`**

```jsx
// frontend/src/App.test.jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders all four tabs and defaults to Overview', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Orders' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Customers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Suppliers' })).toBeInTheDocument()
  })

  it('switches tabs on click', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('tab', { name: 'Orders' }))
    expect(screen.getByRole('tab', { name: 'Orders' })).toHaveAttribute('aria-selected', 'true')
  })
})
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd frontend && npx vitest run`
Expected: FAIL — `App` doesn't render tabs yet (default Vite template)

- [ ] **Step 6: Write `frontend/src/App.jsx`**

```jsx
import { useState } from 'react'
import Overview from './pages/Overview'
import Orders from './pages/Orders'
import Customers from './pages/Customers'
import Suppliers from './pages/Suppliers'

const TABS = {
  Overview: Overview,
  Orders: Orders,
  Customers: Customers,
  Suppliers: Suppliers,
}

export default function App() {
  const [activeTab, setActiveTab] = useState('Overview')
  const ActiveComponent = TABS[activeTab]

  return (
    <div>
      <nav role="tablist">
        {Object.keys(TABS).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>
      <main>
        <ActiveComponent />
      </main>
    </div>
  )
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd frontend && npx vitest run`
Expected: PASS (pages don't exist yet — stub them minimally to unblock this test)

```jsx
// frontend/src/pages/Overview.jsx (stub, filled in Task 12)
export default function Overview() { return <div>Overview</div> }
```
```jsx
// frontend/src/pages/Orders.jsx (stub, filled in Task 13)
export default function Orders() { return <div>Orders</div> }
```
```jsx
// frontend/src/pages/Customers.jsx (stub, filled in Task 14)
export default function Customers() { return <div>Customers</div> }
```
```jsx
// frontend/src/pages/Suppliers.jsx (stub, filled in Task 15)
export default function Suppliers() { return <div>Suppliers</div> }
```

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/src/main.jsx frontend/src/api.js frontend/src/App.jsx frontend/src/App.test.jsx frontend/src/setupTests.js frontend/src/pages/
git commit -m "feat: scaffold React dashboard with 4-tab navigation"
```

---

## Task 12: Overview Page (§6)

**Files:**
- Modify: `frontend/src/pages/Overview.jsx`
- Test: `frontend/src/pages/Overview.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// frontend/src/pages/Overview.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Overview from './Overview'
import { api } from '../api'

vi.mock('../api')

describe('Overview', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', current_stock: 12 }])
    api.getOrders.mockResolvedValue([{ id: 1, customer_id: 1, status: 'pending' }])
  })

  it('shows low-stock alert when a product is under threshold', async () => {
    render(<Overview />)
    await waitFor(() => expect(screen.getByText(/Ambuja Cement/)).toBeInTheDocument())
    expect(screen.getByText(/low stock/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Overview.test.jsx`
Expected: FAIL — stub renders only "Overview"

- [ ] **Step 3: Write `frontend/src/pages/Overview.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

const LOW_STOCK_THRESHOLD = 50

export default function Overview() {
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])

  useEffect(() => {
    api.getProducts().then(setProducts)
    api.getOrders().then(setOrders)
  }, [])

  const lowStock = products.filter((p) => p.current_stock < LOW_STOCK_THRESHOLD)

  return (
    <section>
      <h2>Overview</h2>
      <p>{products.length} products, {orders.length} orders today</p>
      {lowStock.length > 0 && (
        <div role="alert">
          Low stock alert:
          <ul>
            {lowStock.map((p) => (
              <li key={p.id}>{p.name} — {p.current_stock} left</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Overview.test.jsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Overview.jsx frontend/src/pages/Overview.test.jsx
git commit -m "feat: add Overview dashboard page with low-stock alerts"
```

---

## Task 13: Orders Page + Live WhatsApp Parser Box (§6)

**Files:**
- Modify: `frontend/src/pages/Orders.jsx`
- Test: `frontend/src/pages/Orders.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// frontend/src/pages/Orders.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Orders from './Orders'
import { api } from '../api'

vi.mock('../api')

describe('Orders', () => {
  beforeEach(() => {
    api.getOrders.mockResolvedValue([])
    api.parseOrder.mockResolvedValue({
      items: [{ product_hint: 'TMT Sariya 10mm', qty: 2, unit: 'ton' }],
      delivery_address: 'Sharma site',
      delivery_time: 'tomorrow morning',
    })
  })

  it('parses a pasted WhatsApp message and shows the structured result', async () => {
    render(<Orders />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), {
      target: { value: 'bhai 10mm sariya 2 ton kal subah Sharma site pe' },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByText(/Sharma site/)).toBeInTheDocument())
    expect(screen.getByText(/TMT Sariya 10mm/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Orders.test.jsx`
Expected: FAIL — stub has no form

- [ ] **Step 3: Write `frontend/src/pages/Orders.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [rawText, setRawText] = useState('')
  const [parsed, setParsed] = useState(null)

  useEffect(() => {
    api.getOrders().then(setOrders)
  }, [])

  const handleParse = async () => {
    const result = await api.parseOrder(rawText)
    setParsed(result)
  }

  return (
    <section>
      <h2>Orders</h2>
      <div>
        <label htmlFor="whatsapp-input">Paste WhatsApp message</label>
        <textarea id="whatsapp-input" value={rawText} onChange={(e) => setRawText(e.target.value)} />
        <button onClick={handleParse}>Parse order</button>
      </div>
      {parsed && (
        <div>
          <p>Delivery: {parsed.delivery_address} — {parsed.delivery_time}</p>
          <ul>
            {parsed.items.map((item, i) => (
              <li key={i}>{item.product_hint}: {item.qty} {item.unit}</li>
            ))}
          </ul>
        </div>
      )}
      <ul>
        {orders.map((o) => (
          <li key={o.id}>Order #{o.id} — {o.status}</li>
        ))}
      </ul>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Orders.test.jsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Orders.jsx frontend/src/pages/Orders.test.jsx
git commit -m "feat: add Orders page with live WhatsApp order parser"
```

---

## Task 14: Customers/Credit Page (§6)

**Files:**
- Modify: `frontend/src/pages/Customers.jsx`
- Test: `frontend/src/pages/Customers.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// frontend/src/pages/Customers.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Customers from './Customers'
import { api } from '../api'

vi.mock('../api')

describe('Customers', () => {
  it('shows a high-risk badge for a customer over 60 days overdue', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 410000, oldest_days_overdue: 82 })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders' }]} />)

    await waitFor(() => expect(screen.getByText('Vinod Builders')).toBeInTheDocument())
    expect(screen.getByText(/high risk/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Customers.test.jsx`
Expected: FAIL — stub ignores props, no badge

- [ ] **Step 3: Write `frontend/src/pages/Customers.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

function riskBadge(agingDays) {
  if (agingDays > 60) return 'High risk'
  if (agingDays > 30) return 'Medium risk'
  return 'Low risk'
}

export default function Customers({ customers = [] }) {
  const [aging, setAging] = useState({})

  useEffect(() => {
    customers.forEach((c) => {
      api.getCredit(c.id).then((result) => setAging((prev) => ({ ...prev, [c.id]: result })))
    })
  }, [customers])

  return (
    <section>
      <h2>Customers</h2>
      <table>
        <tbody>
          {customers.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{aging[c.id] ? `₹${aging[c.id].total_outstanding.toLocaleString()}` : '—'}</td>
              <td>{aging[c.id] ? riskBadge(aging[c.id].oldest_days_overdue) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Customers.test.jsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Customers.jsx frontend/src/pages/Customers.test.jsx
git commit -m "feat: add Customers/Credit page with aging-based risk badges"
```

---

## Task 15: Suppliers Page (§6)

**Files:**
- Modify: `frontend/src/pages/Suppliers.jsx`
- Test: `frontend/src/pages/Suppliers.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// frontend/src/pages/Suppliers.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Suppliers from './Suppliers'
import { api } from '../api'

vi.mock('../api')

describe('Suppliers', () => {
  it('lists rate cards grouped by product', async () => {
    api.getRateCards.mockResolvedValue([
      { supplier_id: 1, product_id: 1, price: 380, unit: 'bag', date: '2026-06-01', discount_tier_text: '5% above 500 bags' },
    ])
    render(<Suppliers />)
    await waitFor(() => expect(screen.getByText(/380/)).toBeInTheDocument())
    expect(screen.getByText(/5% above 500 bags/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Suppliers.test.jsx`
Expected: FAIL — stub has no table

- [ ] **Step 3: Write `frontend/src/pages/Suppliers.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Suppliers() {
  const [rateCards, setRateCards] = useState([])

  useEffect(() => {
    api.getRateCards().then(setRateCards)
  }, [])

  return (
    <section>
      <h2>Suppliers</h2>
      <table>
        <thead>
          <tr><th>Supplier</th><th>Product</th><th>Price</th><th>Discount</th></tr>
        </thead>
        <tbody>
          {rateCards.map((c, i) => (
            <tr key={i}>
              <td>{c.supplier_id}</td>
              <td>{c.product_id}</td>
              <td>{c.price ?? 'call for rate'} / {c.unit}</td>
              <td>{c.discount_tier_text || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Suppliers.test.jsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Suppliers.jsx frontend/src/pages/Suppliers.test.jsx
git commit -m "feat: add Suppliers page with rate card comparison table"
```

---

## Task 16: Serve React Build from FastAPI + Deploy to Railway (§8)

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/railway.json`
- Create: `backend/Procfile`
- Test: manual curl verification (no pytest — this is infra, not application logic)

- [ ] **Step 1: Build the React app**

```bash
cd frontend && npm run build
```

Expected: produces `frontend/dist/`

- [ ] **Step 2: Mount the built frontend as static files in `backend/app/main.py`**

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
```

Place this mount **after** all `app.include_router(...)` calls — StaticFiles with `html=True` is a catch-all and must not shadow API routes.

- [ ] **Step 3: Write `backend/Procfile`**

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 4: Write `backend/railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": { "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT", "restartPolicyType": "ON_FAILURE" }
}
```

- [ ] **Step 5: Provision Railway project and Postgres**

```bash
railway login
railway init
railway add --plugin postgresql
```

- [ ] **Step 6: Set environment variables**

```bash
railway variables set ANTHROPIC_API_KEY=<your key>
```

`DATABASE_URL` is set automatically by the Postgres plugin — confirm with `railway variables`.

- [ ] **Step 7: Deploy**

```bash
railway up
```

- [ ] **Step 8: Run migrations against the Railway Postgres instance**

```bash
railway run python -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"
railway run python -m app.data.ingest
```

- [ ] **Step 9: Verify the deployed health check and one API route**

```bash
railway domain  # prints the deployed URL
curl https://<your-app>.up.railway.app/health
curl https://<your-app>.up.railway.app/products
```

Expected: `{"status": "ok"}` and a non-empty product list.

- [ ] **Step 10: Commit**

```bash
git add backend/Procfile backend/railway.json backend/app/main.py
git commit -m "feat: serve React build from FastAPI and add Railway deploy config"
```

---

## Task 17: End-to-End Golden-Path Rehearsal (§9)

This task has no code changes — it's the rehearsal specified in the spec's Verification Plan, run against the **deployed** Railway URL, not localhost. Do this once everything above is deployed.

**Files:** none (verification only)

- [ ] **Step 1: Verify Vinod Builders credit-risk golden path**

```bash
BASE=https://<your-app>.up.railway.app
curl -s "$BASE/customers" | grep -i "vinod builders"
```

Note the `customer_id`, then:

```bash
curl -s -X POST "$BASE/orders" -H 'Content-Type: application/json' -d '{
  "customer_id": <vinod_id>, "source": "whatsapp",
  "items": [{"product_id": 1, "qty": 2, "unit_price": 175000}]
}' | python3 -m json.tool
```

Expected: response includes `"credit_risk": {"risk_level": "high", ...}`.

- [ ] **Step 2: Verify the fixed WhatsApp message golden path**

```bash
curl -s -X POST "$BASE/agents/parse-order" -H 'Content-Type: application/json' -d '{
  "raw_text": "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site pe bhijwa dena"
}' | python3 -m json.tool
```

Expected: 3 items extracted (sariya, pipe, cement), delivery address mentions Sharma site.

- [ ] **Step 3: Verify the monsoon demand-forecast golden path**

```bash
curl -s "$BASE/agents/demand-forecast/<ultratech_cement_product_id>" | python3 -m json.tool
```

Expected: `reasoning` mentions monsoon/seasonal demand, `reorder_qty` > 0.

- [ ] **Step 4: Open the dashboard in a browser and click through all 4 tabs**

Visit `https://<your-app>.up.railway.app/` — confirm Overview, Orders, Customers, and Suppliers all load real data with no console errors.

- [ ] **Step 5: Record actual response values from Steps 1–3**

Write down the exact numbers returned (exposure amount, risk level, forecast quantity) — Task 18's lecture script quotes these verbatim so the presenter isn't caught off guard by a number that doesn't match what's rehearsed here.

---

## Task 18: Write the Lecture Script Deliverable (§11)

**Files:**
- Create: `docs/lecture-script.md`

This is the last task, written only after Task 17's rehearsal has produced real numbers to quote. Fill in the `(from Task 17 rehearsal)` markers below with the actual values you recorded — do not invent numbers, and do not leave the markers unfilled.

- [ ] **Step 1: Write the opening narrative section**

```markdown
# Lecture Script — Gupta Building Materials FDE Masterclass

## Opening Narrative (0:00–0:15, no code shown)

> "Rajesh Gupta runs a ₹12 crore building materials business out of Indore — and he runs it from
> memory, a notebook, and WhatsApp. Six functions of this business — inventory, billing, credit,
> orders, delivery, suppliers — live in six places that don't talk to each other. Last month, when
> Rajesh was hospitalized for 4 days, his sons discovered nobody else knew which payments were due.
> They double-ordered 200 bags of cement because nobody checked the register.
>
> This is not a hypothetical. This is India's ₹54 lakh crore MSME sector. And it's exactly the kind
> of mess a Forward Deployed Engineer walks into on day one.
>
> Over the next 3 hours we're going to do three things: unify 5 messy data sources into one database,
> live, in front of you. Walk through the API and dashboard that sits on top of it. And live-code four
> AI agents that turn that unified data into decisions Rajesh's sons can act on without him."
```

- [ ] **Step 2: Write the Phase 1 script (data unification, live run)**

```markdown
## Phase 1 — Data Unification, Live (0:15–1:00)

Run `python -m app.data.ingest` on screen. Narrate each printed step as it appears:

**Step 1/5 (Extract):** "We're reading five raw files exactly as they'd exist at a real distributor —
an Excel stock register with 3 sheets, a Tally CSV export, a digitized khata, WhatsApp order JSON, and
supplier rate cards. Nothing cleaned yet."

**Step 2/5 (Deterministic cleanup):** "Some messiness a script can just fix — mixed date formats,
₹ symbols, 'CASH' rows. No judgment calls here, so no AI needed yet."

**Step 3/5 (Agent 1 — the wow moment):** "Here's where regex gives up. 'ambuja cem. (50 KG)',
'AMBUJA CEMENT 50KG', and 'Ambuja Cement 50kg' are the same product, but no fixed rule catches all
three spellings reliably. Watch the count drop as Agent 1 resolves each one." Point at the printed
`{raw count} raw names collapsed to {clean count} products` line — read the actual numbers off the
screen, don't pre-state them.

**Step 4/5 (Load):** "Now it lands in Postgres — one unified schema instead of six islands."

**Step 5/5 (Verify):** "And we confirm it landed: read the row counts off the screen."
```

- [ ] **Step 3: Write the Phase 2 script (backend/frontend walkthrough)**

```markdown
## Phase 2 — Backend + Frontend Walkthrough (1:00–1:45)

Open the deployed dashboard URL first — let the audience see the working system before the code.

1. **Overview tab** — "Real-time stock, today's orders, low-stock alerts. This is the phone screen
   Arjun opens every morning instead of asking his father."
2. Switch to code: `backend/app/routers/orders.py` — walk through `create_order`, pointing out that
   the credit-risk check (Agent 3) runs synchronously and is returned inline, not as an afterthought.
3. **Customers tab** — point at the risk badges, then show `backend/app/routers/credit.py`'s
   `compute_aging` function — "this is deterministic math, not AI. We only call Claude once we have
   real aging numbers to reason over."
4. **Suppliers tab** — briefly, rate card comparison, `backend/app/routers/suppliers.py`.
```

- [ ] **Step 4: Write the Phase 3 script (live agent coding)**

```markdown
## Phase 3 — Live-Coded AI Agents (1:45–2:50)

For each agent: state the problem, open a blank file, type from the tested reference in
`backend/app/agents/`, run the real test against it, watch it pass.

### Agent 2 — WhatsApp Order Parser (payoff: ~2:10)
Type `backend/app/agents/order_parser.py` live. Then paste the **fixed golden-path message**:
> "bhai 10mm sariya 2 ton pipe 1 inch 50 piece cement ultratech 100 bag kal subah 7 baje Sharma site
> pe bhijwa dena"
into the Orders tab's parse box. "This is the payoff — Hinglish text became a structured order with
zero manual entry." Read the extracted items and delivery address off the screen (from Task 17 Step 2 rehearsal).

### Agent 3 — Credit Risk (payoff: ~2:25)
Type `backend/app/agents/credit_risk.py` live. Place a new order for **Vinod Builders**. "This is the
payoff — Rajesh's sons would have had no way to know this without checking his notebook." State the
actual exposure and risk level: (from Task 17 Step 1 rehearsal).

### Agent 4 — Demand Forecast (payoff: ~2:45)
Type `backend/app/agents/demand_forecast.py` live. Call `/agents/demand-forecast` for UltraTech Cement.
"Monsoon is coming — watch the model catch a seasonal pattern humans usually catch too late." State the
actual predicted demand and reorder quantity: (from Task 17 Step 3 rehearsal).
```

- [ ] **Step 5: Write the timing table and closing**

```markdown
## Timing Checkpoints

| Phase | Budget | Cumulative | If behind at this mark... |
|---|---|---|---|
| Opening narrative | 15 min | 0:15 | skip the MSME-sector stat, keep the Rajesh story |
| Data unification (live run) | 45 min | 1:00 | skip narrating Steps 1–2 verbatim, jump to Agent 1 |
| Backend/frontend walkthrough | 45 min | 1:45 | cut the Suppliers tab walkthrough |
| Live agent coding | 65 min | 2:50 | cut Agent 4 to a code read-through, skip live typing |
| Closing | 10 min | 3:00 | — |

## Closing (2:50–3:00)

Show the Before/After table from the brief (`FDE_Masterclass_Problem_Statement.html` §7) side by side
with the live dashboard. "Every row in that 'Before' column was true this morning. Every row in 'After'
is running on a URL you just watched get built. That's the job: not the AI, the bridge from messy
reality to a system that thinks."
```

- [ ] **Step 6: Commit**

```bash
git add docs/lecture-script.md
git commit -m "docs: add full lecture script for the 3-hour live masterclass session"
```

---
