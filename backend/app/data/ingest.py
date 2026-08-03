import json
import re
from pathlib import Path
from typing import Optional

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


def _parse_amount_text(text: str) -> Optional[float]:
    if not isinstance(text, str):
        return None
    lakh_match = _LAKH_RE.search(text)
    if lakh_match:
        return round(float(lakh_match.group(1)) * 100_000, 2)
    k_match = _K_RE.search(text)
    if k_match:
        return round(float(k_match.group(1)) * 1_000, 2)
    return None


def clean_khata_entries(khata: pd.DataFrame) -> pd.DataFrame:
    """Step 2 (§4.4): parse Hindi-English lakh/thousand shorthand into numeric amounts."""
    df = khata.copy()
    df["amount"] = df["amount_text"].apply(_parse_amount_text)
    return df
