import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from app.agents.cleaning import clean_product_name
from app.data.catalog import UNIT_BY_CATEGORY
from app.models import Product, ProductVariant, Customer, Supplier, SupplierRateCard, Invoice, CreditLedger, WhatsappMessage

RAW_DIR = Path(__file__).parent / "raw"

_PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _parse_rate_price(price_text):
    if not isinstance(price_text, str):
        return None
    match = _PRICE_RE.search(price_text)
    return float(match.group(1)) if match else None


def extract() -> dict:
    """Step 1 (§4.4): read each raw file into a DataFrame, unchanged."""
    stock_sheets = pd.read_excel(RAW_DIR / "stock_register.xlsx", sheet_name=None)
    stock = pd.concat(stock_sheets.values(), ignore_index=True)
    tally = pd.read_csv(RAW_DIR / "tally_export.csv")
    # dtype pinned: a bare read_csv coerces customer_phone (e.g. "+919876543210") to int64,
    # silently stripping the "+91" prefix — force it to stay a string.
    khata = pd.read_csv(RAW_DIR / "khata_ledger.csv", dtype={"customer_phone": str})
    whatsapp = json.loads((RAW_DIR / "whatsapp_orders.json").read_text())
    # supplier_rates.csv's "contact" column ("FirstName - +91XXXXXXXXXX") is non-numeric,
    # so pandas infers it as object/str without help — verified empirically, no dtype pin needed.
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
    assert not df["date"].isna().any(), "some tally dates failed to parse — check date format assumptions"
    df["amount"] = (
        df["amount"].astype(str).str.replace("₹", "", regex=False).str.replace(",", "", regex=False).astype(float)
    )
    return df


_LAKH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*L", re.IGNORECASE)
_K_RE = re.compile(r"(\d+(?:\.\d+)?)\s*k", re.IGNORECASE)


def _parse_amount_text(text: str) -> Optional[float]:
    if not isinstance(text, str):
        return None
    lakh_match = _LAKH_RE.search(text)
    if lakh_match:
        try:
            return round(float(lakh_match.group(1)) * 100_000, 2)
        except ValueError:
            return None
    k_match = _K_RE.search(text)
    if k_match:
        try:
            return round(float(k_match.group(1)) * 1_000, 2)
        except ValueError:
            return None
    return None


def clean_khata_entries(khata: pd.DataFrame) -> pd.DataFrame:
    """Step 2 (§4.4): parse Hindi-English lakh/thousand shorthand into numeric amounts."""
    df = khata.copy()
    df["amount"] = df["amount_text"].apply(_parse_amount_text)
    assert df["amount"].notna().all(), "some khata amounts failed to parse — check amount_text format assumptions"
    return df


def resolve_ambiguous_products(stock: pd.DataFrame) -> list[dict]:
    """Step 3 (§4.4): hand ambiguous product names to Agent 1, dedupe by (name, variant)."""
    seen = {}
    qty_by_key = {}
    raw_names_by_key = {}
    unique_names = stock["product_name"].unique()
    for i, raw_name in enumerate(unique_names, 1):
        try:
            cleaned = clean_product_name(raw_name)
        except Exception as e:
            print(f"    ...skipping {raw_name!r}: {e}")
            continue
        key = (cleaned["name"], cleaned["variant"])
        seen[key] = cleaned
        raw_qty = stock.loc[stock["product_name"] == raw_name, "qty"].sum()
        qty_by_key[key] = qty_by_key.get(key, 0) + max(raw_qty, 0)  # negative qty is a data-entry error in the messy source, don't let it net out real stock
        raw_names_by_key.setdefault(key, []).append(raw_name)
        if i % 25 == 0 or i == len(unique_names):
            print(f"    ...{i}/{len(unique_names)} processed")

    result = []
    for key, cleaned in seen.items():
        result.append({**cleaned, "qty": qty_by_key[key], "raw_names": raw_names_by_key[key]})
    return result


