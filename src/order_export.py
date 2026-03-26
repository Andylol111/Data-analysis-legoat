"""Load WooCommerce order export and parse Line Items into long-form rows."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# "Product Name x3" or "Product x12" (multiline in source cell)
_LINE_RE = re.compile(r"^\s*(.+?)\s+x\s*(\d+)\s*$", re.MULTILINE | re.IGNORECASE)


def load_orders_export(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_line_items_block(text: str) -> list[tuple[str, int]]:
    if not isinstance(text, str) or not text.strip():
        return []
    out: list[tuple[str, int]] = []
    for m in _LINE_RE.finditer(text.strip()):
        name = m.group(1).strip()
        try:
            qty = int(m.group(2))
        except ValueError:
            continue
        if name:
            out.append((name, qty))
    return out


def explode_line_items(df: pd.DataFrame) -> pd.DataFrame:
    """One row per order line (product x quantity)."""
    rows = []
    oid = "Order ID" if "Order ID" in df.columns else df.columns[0]
    created = "Order Created At" if "Order Created At" in df.columns else None
    link = "Customer Link ID" if "Customer Link ID" in df.columns else None
    cust = "Customer ID" if "Customer ID" in df.columns else None
    bill_zip = "Billing Address Postcode" if "Billing Address Postcode" in df.columns else None
    bill_st = "Billing Address State" if "Billing Address State" in df.columns else None
    net = "Net" if "Net" in df.columns else "Total After Refunds"
    status = "Status" if "Status" in df.columns else None

    for _, r in df.iterrows():
        items = parse_line_items_block(r.get("Line Items", ""))
        ck = ""
        if link and pd.notna(r.get(link)) and str(r.get(link)).strip():
            ck = str(r.get(link)).strip()
        elif cust and pd.notna(r.get(cust)) and str(r.get(cust)).strip():
            ck = str(r.get(cust)).strip()
        base = {
            "order_id": r.get(oid),
            "order_date": pd.to_datetime(r.get(created), errors="coerce") if created else None,
            "customer_id": ck,
            "billing_postcode": _clean_zip(r.get(bill_zip)) if bill_zip else None,
            "billing_state": str(r.get(bill_st)).strip() if bill_st and pd.notna(r.get(bill_st)) else None,
            "net": pd.to_numeric(r.get(net), errors="coerce"),
            "status": r.get(status) if status else None,
        }
        if not items:
            rows.append({**base, "product_name": None, "quantity": 0})
            continue
        for name, qty in items:
            rows.append({**base, "product_name": name, "quantity": qty})

    return pd.DataFrame(rows)


def _clean_zip(z) -> str | None:
    if z is None or (isinstance(z, float) and pd.isna(z)):
        return None
    s = str(z).strip()
    return s[:10] if s else None


def completed_orders_mask(df: pd.DataFrame) -> pd.Series:
    if "Status" not in df.columns:
        return pd.Series(True, index=df.index)
    return df["Status"].astype(str).str.lower().eq("completed")
