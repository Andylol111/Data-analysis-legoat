"""Association metrics from pre-aggregated product pairs + product order counts."""
from __future__ import annotations

import pandas as pd


def load_products(path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    # normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    id_col = "Product ID" if "Product ID" in df.columns else df.columns[1]
    orders_col = "Net Orders" if "Net Orders" in df.columns else None
    if orders_col is None:
        raise ValueError("Expected Net Orders in product export")
    title_col = "Title" if "Title" in df.columns else df.columns[0]
    cat_col = "Category Names" if "Category Names" in df.columns else None
    use = [id_col, title_col, orders_col]
    if cat_col:
        use.append(cat_col)
    out = df[use].copy()
    out.columns = ["product_id", "title", "net_orders"] + (
        ["category"] if cat_col else []
    )
    out["product_id"] = pd.to_numeric(out["product_id"], errors="coerce").astype("Int64")
    out["net_orders"] = pd.to_numeric(out["net_orders"], errors="coerce").fillna(0)
    # collapse duplicate product ids (variations) — sum orders
    agg = {"net_orders": "sum", "title": "first"}
    if "category" in out.columns:
        agg["category"] = "first"
    out = out.groupby("product_id", as_index=False).agg(agg)
    return out


def aggregate_pairs(pairs_path) -> pd.DataFrame:
    p = pd.read_csv(pairs_path)
    p["co_count"] = pd.to_numeric(p["Times Bought Together"], errors="coerce").fillna(0)
    # same logical pair may appear with different variation ids — sum
    g = (
        p.groupby(["Product A Id", "Product B Id"], as_index=False)["co_count"]
        .sum()
    )
    return g


def build_rules(
    pairs_df: pd.DataFrame,
    products_df: pd.DataFrame,
    total_orders: float,
) -> pd.DataFrame:
    """
    support(A,B) = co_ab / N
    conf(B|A) = co_ab / orders_A
    lift = support(A,B) / (support(A) * support(B))
    """
    pid = products_df.set_index("product_id")["net_orders"].to_dict()

    rows = []
    for _, r in pairs_df.iterrows():
        a, b, co = int(r["Product A Id"]), int(r["Product B Id"]), float(r["co_count"])
        if co <= 0:
            continue
        oa = pid.get(a)
        ob = pid.get(b)
        if oa is None or ob is None or oa <= 0 or ob <= 0:
            continue
        sa = oa / total_orders
        sb = ob / total_orders
        sab = co / total_orders
        lift = sab / (sa * sb) if sa * sb > 0 else float("nan")
        conf_a_to_b = co / oa
        conf_b_to_a = co / ob
        rows.append(
            {
                "product_a_id": a,
                "product_b_id": b,
                "co_purchase_count": co,
                "support": sab,
                "confidence_a_to_b": conf_a_to_b,
                "confidence_b_to_a": conf_b_to_a,
                "lift": lift,
                "orders_a": oa,
                "orders_b": ob,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("lift", ascending=False)
    return out


def filter_actionable_rules(
    rules: pd.DataFrame,
    min_orders_each: float = 15.0,
    min_co_purchase: float = 5.0,
) -> pd.DataFrame:
    """Down-rank noise from ultra-rare SKUs (lift explodes when support(A)≈1/N)."""
    if rules.empty:
        return rules
    m = rules[
        (rules["orders_a"] >= min_orders_each)
        & (rules["orders_b"] >= min_orders_each)
        & (rules["co_purchase_count"] >= min_co_purchase)
    ]
    return m.sort_values(["lift", "co_purchase_count"], ascending=[False, False])


def attach_product_names(rules: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    titles = products_df.set_index("product_id")["title"].to_dict()
    out = rules.copy()
    out["product_a_name"] = out["product_a_id"].map(titles)
    out["product_b_name"] = out["product_b_id"].map(titles)
    return out
