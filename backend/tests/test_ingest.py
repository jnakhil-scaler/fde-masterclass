import pandas as pd
import pytest

from app.agents.claude_client import has_real_api_key
from app.data.generate_data import generate_all
from app.data.ingest import extract, clean_tally_dates_and_amounts, clean_khata_entries, resolve_ambiguous_products, load, verify
from app.models import Invoice, CreditLedger, Product, SupplierRateCard

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


def test_load_inserts_supplier_rate_cards_and_maps_unit_by_category(db):
    catalog = [
        {"name": "Ambuja Cement", "brand": "Ambuja", "variant": "50 KG Bag", "category": "Cement", "hsn": "2523"},
        {"name": "TMT Sariya 10mm", "brand": "Generic", "variant": "10mm", "category": "Steel", "hsn": "7213"},
    ]
    tally = pd.DataFrame(columns=["date", "amount", "gst_number", "product_name", "qty"])
    khata = pd.DataFrame(columns=["customer_name", "date_text", "amount_text", "amount", "note"])
    rates = pd.DataFrame([{
        "supplier_name": "Supplier 1",
        "product_name": "Ambuja Cement",
        "price": "380/bag",
        "unit": "bag",
        "as_of_date": "2024-01-01",
        "discount_text": "5% above 500 bags",
    }])

    load(db, catalog=catalog, tally=tally, khata=khata, whatsapp=[], rates=rates)

    rate_card = db.query(SupplierRateCard).one()
    assert rate_card.price == 380.0
    assert rate_card.unit == "bag"

    cement = db.query(Product).filter_by(name="Ambuja Cement").one()
    steel = db.query(Product).filter_by(name="TMT Sariya 10mm").one()
    assert cement.unit == "bag"
    assert steel.unit == "ton"
