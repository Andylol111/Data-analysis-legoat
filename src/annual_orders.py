"""Yearly orders + subscription rollups."""
from __future__ import annotations

import pandas as pd


def load_annual_orders(path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_subscriptions(path) -> pd.DataFrame:
    return pd.read_csv(path)


def orders_subscription_summary(orders: pd.DataFrame, subs: pd.DataFrame) -> pd.DataFrame:
    """Join on year for a single dashboard table."""
    o = orders.copy()
    o["Date"] = o["Date"].astype(str)
    s = subs.copy()
    s["Date"] = s["Date"].astype(str)
    merged = o.merge(s, on="Date", how="outer", suffixes=("_orders", "_subs"))
    return merged.sort_values("Date")
