"""Paths and filenames for bundled exports."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "outputs"
FIGURES = OUTPUT / "figures"

PRODUCTS_EXPORT = DATA / "bf07910d02561dd740a14bada1338dad.csv"
PAIRS = DATA / "products-bought-together-report-2022-03-20-2026-03-20.csv"
ORDERS_ANNUAL = DATA / "orders-report-2022-03-20-2026-03-20.csv"
SUBSCRIPTIONS_ANNUAL = DATA / "subscriptions-events-report-2022-03-20-2026-03-20.csv"
FIRST_PRODUCT = DATA / "grouped-by-first_product-data-2022-03-20-2026-03-20.csv"
POSTCODE = DATA / "grouped-by-billing_address_postcode-data-2022-03-20-2026-03-20.csv"
GA_LONG = DATA / "Reports_snapshot(1).csv"
GA_SHORT = DATA / "Reports_snapshot.csv"
# Order export with no personal identifiers (place your sanitized Woo export here)
ORDERS_EXPORT_NO_PII = DATA / "orders_export_no_pii.csv"
