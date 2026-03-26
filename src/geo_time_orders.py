"""Billing geography and monthly revenue from order export."""
from __future__ import annotations

import pandas as pd


def revenue_by_state(orders: pd.DataFrame, completed_only: bool = True) -> pd.DataFrame:
    df = orders.copy()
    if completed_only and "Status" in df.columns:
        df = df[df["Status"].astype(str).str.lower() == "completed"]
    st = "Billing Address State"
    net = "Net" if "Net" in df.columns else "Total"
    if st not in df.columns:
        return pd.DataFrame()
    oid = "Order ID" if "Order ID" in df.columns else df.columns[0]
    g = (
        df.groupby(st, dropna=False)
        .agg(
            net_revenue=(net, lambda s: pd.to_numeric(s, errors="coerce").sum()),
            n_orders=(oid, "count"),
        )
        .reset_index()
    )
    return g.sort_values("net_revenue", ascending=False)


def revenue_by_month(orders: pd.DataFrame, completed_only: bool = True) -> pd.DataFrame:
    df = orders.copy()
    if completed_only and "Status" in df.columns:
        df = df[df["Status"].astype(str).str.lower() == "completed"]
    dt = "Order Created At"
    net = "Net" if "Net" in df.columns else "Total"
    if dt not in df.columns:
        return pd.DataFrame()
    df["_d"] = pd.to_datetime(df[dt], errors="coerce")
    df = df[df["_d"].notna()]
    df["_m"] = df["_d"].dt.to_period("M").astype(str)
    g = (
        df.groupby("_m", as_index=False)
        .agg(
            net_revenue=(net, lambda s: pd.to_numeric(s, errors="coerce").sum()),
            n_orders=("Order ID", "count"),
        )
        .rename(columns={"_m": "month"})
    )
    return g.sort_values("month")
