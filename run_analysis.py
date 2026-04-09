#!/usr/bin/env python3
"""
Run analytics on bundled WooCommerce + GA exports.

With `data/orders_export_no_pii.csv` (sanitized order-level + line items), also runs:
transaction Apriori, customer LDA, billing-state / monthly revenue summaries.
Outputs: outputs/*.csv, outputs/figures/*.png, outputs/ga_tables/*.csv, REPORT.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.association_rules import (  # noqa: E402
    aggregate_pairs,
    attach_product_names,
    build_rules,
    filter_actionable_rules,
    load_products,
)
from src.cooccurrence_nmf import build_cooccurrence_matrix, nmf_factors  # noqa: E402
from src.basket_mining import apriori_rules, orders_to_baskets  # noqa: E402
from src.config import (  # noqa: E402
    FIGURES,
    FIRST_PRODUCT,
    GA_LONG,
    ORDERS_ANNUAL,
    ORDERS_EXPORT_NO_PII,
    OUTPUT,
    PAIRS,
    POSTCODE,
    PRODUCTS_EXPORT,
    SUBSCRIPTIONS_ANNUAL,
)
from src.geo_time_orders import revenue_by_month, revenue_by_state  # noqa: E402
from src.order_geography_map import plot_order_geography_heatmap  # noqa: E402
from src.lda_customers import customer_product_matrix, fit_lda  # noqa: E402
from src.order_export import (  # noqa: E402
    completed_orders_mask,
    explode_line_items,
    load_orders_export,
)
from src.first_product_cohorts import cohort_rankings, load_first_product  # noqa: E402
from src.network_co_purchase import build_graph, graph_summary, top_edges  # noqa: E402
from src.parse_ga import extract_daily_series, parse_ga_snapshot, save_ga_tables  # noqa: E402
from src.postcodes import load_postcodes, summarize_postcodes, top_postcodes  # noqa: E402
from src.annual_orders import (  # noqa: E402
    load_annual_orders,
    load_subscriptions,
    orders_subscription_summary,
)
from src.advanced_pipeline import run_advanced_all  # noqa: E402


def ensure_dirs() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)


def plot_annual_business(merged: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    years = merged["Date"].astype(str)
    if "Net" in merged.columns:
        net_col = "Net"
    elif "Net_x" in merged.columns:
        net_col = "Net_x"
    else:
        net_col = [c for c in merged.columns if c.startswith("Net")][0]
    axes[0].bar(years, merged[net_col].fillna(0), color="steelblue", alpha=0.85)
    axes[0].set_ylabel("Order net revenue ($)")
    axes[0].set_title("Annual order net revenue")
    if "Signup Count" in merged.columns:
        axes[1].plot(years, merged["Signup Count"].fillna(0), "o-", label="Signups")
    if "Cancelled Count" in merged.columns:
        axes[1].plot(years, -merged["Cancelled Count"].fillna(0), "s-", color="crimson", label="Cancels (negated)")
    axes[1].set_ylabel("Count")
    axes[1].legend()
    axes[1].set_title("Subscription signups vs cancellations")
    axes[1].set_xlabel("Year")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close()


def plot_ga_daily(series: pd.DataFrame | None, out: Path) -> None:
    if series is None or series.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 4))
    v = pd.to_numeric(series.get("value", series.iloc[:, -1]), errors="coerce")
    ax.plot(range(len(v)), v, lw=0.8, color="darkgreen")
    ax.set_title("GA snapshot: daily series (first matching 'Active users' block)")
    ax.set_xlabel("nth day index")
    ax.set_ylabel("value")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close()


def plot_postcode_histogram(df: pd.DataFrame, out: Path) -> None:
    col = "Total Spent" if "Total Spent" in df.columns else None
    if not col:
        return
    s = df[col].dropna()
    s = s[s > 0]
    if len(s) < 5:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(np.log1p(s), bins=40, color="coral", edgecolor="white")
    ax.set_xlabel("log(1 + Total Spent per ZIP)")
    ax.set_ylabel("ZIP count")
    ax.set_title("Distribution of ZIP-level total spend")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close()


def plot_monthly_revenue(monthly: pd.DataFrame, out: Path) -> None:
    if monthly is None or monthly.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 4))
    x = range(len(monthly))
    ax.bar(x, monthly["net_revenue"].fillna(0), color="darkslateblue", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(monthly["month"].astype(str), rotation=45, ha="right")
    ax.set_ylabel("Net revenue ($)")
    ax.set_title("Completed orders — net revenue by month (order export)")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close()


def plot_state_revenue(st: pd.DataFrame, out: Path, top_n: int = 20) -> None:
    if st is None or st.empty:
        return
    sub = st.head(top_n)
    st_col = sub.columns[0]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(sub.iloc[::-1][st_col].astype(str), sub.iloc[::-1]["net_revenue"])
    ax.set_xlabel("Net revenue ($)")
    ax.set_title(f"Top {top_n} billing states by net revenue")
    plt.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close()


def plot_nmf_top_products(W_df: pd.DataFrame, out_dir: Path, k: int = 3) -> None:
    """Bar chart of top absolute loadings for first factors."""
    factor_cols = [c for c in W_df.columns if c.startswith("factor_")]
    for j, fc in enumerate(factor_cols[:k]):
        sub = W_df[["title", fc]].dropna()
        sub = sub.reindex(sub[fc].abs().sort_values(ascending=False).index).head(15)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(sub["title"][::-1], sub[fc][::-1], color="teal", alpha=0.85)
        ax.set_title(f"NMF {fc} — top product loadings")
        plt.tight_layout()
        fig.savefig(out_dir / f"nmf_{fc}.png", dpi=150)
        plt.close()


def write_report(path: Path, snippets: list[str]) -> None:
    path.write_text("\n\n".join(snippets), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    report_lines = [
        "# FireFly Farms — automated analysis report",
        "Generated from bundled WooCommerce + GA exports (aggregate + order-level where available).",
        "",
    ]

    # --- Annual orders + subscriptions ---
    orders = load_annual_orders(ORDERS_ANNUAL)
    subs = load_subscriptions(SUBSCRIPTIONS_ANNUAL)
    merged = orders_subscription_summary(orders, subs)
    merged.to_csv(OUTPUT / "annual_orders_subscriptions.csv", index=False)
    total_orders = float(orders["Orders"].sum())
    report_lines.append(f"- **Total orders (all years in export):** {int(total_orders)}")
    plot_annual_business(merged, FIGURES / "annual_orders_subscriptions.png")

    # --- First-product cohorts ---
    fp = load_first_product(FIRST_PRODUCT)
    fp.to_csv(OUTPUT / "first_product_cohorts_full.csv", index=False)
    top_c = cohort_rankings(fp)
    top_c.to_csv(OUTPUT / "first_product_cohorts_top40.csv", index=False)

    # --- Postcodes ---
    pc = load_postcodes(POSTCODE)
    pc.to_csv(OUTPUT / "postcode_cohorts_full.csv", index=False)
    top_postcodes(pc).to_csv(OUTPUT / "postcode_top30_spend.csv", index=False)
    plot_postcode_histogram(pc, FIGURES / "postcode_spend_distribution.png")
    summ = summarize_postcodes(pc)
    report_lines.append(
        f"- **ZIP cohorts:** {summ.get('n_postcodes')} postcodes; total spend ≈ ${summ.get('total_spend', 0):,.0f}"
    )

    # --- Products + association rules ---
    products = load_products(PRODUCTS_EXPORT)
    products.to_csv(OUTPUT / "products_aggregated_by_id.csv", index=False)
    pairs_agg = aggregate_pairs(PAIRS)
    pairs_agg.to_csv(OUTPUT / "pairs_aggregated_by_product_ids.csv", index=False)

    rules = build_rules(pairs_agg, products, total_orders)
    rules_named = attach_product_names(rules, products)
    rules_named.to_csv(OUTPUT / "association_rules_all_pairs.csv", index=False)

    rules_f = filter_actionable_rules(rules_named, min_orders_each=15, min_co_purchase=5)
    rules_f.to_csv(OUTPUT / "association_rules_filtered.csv", index=False)
    report_lines.append(
        f"- **Association rules:** {len(rules_named)} pairs scored; "
        f"{len(rules_f)} after filter (min 15 orders each side, min 5 co-purchases)."
    )

    titles = products.set_index("product_id")["title"].to_dict()
    G = build_graph(pairs_agg.rename(columns={"co_count": "co_count"}), min_co=5.0)
    nx_edges = top_edges(G, titles, k=50)
    nx_edges.to_csv(OUTPUT / "co_purchase_top_edges.csv", index=False)
    cent = graph_summary(G, titles)
    cent.to_csv(OUTPUT / "co_purchase_centrality.csv", index=False)

    # --- NMF on product–product matrix ---
    co_mat, ids = build_cooccurrence_matrix(pairs_agg, products)
    co_mat.to_csv(OUTPUT / "product_cooccurrence_matrix.csv")
    try:
        W_df, _H = nmf_factors(co_mat, n_components=6)
        W_df["title"] = W_df.index.map(lambda i: titles.get(int(i), ""))
        W_df.to_csv(OUTPUT / "nmf_product_loadings.csv", index_label="product_id")
        plot_nmf_top_products(W_df, FIGURES, k=3)
        report_lines.append(
            "- **NMF** on product co-occurrence (+ diagonal net orders): see `outputs/nmf_product_loadings.csv`."
        )
    except Exception as e:
        report_lines.append(f"- **NMF:** skipped ({e})")

    # --- GA snapshot ---
    ga_path = GA_LONG if GA_LONG.exists() else None
    if ga_path and ga_path.exists():
        sections = parse_ga_snapshot(ga_path)
        ga_dir = OUTPUT / "ga_tables"
        save_ga_tables(sections, ga_dir)
        report_lines.append(
            f"- **GA tables parsed:** {len(sections)} sections saved under `outputs/ga_tables/`."
        )
        daily = extract_daily_series(sections)
        if daily is not None:
            daily.to_csv(OUTPUT / "ga_daily_active_users_series.csv", index=False)
            plot_ga_daily(daily, FIGURES / "ga_daily_series.png")

    # --- Sanitized order export: baskets, LDA, geo, monthly ---
    raw_orders = None
    monthly_orders = None
    if ORDERS_EXPORT_NO_PII.exists():
        raw = load_orders_export(ORDERS_EXPORT_NO_PII)
        raw_orders = raw
        order_lines = explode_line_items(raw)
        order_lines.to_csv(OUTPUT / "order_line_items_long.csv", index=False)
        report_lines.append(
            f"- **Order export:** {len(raw)} rows; exploded line rows: {len(order_lines)}."
        )

        done_mask = completed_orders_mask(raw)
        done_ids = set(
            pd.to_numeric(raw.loc[done_mask, "Order ID"], errors="coerce").dropna().astype(int)
        )
        order_lines["oid"] = pd.to_numeric(order_lines["order_id"], errors="coerce")
        lines_ok = order_lines[
            order_lines["oid"].isin(done_ids) & order_lines["product_name"].notna()
        ]

        st_df = revenue_by_state(raw, completed_only=True)
        if not st_df.empty:
            st_df.to_csv(OUTPUT / "revenue_by_billing_state.csv", index=False)
            plot_state_revenue(st_df, FIGURES / "revenue_by_billing_state.png")
            if plot_order_geography_heatmap(st_df, FIGURES / "orders_geography_heatmap.png"):
                report_lines.append(
                    "- **Order geography:** heatmap/bubble map `outputs/figures/orders_geography_heatmap.png` "
                    "(billing state volume & revenue; farm location marked)."
                )

        mo = revenue_by_month(raw, completed_only=True)
        monthly_orders = mo
        if not mo.empty:
            mo.to_csv(OUTPUT / "revenue_by_month.csv", index=False)
            plot_monthly_revenue(mo, FIGURES / "revenue_by_month.png")

        baskets = orders_to_baskets(lines_ok.dropna(subset=["product_name"]))
        fi, arules = apriori_rules(baskets, min_support=0.012, min_threshold=0.35)
        if fi is not None:
            fi.to_csv(OUTPUT / "apriori_frequent_itemsets.csv", index=False)
            if arules is not None and not arules.empty:
                arules.to_csv(OUTPUT / "apriori_association_rules.csv", index=False)
            report_lines.append(
                f"- **Apriori (from parsed line items):** {len(fi)} frequent itemsets; "
                f"{len(arules) if arules is not None else 0} rules."
            )

        try:
            cm, _custs, prods = customer_product_matrix(
                lines_ok, min_customer_lines=4, min_product_count=12
            )
            if len(cm) >= 15 and len(prods) >= 8:
                cust_topic, topic_words, _m = fit_lda(cm, n_topics=6)
                cust_topic.to_csv(OUTPUT / "lda_customer_topic_weights.csv")
                topic_words.to_csv(OUTPUT / "lda_topic_product_loadings.csv")
                report_lines.append(
                    f"- **LDA (customer purchase personas):** {len(cm)} customers × {len(prods)} products; 6 topics."
                )
        except Exception as e:
            report_lines.append(f"- **LDA:** skipped ({e}).")

    run_advanced_all(
        raw_orders,
        monthly_orders,
        POSTCODE,
        PRODUCTS_EXPORT,
        report_lines,
    )

    write_report(OUTPUT / "REPORT.md", report_lines)

    from src.analytics_index import write_index

    write_index(OUTPUT)
    print(f"Done. See {OUTPUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
