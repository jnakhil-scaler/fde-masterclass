import json
from pathlib import Path
import random

import pandas as pd
from faker import Faker

from app.data.catalog import PRODUCT_CATALOG

OUTPUT_DIR = Path(__file__).parent / "raw"

# Fixed 3-template set, indexed positionally below (not a generic iterable) because each
# template needs a differently-shaped substitution (full brand, abbreviated lowercase, upper).
# Adding a 4th variant means adding both a template here and a matching format() call below.
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


def _generate_stock_register(fake: Faker, rng: random.Random, total_skus: int = 500) -> dict[str, pd.DataFrame]:
    rows = []
    for name, category, unit, _, hsn in PRODUCT_CATALOG:
        variants = _name_variants(name) if category == "Cement" else [name]
        for variant in variants:
            # Messy unit strings on purpose: plural, upper-case, and a bag-specific abbreviation,
            # so downstream unit-normalization has real inconsistency to clean up.
            rows.append({
                "product_name": variant,
                "category": category,
                "unit": rng.choice([unit, unit + "s", unit.upper(), "BGS" if unit == "bag" else unit]),
                "qty": rng.choice([rng.randint(10, 500), -rng.randint(1, 20)]),
                "hsn_code": hsn,
            })
    # pad out to `total_skus` SKUs (default ~500) with generic hardware items.
    # A negative range() is already a no-op, so if total_skus is smaller than the
    # real catalog row count above, this loop simply contributes zero rows.
    for _ in range(max(0, total_skus - len(rows))):
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
            "customer": rng.choice(["CASH", f"{fake.name()} {rng.choice(['Contractor', 'Builders', 'Construction', 'Enterprises'])}"]),
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


def _generate_whatsapp_orders(fake: Faker, rng: random.Random) -> list:
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


SUPPLIER_NAME_SUFFIXES = ["Traders", "Building Materials", "Steel & Cement Co.", "Hardware Agency", "Enterprises", "& Sons", "Trading Co.", "Suppliers", "Agency", "& Brothers"]


def _generate_supplier_rates(fake: Faker, rng: random.Random) -> pd.DataFrame:
    rows = []
    for _ in range(1, 13):
        supplier = f"{fake.last_name()} {rng.choice(SUPPLIER_NAME_SUFFIXES)}"
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


def generate_all(seed: int = 42, total_skus: int = 500):
    fake = Faker("en_IN")
    Faker.seed(seed)
    rng = random.Random(seed)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_DIR / "stock_register.xlsx") as writer:
        for sheet_name, sheet_df in _generate_stock_register(fake, rng, total_skus=total_skus).items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    _generate_tally_export(fake, rng).to_csv(OUTPUT_DIR / "tally_export.csv", index=False)
    _generate_khata_ledger(fake, rng).to_csv(OUTPUT_DIR / "khata_ledger.csv", index=False)
    (OUTPUT_DIR / "whatsapp_orders.json").write_text(json.dumps(_generate_whatsapp_orders(fake, rng), indent=2))
    _generate_supplier_rates(fake, rng).to_csv(OUTPUT_DIR / "supplier_rates.csv", index=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate the 5 raw messy datasets for Gupta Building Materials.")
    parser.add_argument("--total-skus", type=int, default=500, help="Number of SKU rows in the stock register (default: 500, full realistic scale). Use a smaller number (e.g. 70) for a fast live-demo run.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_all(seed=args.seed, total_skus=args.total_skus)