def load(db, catalog: list[dict], tally: pd.DataFrame, khata: pd.DataFrame, whatsapp: list[dict], rates: pd.DataFrame) -> dict:
    """Step 4 (§4.4): insert into Postgres in dependency order."""
    products = []
    products_by_name = {}
    variant_count = 0
    for entry in catalog:
        product = Product(name=entry["name"], brand=entry["brand"], category=entry["category"], unit=UNIT_BY_CATEGORY.get(entry["category"], "piece"), hsn_code=entry["hsn"], current_stock=entry.get("qty", 0))
        db.add(product)
        products.append(product)
        products_by_name[entry["name"]] = product
    db.flush()

    for entry in catalog:
        product = products_by_name[entry["name"]]
        for raw_name in entry.get("raw_names", []):
            db.add(ProductVariant(raw_name=raw_name, product_id=product.id))
            variant_count += 1

    customers_by_name = {}
    phone_to_customer = {}
    for name in khata["customer_name"].unique():
        phone = khata.loc[khata["customer_name"] == name, "customer_phone"].iloc[0]
        customer = Customer(name=name, phone=phone)
        db.add(customer)
        customers_by_name[name] = customer
        if phone:
            phone_to_customer[phone] = customer
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
        matched_customer = phone_to_customer.get(msg.get("sender_phone"))
        db.add(WhatsappMessage(
            raw_text=msg["raw_text"],
            received_at=pd.Timestamp(msg["timestamp"]),
            customer_id=matched_customer.id if matched_customer else None,
        ))

    suppliers_by_name = {}
    for name in rates["supplier_name"].unique():
        contact = rates.loc[rates["supplier_name"] == name, "contact"].iloc[0]
        supplier = Supplier(name=name, contact=contact)
        db.add(supplier)
        suppliers_by_name[name] = supplier
    db.flush()

    for _, row in rates.iterrows():
        supplier = suppliers_by_name.get(row["supplier_name"])
        product = products_by_name.get(row["product_name"])
        if supplier and product:
            db.add(SupplierRateCard(
                supplier_id=supplier.id,
                product_id=product.id,
                price=_parse_rate_price(row["price"]),
                unit=row["unit"],
                date=pd.Timestamp(row["as_of_date"]),
                discount_tier_text=row.get("discount_text"),
            ))

    db.commit()
    return {
        "products": len(products),
        "customers": len(customers_by_name),
        "invoices": len(tally),
        "whatsapp": len(whatsapp),
        "suppliers": len(suppliers_by_name),
        "product_variants": variant_count,
    }


def verify(db) -> dict:
    """Step 5 (§4.4): row-count check against Postgres, printed live during the walkthrough."""
    return {
        "products": db.query(Product).count(),
        "customers": db.query(Customer).count(),
        "invoices": db.query(Invoice).count(),
        "credit_entries": db.query(CreditLedger).count(),
        "whatsapp_messages": db.query(WhatsappMessage).count(),
        "suppliers": db.query(Supplier).count(),
        "product_variants": db.query(ProductVariant).count(),
    }


if __name__ == "__main__":
    from app.db import SessionLocal, Base, engine

    print("Resetting schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("Step 1/5: extract...")
    raw = extract()
    print(f"  → stock: {len(raw['stock'])} rows, tally: {len(raw['tally'])} rows, khata: {len(raw['khata'])} rows")

    print("Step 2/5: deterministic cleanup...")
    tally_clean = clean_tally_dates_and_amounts(raw["tally"])
    khata_clean = clean_khata_entries(raw["khata"])

    print("Step 3/5: resolving ambiguous product names via Agent 1...")
    catalog = resolve_ambiguous_products(raw["stock"])
    print(f"  → {raw['stock']['product_name'].nunique()} raw names collapsed to {len(catalog)} products")

    db = SessionLocal()
    try:
        print("Step 4/5: loading into Postgres...")
        stats = load(db, catalog=catalog, tally=tally_clean, khata=khata_clean, whatsapp=raw["whatsapp"], rates=raw["rates"])
        print(f"  → loaded {stats}")

        print("Step 5/5: verifying...")
        print(f"  → {verify(db)}")
    finally:
        db.close()
