# Status: eleven advanced analytics methods

This project’s **implemented** pieces vs **roadmap** items, tied to **data you have** vs **data still needed**.

| # | Method | Status | In this codebase | What unlocks “full” use |
|---|--------|--------|-------------------|-------------------------|
| 1 | **LDA** (purchase personas) | **Partial** | Customer-level LDA when `data/orders_export_no_pii.csv` is present; topics over product tokens | More history; consistent product taxonomy |
| 2 | **Apriori / FP-Growth** | **Implemented** | `mlxtend` on parsed order baskets + pre-aggregated pair rules from Woo | Already strong at pair level |
| 3 | **HMM** (subscription states) | **Not implemented** | — | Per-subscriber event timeline (renewals, pauses, skips) |
| 4 | **Moran’s I** (spatial autocorrelation) | **Partial** | ZIP/state summaries from orders; no spatial weights file yet | Polygon/neighbor matrix + aligned regional metrics |
| 5 | **GWR** | **Not implemented** | — | Same as Moran’s + covariates at geography + enough regions |
| 6 | **Cox** (survival / churn) | **Not implemented** | — | Subscription start/end per customer |
| 7 | **CCA** (segmentation × sales) | **Not implemented** | — | Same units for GA + sales (e.g. region × time) |
| 8 | **VAR** (multi-series dynamics) | **Partial** | Monthly revenue series from orders; GA daily series | Longer monthly commercial history |
| 9 | **NMF** (region × product archetypes) | **Partial** | Product–product NMF from co-purchase matrix | Region × product matrix |
| 10 | **GMM** (spend / behavior clusters) | **Not implemented** | — | Customer feature matrix (orders + mix + geo) |
| 11 | **DTW + hierarchical clustering** | **Not implemented** | — | Region (or SKU) × time panel at week/month frequency |

**Summary:** Pipelines **1, 2, 9** are partially covered; **4, 8** have building blocks; **3, 5, 6, 7, 10, 11** need additional exports or engineering. The dashboard and chat assistant are **grounded only on files under `outputs/`** and this status document.

---

## Automated pipeline (this repo, `run_analysis.py`)

When `orders_export_no_pii.csv` is present, the following are **also** written under `outputs/advanced/`:

| Method family | Implementation |
|---------------|------------------|
| **CLV / repeat purchase** | BG/NBD + Gamma–Gamma (`lifetimes`) |
| **GMM** | `sklearn.mixture.GaussianMixture` on RFM features |
| **PCA + hierarchical clustering** | Customer × month matrix → PCA → Ward linkage |
| **Anomaly detection** | Isolation Forest on order features |
| **Regression** | OLS, median quantile regression, Elastic Net |
| **Nonparametric** | Bootstrap CI for mean net; Mann–Whitney between top states |
| **Time series** | STL on monthly revenue; linear trend forecast; PELT changepoints |
| **Correlation** | Numeric columns in product export |
| **ZIP clustering** | Hierarchical linkage on postcode aggregate numerics |
