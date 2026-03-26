"""
Advanced models feasible on order-level + aggregate exports.
Each block is isolated — failures do not stop the rest.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUTPUT_ADV = Path(__file__).resolve().parents[1] / "outputs" / "advanced"
FIGURES = Path(__file__).resolve().parents[1] / "outputs" / "figures"


def _customer_key(row: pd.Series) -> str:
    for k in ("Customer Link ID", "Customer ID"):
        if k in row.index and pd.notna(row[k]) and str(row[k]).strip():
            return str(row[k]).strip()
    return ""


def _transactions_from_orders(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["Status"].astype(str).str.lower() == "completed"].copy()
    df["_cust"] = df.apply(_customer_key, axis=1)
    df = df[df["_cust"].str.len() > 0]
    df["_dt"] = pd.to_datetime(df.get("Order Created At"), errors="coerce")
    df = df[df["_dt"].notna()]
    df["_net"] = pd.to_numeric(df.get("Net"), errors="coerce")
    df = df[df["_net"].notna() & (df["_net"] > 0)]
    return pd.DataFrame(
        {
            "customer_id": df["_cust"],
            "date": df["_dt"],
            "monetary_value": df["_net"],
        }
    )


def run_clv_lifetimes(trans: pd.DataFrame, report: list[str]) -> None:
    """BG/NBD + Gamma-Gamma + simple CLV (lifetimes)."""
    try:
        from lifetimes import BetaGeoFitter, GammaGammaFitter
        from lifetimes.utils import summary_data_from_transaction_data
    except ImportError:
        report.append("- **CLV (BG/NBD):** skipped (install `lifetimes`).")
        return

    if trans.empty or trans["customer_id"].nunique() < 30:
        report.append("- **CLV (BG/NBD):** skipped (need enough customers).")
        return

    end = trans["date"].max()
    summary = summary_data_from_transaction_data(
        trans,
        customer_id_col="customer_id",
        datetime_col="date",
        monetary_value_col="monetary_value",
        observation_period_end=end,
    )
    summary = summary[summary["frequency"] >= 0]
    if len(summary) < 30:
        report.append("- **CLV (BG/NBD):** skipped after summarization.")
        return

    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_ADV / "clv_rfm_summary.csv")

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(summary["frequency"], summary["recency"], summary["T"])
    summary["p_alive"] = bgf.conditional_probability_alive(
        summary["frequency"], summary["recency"], summary["T"]
    )
    summary["exp_purchases_90d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        90, summary["frequency"], summary["recency"], summary["T"]
    )

    rep = summary[summary["frequency"] > 0].copy()
    if len(rep) >= 20:
        ggf = GammaGammaFitter(penalizer_coef=0.01)
        ggf.fit(rep["frequency"], rep["monetary_value"])
        summary_clv = summary.copy()
        cond = summary_clv["frequency"] > 0
        summary_clv.loc[cond, "exp_avg_profit"] = ggf.conditional_expected_average_profit(
            summary_clv.loc[cond, "frequency"],
            summary_clv.loc[cond, "monetary_value"],
        )
        summary_clv.loc[cond, "clv_12m"] = ggf.customer_lifetime_value(
            bgf,
            summary_clv.loc[cond, "frequency"],
            summary_clv.loc[cond, "recency"],
            summary_clv.loc[cond, "T"],
            summary_clv.loc[cond, "monetary_value"],
            time=12,
            discount_rate=0.01,
            freq="D",
        )
        summary_clv.to_csv(OUTPUT_ADV / "clv_customer_estimates.csv", index=True)
        report.append(
            f"- **CLV (BG/NBD + Gamma-Gamma):** {len(summary_clv)} customers; see `outputs/advanced/clv_customer_estimates.csv`."
        )
    else:
        summary.to_csv(OUTPUT_ADV / "clv_customer_estimates.csv", index=True)
        report.append(
            f"- **BG/NBD:** fitted; Gamma-Gamma skipped (few repeat buyers). See `outputs/advanced/clv_customer_estimates.csv`."
        )


def run_time_series_monthly(mo: pd.DataFrame, report: list[str]) -> None:
    """STL decomposition, naive ARIMA, PELT changepoints on monthly revenue."""
    if mo is None or mo.empty or len(mo) < 6:
        report.append("- **Time series (STL/ARIMA/changepoints):** skipped (need ≥6 months).")
        return

    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    mo = mo.sort_values("month")
    y = pd.to_numeric(mo["net_revenue"], errors="coerce").values.astype(float)

    # STL
    try:
        from statsmodels.tsa.seasonal import STL

        period = min(11, max(3, (len(mo) // 2) | 1))
        if period % 2 == 0:
            period -= 1
        period = max(3, min(period, len(mo) - 1))
        stl = STL(y, period=period, robust=True)
        res = stl.fit()
        pd.DataFrame(
            {
                "month": mo["month"].astype(str),
                "trend": res.trend,
                "seasonal": res.seasonal,
                "resid": res.resid,
            }
        ).to_csv(OUTPUT_ADV / "ts_monthly_stl_components.csv", index=False)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(mo["month"].astype(str), y, label="observed")
        ax.plot(mo["month"].astype(str), res.trend, label="trend")
        ax.legend()
        ax.set_title("Monthly net revenue — STL trend vs observed")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        fig.savefig(FIGURES / "adv_monthly_stl.png", dpi=150)
        plt.close()
        report.append(
            "- **STL decomposition (monthly revenue):** `outputs/advanced/ts_monthly_stl_components.csv`, figure `figures/adv_monthly_stl.png`."
        )
    except Exception as e:
        report.append(f"- **STL:** skipped ({e}).")

    # Naive linear-trend forecast (avoids statsmodels ARIMA, which can break on some Python stacks)
    try:
        t = np.arange(len(y), dtype=float)
        coef = np.polyfit(t, y, 1)
        future_t = np.arange(len(y), len(y) + 3, dtype=float)
        forecast = np.polyval(coef, future_t)
        resid = y - np.polyval(coef, t)
        se = float(np.std(resid)) if len(resid) > 1 else 0.0
        pd.DataFrame(
            {
                "step_ahead": [1, 2, 3],
                "forecast_trend": forecast,
                "approx_ci_low": forecast - 1.96 * se,
                "approx_ci_high": forecast + 1.96 * se,
            }
        ).to_csv(OUTPUT_ADV / "ts_linear_trend_forecast_3m.csv", index=False)
        with open(OUTPUT_ADV / "ts_linear_trend_note.txt", "w", encoding="utf-8") as f:
            f.write(
                "Linear trend extrapolation on monthly net revenue (not ARIMA). "
                "CI uses global residual std — for exploration only.\n"
            )
        report.append(
            "- **Monthly trend forecast:** 3-step linear extrapolation in `outputs/advanced/ts_linear_trend_forecast_3m.csv`."
        )
    except Exception as e:
        report.append(f"- **Trend forecast:** skipped ({e}).")

    # Changepoints (PELT)
    try:
        import ruptures as rpt

        signal = y.reshape(-1, 1)
        algo = rpt.Pelt(model="rbf").fit(signal)
        bk = algo.predict(pen=3)
        pd.DataFrame({"changepoint_index_end": bk}).to_csv(
            OUTPUT_ADV / "ts_changepoint_indices.csv", index=False
        )
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(range(len(y)), y, color="steelblue")
        for b in bk[:-1]:
            ax.axvline(b - 1, color="crimson", alpha=0.6)
        ax.set_title("PELT changepoints on monthly revenue")
        fig.savefig(FIGURES / "adv_changepoints.png", dpi=150)
        plt.close()
        report.append("- **Changepoints (PELT):** see `outputs/advanced/ts_changepoint_indices.csv`.")
    except Exception as e:
        report.append(f"- **Changepoints:** skipped ({e}).")


def run_isolation_forest_orders(raw: pd.DataFrame, report: list[str]) -> None:
    """Flag unusual completed orders by amount, items, shipping."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    df = raw[raw["Status"].astype(str).str.lower() == "completed"].copy()
    if len(df) < 50:
        report.append("- **Isolation Forest:** skipped (too few orders).")
        return

    df["_net"] = pd.to_numeric(df.get("Net"), errors="coerce")
    df["_items"] = pd.to_numeric(df.get("Total Items"), errors="coerce")
    df["_ship"] = pd.to_numeric(df.get("Total Shipping"), errors="coerce")
    df = df.dropna(subset=["_net", "_items"])
    X = df[["_net", "_items", "_ship"]].fillna(0).values
    X = np.log1p(np.maximum(X, 0))
    Xs = StandardScaler().fit_transform(X)
    iso = IsolationForest(random_state=42, contamination=0.05)
    pred = iso.fit_predict(Xs)
    df["_anomaly"] = pred
    df["_score"] = iso.score_samples(Xs)
    out = df[
        [
            c
            for c in ["Order ID", "Order Created At", "Net", "Total Items", "Total Shipping"]
            if c in df.columns
        ]
        + ["_anomaly", "_score"]
    ]
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_ADV / "orders_anomaly_isolation_forest.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df["_score"], bins=40, color="teal", alpha=0.85)
    ax.set_title("Isolation Forest anomaly scores (lower = more unusual)")
    plt.tight_layout()
    fig.savefig(FIGURES / "adv_isolation_forest_scores.png", dpi=150)
    plt.close()
    report.append(
        f"- **Isolation Forest:** {int((pred == -1).sum())} flagged unusual orders; `outputs/advanced/orders_anomaly_isolation_forest.csv`."
    )


