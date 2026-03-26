"""First-product acquisition cohorts."""
from __future__ import annotations

import pandas as pd


def load_first_product(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


def cohort_rankings(df: pd.DataFrame, metric: str = "Avg Spent") -> pd.DataFrame:
    if metric not in df.columns:
        metric = [c for c in df.columns if "Spent" in c][0]
    base = df.columns[0]
    return df.sort_values(metric, ascending=False)[[base, "Total Customers", metric, "Returning Customers Rate"]].head(40)
