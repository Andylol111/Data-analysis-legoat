"""Billing postcode (ZIP) cohort aggregates."""
from __future__ import annotations

import pandas as pd


def load_postcodes(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    zip_col = "Billing ZIP" if "Billing ZIP" in df.columns else df.columns[0]
    df = df.rename(columns={zip_col: "postcode"})
    for c in df.columns:
        if c != "postcode":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def summarize_postcodes(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    spend = df.get("Total Spent", pd.Series(dtype=float))
    cust = df.get("Total Customers", pd.Series(dtype=float))
    return {
        "n_postcodes": len(df),
        "total_customers": float(cust.sum()) if cust is not None else None,
        "total_spend": float(spend.sum()) if spend is not None else None,
        "median_customers_per_zip": float(cust.median()) if cust is not None else None,
    }


def top_postcodes(df: pd.DataFrame, by: str = "Total Spent", n: int = 30) -> pd.DataFrame:
    if by not in df.columns:
        by = df.columns[df.columns.str.contains("Spent", case=False)][0]
    return df.nlargest(n, by)