def run_regression_suite(raw: pd.DataFrame, report: list[str]) -> None:
    """Quantile (median) and Elastic Net regression for Net ~ order features."""
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler
    from statsmodels.regression.linear_model import OLS
    from statsmodels.regression.quantile_regression import QuantReg
    from statsmodels.tools.tools import add_constant

    df = raw[raw["Status"].astype(str).str.lower() == "completed"].copy()
    df["_net"] = pd.to_numeric(df.get("Net"), errors="coerce")
    df["_items"] = pd.to_numeric(df.get("Total Items"), errors="coerce")
    df["_ship"] = pd.to_numeric(df.get("Total Shipping"), errors="coerce")
    df["_disc"] = pd.to_numeric(df.get("Total Discount"), errors="coerce").fillna(0)
    df = df.dropna(subset=["_net", "_items"])
    if len(df) < 40:
        report.append("- **Quantile / Elastic Net:** skipped (too few rows).")
        return

    X = df[["_items", "_ship", "_disc"]].values.astype(float)
    y = df["_net"].values.astype(float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    Xs = StandardScaler().fit_transform(X)

    try:
        ols = OLS(y, add_constant(Xs)).fit()
        with open(OUTPUT_ADV / "regression_ols_net.txt", "w", encoding="utf-8") as f:
            f.write(ols.summary().as_text())
    except Exception:
        pass

    try:
        qr = QuantReg(y, add_constant(Xs)).fit(q=0.5)
        with open(OUTPUT_ADV / "regression_quantile_median_net.txt", "w", encoding="utf-8") as f:
            f.write(qr.summary().as_text())
        report.append("- **Median regression (quantile 0.5):** see `outputs/advanced/regression_quantile_median_net.txt`.")
    except Exception as e:
        report.append(f"- **Quantile regression:** skipped ({e}).")

    try:
        enet = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], cv=5, random_state=42)
        enet.fit(Xs, y)
        coef = pd.DataFrame(
            {
                "feature": ["intercept", "items_scaled", "ship_scaled", "disc_scaled"],
                "coef": np.r_[enet.intercept_, enet.coef_],
            }
        )
        coef.to_csv(OUTPUT_ADV / "regression_elastic_net_coefs.csv", index=False)
        report.append("- **Elastic Net:** coefficients in `outputs/advanced/regression_elastic_net_coefs.csv`.")
    except Exception as e:
        report.append(f"- **Elastic Net:** skipped ({e}).")


