import pandas as pd
import pytest

from app.agents.claude_client import has_real_api_key
from app.data.generate_data import generate_all
from app.data.ingest import extract, clean_tally_dates_and_amounts, clean_khata_entries, resolve_ambiguous_products, load, verify
from app.models import Invoice, CreditLedger, Product, SupplierRateCard, Customer, WhatsappMessage, Supplier

pytestmark_agent = pytest.mark.skipif(not has_real_api_key(), reason="requires a real (non-placeholder) Anthropic API key")


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


def test_clean_khata_parses_date_text_into_real_dates():
    generate_all(seed=42)
    raw = extract()
    cleaned = clean_khata_entries(raw["khata"])
    assert cleaned["date"].notna().all()
    assert cleaned["date"].dtype.kind == "M"  # datetime64
    # no parsed date should be in the future
    from datetime import datetime
    assert (cleaned["date"] <= pd.Timestamp(datetime.utcnow()) + pd.Timedelta(days=1)).all()


@pytestmark_agent
def test_resolve_ambiguous_products_collapses_name_variants():
    # total_skus=20 (not the default 500) -- this test only needs to prove the
    # Ambuja dedup works, not process the full catalog. At 500 it's ~470
    # sequential real API calls (minutes, real cost, and more surface area for
    # a single slow/stuck call to eat the whole run) for the same assertion.
    generate_all(seed=42, total_skus=20)
    raw = extract()
    catalog = resolve_ambiguous_products(raw["stock"])
    ambuja_rows = [p for p in catalog if p["brand"] == "Ambuja"]
    assert len(ambuja_rows) == 1


def test_load_and_verify_populate_postgres(db):
    generate_all(seed=42)
    raw = extract()
    catalog = [{"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523", "qty": 100, "raw_names": ["Ambuja Cement 50kg", "AMBUJA CEMENT 50KG"]}]
    stats = load(db, catalog=catalog, tally=clean_tally_dates_and_amounts(raw["tally"]), khata=clean_khata_entries(raw["khata"]),
                 whatsapp=raw["whatsapp"], rates=raw["rates"])
    report = verify(db)
    assert report["products"] == stats["products"]
    assert db.query(Product).count() > 0
    assert report["product_variants"] == 2  # matches the 2 raw_names in the fake catalog entry


def test_load_populates_customer_phone_from_khata(db):
    generate_all(seed=42)
    raw = extract()
    catalog = [{"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523", "qty": 100, "raw_names": ["x"]}]
    load(db, catalog=catalog, tally=clean_tally_dates_and_amounts(raw["tally"]), khata=clean_khata_entries(raw["khata"]),
         whatsapp=raw["whatsapp"], rates=raw["rates"])
    vinod = db.query(Customer).filter_by(name="Vinod Builders").first()
    assert vinod.phone is not None
    assert vinod.phone.startswith("+91")


def test_load_links_whatsapp_message_to_customer_by_phone(db):
    generate_all(seed=42)
    raw = extract()
    catalog = [{"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523", "qty": 100, "raw_names": ["x"]}]
    load(db, catalog=catalog, tally=clean_tally_dates_and_amounts(raw["tally"]), khata=clean_khata_entries(raw["khata"]),
         whatsapp=raw["whatsapp"], rates=raw["rates"])
    golden_message = db.query(WhatsappMessage).filter(WhatsappMessage.raw_text.contains("10mm sariya 2 ton")).first()
    assert golden_message.customer_id is not None
    linked_customer = db.query(Customer).filter_by(id=golden_message.customer_id).first()
    assert linked_customer.name == "Vinod Builders"


def test_load_populates_supplier_contact(db):
    generate_all(seed=42)
    raw = extract()
    catalog = [{"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523", "qty": 100, "raw_names": ["x"]}]
    load(db, catalog=catalog, tally=clean_tally_dates_and_amounts(raw["tally"]), khata=clean_khata_entries(raw["khata"]),
         whatsapp=raw["whatsapp"], rates=raw["rates"])
    supplier = db.query(Supplier).first()
    assert supplier.contact is not None


def test_load_inserts_supplier_rate_cards_and_maps_unit_by_category(db):
    catalog = [
        {"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523"},
        {"name": "TMT Sariya 10mm", "brand": "Generic", "variant": "10mm", "category": "Steel", "hsn": "7213"},
    ]
    tally = pd.DataFrame(columns=["date", "amount", "gst_number", "product_name", "qty"])
    khata = pd.DataFrame(columns=["customer_name", "date_text", "amount_text", "amount", "note", "customer_phone"])
    rates = pd.DataFrame([{
        "supplier_name": "Supplier 1",
        "product_name": "Ambuja Cement",
        "price": "380/bag",
        "unit": "bag",
        "as_of_date": "2024-01-01",
        "discount_text": "5% above 500 bags",
        "contact": "Ramesh - +919999999999",
    }])

    load(db, catalog=catalog, tally=tally, khata=khata, whatsapp=[], rates=rates)

    rate_card = db.query(SupplierRateCard).one()
    assert rate_card.price == 380.0
    assert rate_card.unit == "bag"

    cement = db.query(Product).filter_by(name="Ambuja Cement").one()
    steel = db.query(Product).filter_by(name="TMT Sariya 10mm").one()
    assert cement.unit == "bag"
    assert steel.unit == "ton"
