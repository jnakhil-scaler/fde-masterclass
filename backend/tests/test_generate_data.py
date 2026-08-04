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
    assert len(vinod_rows) == 1  # exactly one khata row — not 3 duplicated entries (was ₹12.3L, should be ₹4.1L)
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


def test_generate_all_respects_smaller_total_skus_for_live_demo():
    generate_all(seed=42, total_skus=70)
    sheets = pd.read_excel(OUTPUT_DIR / "stock_register.xlsx", sheet_name=None)
    all_rows = pd.concat(sheets.values())
    assert len(all_rows) == 70
    ambuja_variants = all_rows[all_rows["product_name"].str.contains("mbuja", case=False, na=False)]
    assert ambuja_variants["product_name"].nunique() >= 3


def test_khata_customers_have_phone_numbers():
    generate_all(seed=42)
    # NOTE: dtype={"customer_phone": str} is required here because pandas' default
    # type-sniffing on read_csv silently coerces "+91XXXXXXXXXX" strings to int64
    # (stripping the leading "+"). Any code reading this column must pin the dtype.
    khata = pd.read_csv(OUTPUT_DIR / "khata_ledger.csv", dtype={"customer_phone": str})
    assert "customer_phone" in khata.columns
    assert khata["customer_phone"].notna().all()
    # same customer, same phone across all their rows
    vinod = khata[khata["customer_name"] == "Vinod Builders"]
    assert vinod["customer_phone"].nunique() == 1


def test_whatsapp_senders_are_real_khata_customers():
    generate_all(seed=42)
    khata = pd.read_csv(OUTPUT_DIR / "khata_ledger.csv", dtype={"customer_phone": str})
    known_phones = set(khata["customer_phone"])
    whatsapp = json.loads((OUTPUT_DIR / "whatsapp_orders.json").read_text())
    assert all(m["sender_phone"] in known_phones for m in whatsapp)


def test_golden_path_whatsapp_message_is_from_vinod_builders():
    generate_all(seed=42)
    khata = pd.read_csv(OUTPUT_DIR / "khata_ledger.csv", dtype={"customer_phone": str})
    vinod_phone = khata[khata["customer_name"] == "Vinod Builders"]["customer_phone"].iloc[0]
    whatsapp = json.loads((OUTPUT_DIR / "whatsapp_orders.json").read_text())
    golden_message = next(m for m in whatsapp if "10mm sariya 2 ton" in m["raw_text"])
    assert golden_message["sender_phone"] == vinod_phone


def test_supplier_rates_include_contact_info():
    generate_all(seed=42)
    rates = pd.read_csv(OUTPUT_DIR / "supplier_rates.csv")
    assert "contact" in rates.columns
    assert rates["contact"].notna().all()
    # same supplier, same contact across all their product rows
    first_supplier = rates["supplier_name"].iloc[0]
    assert rates[rates["supplier_name"] == first_supplier]["contact"].nunique() == 1