def run_gmm_rfm(trans: pd.DataFrame, report: list[str]) -> None:
    """Gaussian mixture on customer RFM-style features."""
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler

    if trans.empty:
        return
    end = trans["date"].max()
    rows = []
    for cid, g in trans.groupby("customer_id"):
        g = g.sort_values("date")
        first = g["date"].min()
        last = g["date"].max()
        freq = len(g) - 1
        rec = (last - first).days if freq > 0 else 0
        T = (end - first).days
        rows.append(
            {
                "customer_id": cid,
                "frequency": freq,
                "recency_days": rec,
                "T_days": max(T, 1),
                "monetary_mean": g["monetary_value"].mean(),
            }
        )
    rfm = pd.DataFrame(rows)
    if len(rfm) < 30:
        report.append("- **GMM (RFM):** skipped (too few customers).")
        return

    X = rfm[["frequency", "recency_days", "T_days", "monetary_mean"]].values.astype(float)
    X = np.log1p(X)
    Xs = StandardScaler().fit_transform(X)
    gmm = GaussianMixture(n_components=min(5, len(rfm) // 10), covariance_type="full", random_state=42)
    gmm.fit(Xs)
    rfm["segment"] = gmm.predict(Xs)
    rfm["segment_prob_max"] = gmm.predict_proba(Xs).max(axis=1)
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    rfm.to_csv(OUTPUT_ADV / "gmm_customer_segments_rfm.csv", index=False)
    report.append(
        f"- **GMM (RFM features):** {gmm.n_components} segments; `outputs/advanced/gmm_customer_segments_rfm.csv`."
    )


def run_pca_hierarchy_customers(trans: pd.DataFrame, report: list[str]) -> None:
    """PCA on customer purchase vectors + hierarchical linkage."""
    from sklearn.decomposition import PCA
    from scipy.cluster import hierarchy
    from scipy.spatial.distance import pdist

    if trans.empty or trans["customer_id"].nunique() < 25:
        report.append("- **PCA / hierarchical clustering:** skipped (too few customers).")
        return

    t = trans.copy()
    t["_m"] = t["date"].dt.to_period("M")
    wide = t.pivot_table(
        index="customer_id",
        columns="_m",
        values="monetary_value",
        aggfunc="sum",
        fill_value=0,
    )
    if wide.shape[1] > 36:
        wide = wide.iloc[:, -36:]
    if wide.shape[0] < 15 or wide.shape[1] < 2:
        report.append("- **PCA / hierarchy:** skipped (sparse matrix).")
        return

    X = wide.values.astype(float)
    X = np.log1p(X)
    from sklearn.preprocessing import StandardScaler

    Xs = StandardScaler().fit_transform(X)
    n_comp = min(8, Xs.shape[1], Xs.shape[0] - 1)
    n_comp = max(2, n_comp)
    pca = PCA(n_components=n_comp)
    Z = pca.fit_transform(Xs)
    expl = pd.DataFrame(
        {"component": [f"PC{i+1}" for i in range(n_comp)], "variance_ratio": pca.explained_variance_ratio_}
    )
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    expl.to_csv(OUTPUT_ADV / "pca_customer_variance.csv", index=False)
    cust_z = pd.DataFrame(Z, index=wide.index, columns=[f"PC{i+1}" for i in range(n_comp)])
    cust_z.to_csv(OUTPUT_ADV / "pca_customer_scores.csv")

    Zs = StandardScaler().fit_transform(Z)
    d = pdist(Zs, metric="euclidean")
    link = hierarchy.linkage(d, method="ward")
    pd.DataFrame(link, columns=["c1", "c2", "dist", "count"]).to_csv(
        OUTPUT_ADV / "hierarchy_linkage_matrix.csv", index=False
    )
    report.append(
        "- **PCA + hierarchical (Ward):** see `outputs/advanced/pca_customer_*.csv` and `hierarchy_linkage_matrix.csv`."
    )


def run_postcode_clustering(postcode_path: Path, report: list[str]) -> None:
    """Hierarchical clustering on ZIP aggregate metrics."""
    from scipy.cluster import hierarchy
    from scipy.spatial.distance import pdist
    from sklearn.preprocessing import StandardScaler

    if not postcode_path.exists():
        return
    df = pd.read_csv(postcode_path)
    num = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(num) < 2 or len(df) < 15:
        report.append("- **ZIP clustering:** skipped.")
        return
    X = df[num].fillna(0).values.astype(float)
    X = np.log1p(np.maximum(X, 0))
    Xs = StandardScaler().fit_transform(X)
    d = pdist(Xs, metric="euclidean")
    link = hierarchy.linkage(d, method="average")
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(link, columns=["c1", "c2", "dist", "count"]).to_csv(
        OUTPUT_ADV / "hierarchy_postcode_linkage.csv", index=False
    )
    report.append("- **ZIP feature clustering:** linkage saved to `outputs/advanced/hierarchy_postcode_linkage.csv`.")


def run_bootstrap_mannwhitney(raw: pd.DataFrame, report: list[str]) -> None:
    """Bootstrap CI for mean order net; Mann–Whitney between top two billing states."""
    from scipy.stats import bootstrap, mannwhitneyu

    df = raw[raw["Status"].astype(str).str.lower() == "completed"].copy()
    df["_net"] = pd.to_numeric(df.get("Net"), errors="coerce")
    df["_st"] = df.get("Billing Address State", pd.Series("", index=df.index)).astype(str)
    df = df.dropna(subset=["_net"])
    nets = df["_net"].values.astype(float)
    if len(nets) < 30:
        return
    rng = np.random.default_rng(42)

    def _mean(x, axis=None, **kwargs):
        return np.mean(x, axis=axis)

    try:
        res = bootstrap((nets,), _mean, rng=rng, confidence_level=0.95, method="percentile")
        pd.DataFrame(
            {
                "metric": ["mean_net_order"],
                "point": [float(np.mean(nets))],
                "ci_low": [float(res.confidence_interval.low)],
                "ci_high": [float(res.confidence_interval.high)],
            }
        ).to_csv(OUTPUT_ADV / "bootstrap_mean_net_order_95ci.csv", index=False)
        report.append(
            "- **Bootstrap 95% CI (mean net order):** `outputs/advanced/bootstrap_mean_net_order_95ci.csv`."
        )
    except Exception as e:
        report.append(f"- **Bootstrap:** skipped ({e}).")

    try:
        top = df.groupby("_st")["_net"].count().sort_values(ascending=False).head(3).index.tolist()
        if len(top) >= 2:
            a = df[df["_st"] == top[0]]["_net"].values
            b = df[df["_st"] == top[1]]["_net"].values
            if len(a) >= 8 and len(b) >= 8:
                stat, p = mannwhitneyu(a, b, alternative="two-sided")
                pd.DataFrame(
                    {
                        "state_a": [top[0]],
                        "state_b": [top[1]],
                        "mannwhitney_statistic": [stat],
                        "p_value_two_sided": [p],
                        "n_a": [len(a)],
                        "n_b": [len(b)],
                    }
                ).to_csv(OUTPUT_ADV / "mannwhitney_top2_states_net.csv", index=False)
                report.append(
                    f"- **Mann–Whitney (net order, {top[0]} vs {top[1]}):** `outputs/advanced/mannwhitney_top2_states_net.csv`."
                )
    except Exception as e:
        report.append(f"- **Mann–Whitney:** skipped ({e}).")


def run_correlation_product_export(products_path: Path, report: list[str]) -> None:
    """Correlation matrix of numeric product columns."""
    if not products_path.exists():
        return
    df = pd.read_csv(products_path, low_memory=False)
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return
    c = num.corr()
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    c.to_csv(OUTPUT_ADV / "corr_product_numeric.csv")
    report.append("- **Correlation (product export numerics):** `outputs/advanced/corr_product_numeric.csv`.")


def run_advanced_all(
    raw: pd.DataFrame | None,
    mo: pd.DataFrame | None,
    postcode_path: Path,
    products_path: Path,
    report_lines: list[str],
) -> None:
    OUTPUT_ADV.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ADV / "README.txt").write_text(
        "Advanced model outputs (BG/NBD, STL, ARIMA, isolation forest, regressions, GMM, PCA, clustering).\n",
        encoding="utf-8",
    )

    run_correlation_product_export(products_path, report_lines)
    run_postcode_clustering(postcode_path, report_lines)

    if raw is None or raw.empty:
        report_lines.append("- **Advanced order-level models:** skipped (no order export).")
        return

    trans = _transactions_from_orders(raw)
    run_clv_lifetimes(trans, report_lines)
    run_gmm_rfm(trans, report_lines)
    run_pca_hierarchy_customers(trans, report_lines)
    run_isolation_forest_orders(raw, report_lines)
    run_regression_suite(raw, report_lines)
    run_bootstrap_mannwhitney(raw, report_lines)
    run_time_series_monthly(mo if mo is not None else pd.DataFrame(), report_lines)
