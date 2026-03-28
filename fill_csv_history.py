"""
fill_csv_history.py
====================
Populates data/raw/daily_sales_TEMPLATE.csv with 60 days of realistic
fictional sales data so the Daily Ops chart has meaningful content.

Keeps any existing rows (does not truncate).
Run once: python fill_csv_history.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT     = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "raw" / "daily_sales_TEMPLATE.csv"
CSV_COLUMNS = ["Date", "Product", "Quantity", "Unit_Price", "Total", "Payment_Method", "Source"]

# ── Product catalogue with realistic prices ────────────────────────────────────
PRODUCTS = [
    # (name, unit_price, weight)  — weight = how often it sells
    ("Chaveiro Pequeno",        15.00, 3.0),
    ("Chaveiro Xadrez",         20.00, 2.5),
    ("Chaveiro Personalizado",  25.00, 2.0),
    ("Chaveiro Couro",          30.00, 1.5),
    ("Chaveiro Duplo",          35.00, 1.0),
    ("Carteira Alça",           45.00, 3.0),
    ("Carteira Zip",            55.00, 2.5),
    ("Carteira Tricolor",       60.00, 2.0),
    ("Carteira Slim",           50.00, 1.5),
    ("Carteira Premium",        75.00, 1.0),
    ("Carteira Mini",           40.00, 2.0),
    ("Carteira Envelope",       65.00, 1.5),
    ("Nécessaire Stylo",        35.00, 3.0),
    ("Nécessaire Grande",       45.00, 2.5),
    ("Nécessaire Média",        38.00, 2.5),
    ("Nécessaire Pequena",      30.00, 2.0),
    ("Nécessaire Viagem",       55.00, 1.5),
    ("Bolsa Palha",             89.00, 2.0),
    ("Bolsa Couro",            120.00, 1.5),
    ("Body Floral",             65.00, 1.5),
    ("Body Estampado",          70.00, 1.0),
    ("Canga Listrada",          45.00, 1.5),
    ("Canga Estampada",         50.00, 1.0),
]

PAYMENT_METHODS = ["Pix", "Pix", "Pix",
                   "Dinheiro", "Dinheiro",
                   "Crédito", "Crédito",
                   "Débito"]

random.seed(42)

def weighted_product():
    names   = [p[0] for p in PRODUCTS]
    prices  = {p[0]: p[1] for p in PRODUCTS}
    weights = [p[2] for p in PRODUCTS]
    name = random.choices(names, weights=weights, k=1)[0]
    return name, prices[name]

def day_multiplier(d: date) -> float:
    """Weekend and month-end boost."""
    m = 1.0
    if d.weekday() >= 5:   m *= 1.6   # Sat/Sun
    if d.weekday() == 4:   m *= 1.3   # Fri
    if d.day >= 28:        m *= 1.2   # month-end
    return m

def generate_rows(start: date, end: date) -> list[dict]:
    rows = []
    current = start
    while current <= end:
        base_txns = random.randint(2, 8)
        n_txns = max(1, round(base_txns * day_multiplier(current)))
        for _ in range(n_txns):
            product, price = weighted_product()
            qty = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
            total = round(qty * price, 2)
            rows.append({
                "Date":           current.strftime("%Y-%m-%d"),
                "Product":        product,
                "Quantity":       qty,
                "Unit_Price":     price,
                "Total":          total,
                "Payment_Method": random.choice(PAYMENT_METHODS),
                "Source":         "historical",
            })
        current += timedelta(days=1)
    return rows

# ── Read existing rows to avoid re-inserting ──────────────────────────────────
existing_keys = set()
if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing_keys.add((row.get("Date",""), row.get("Product",""),
                               row.get("Source",""), row.get("Total","")))

# ── Generate 60 days ending yesterday ─────────────────────────────────────────
today     = date.today()
end_date  = today - timedelta(days=1)
start_date = end_date - timedelta(days=59)

new_rows = [
    r for r in generate_rows(start_date, end_date)
    if (r["Date"], r["Product"], r["Source"], str(r["Total"])) not in existing_keys
]

# ── Write CSV (append or create with header) ──────────────────────────────────
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
needs_header = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0

with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    if needs_header:
        writer.writeheader()
    writer.writerows(new_rows)

total_revenue = sum(r["Total"] for r in new_rows)
print(f"✅ Added {len(new_rows)} rows | Period: {start_date} → {end_date} | Revenue: R$ {total_revenue:,.2f}")
print(f"   CSV: {CSV_PATH}")
