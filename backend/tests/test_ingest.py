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
