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
