"""Frequent itemsets and association rules from order baskets (product names)."""
from __future__ import annotations

import pandas as pd

try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    HAS_MLXTEND = True
except ImportError:
    HAS_MLXTEND = False


def orders_to_baskets(lines: pd.DataFrame) -> list[list[str]]:
    """One basket = list of product names (repeat qty times for weighted support)."""
    baskets: list[list[str]] = []
    for oid, g in lines.groupby("order_id"):
        items: list[str] = []
        for _, r in g.iterrows():
            if not r.get("product_name"):
                continue
            q = int(max(1, float(r.get("quantity", 1))))
            items.extend([str(r["product_name"])] * q)
        if items:
            baskets.append(items)
    return baskets


def apriori_rules(
    baskets: list[list[str]],
    min_support: float = 0.015,
    min_threshold: float = 0.4,
    metric: str = "confidence",
) -> tuple[pd.DataFrame, pd.DataFrame] | tuple[None, None]:
    """
    Returns (frequent_itemsets, rules) or (None, None) if mlxtend missing.
    min_support is fraction of orders (transactions).
    """
    if not HAS_MLXTEND or not baskets:
        return None, None
    te = TransactionEncoder()
    te_ary = te.fit_transform(baskets)
    ohe = pd.DataFrame(te_ary, columns=te.columns_)
    fi = apriori(ohe, min_support=min_support, use_colnames=True)
    if fi.empty:
        return fi, pd.DataFrame()
    rules = association_rules(
        fi,
        metric=metric,
        min_threshold=min_threshold,
    )
    return fi, rules
