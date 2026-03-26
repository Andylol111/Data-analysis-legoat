# Output file guide (`outputs/`)

Short descriptions of what each artifact **is** and **how to use it** for decisions.

## Core report

| File | Description |
|------|-------------|
| `REPORT.md` | Auto-generated bullet summary after each `run_analysis.py`: counts, filters applied, and which modules ran. |

## Association & bundles

| File | Description |
|------|-------------|
| `association_rules_all_pairs.csv` | **Support**, **confidence**, **lift** for every product pair in the Woo “bought together” extract. |
| `association_rules_filtered.csv` | Same metrics with **minimum orders per SKU** and **minimum co-purchases** to reduce noise from rare items. |
| `pairs_aggregated_by_product_ids.csv` | Raw pair counts summed when the same pair appears under multiple variation IDs. |
| `co_purchase_top_edges.csv` | Heaviest edges in the **product co-purchase network** (good for merchandising bundles). |
| `co_purchase_centrality.csv` | **Weighted degree** and **betweenness** — which SKUs sit in the middle of many bundles. |

## Matrix factorization

| File | Description |
|------|-------------|
| `product_cooccurrence_matrix.csv` | Square matrix: off-diagonal = co-purchase counts; diagonal ≈ orders containing that SKU. |
| `nmf_product_loadings.csv` | **NMF** factors over that matrix — latent “affinity” dimensions among products (not dollars). |

## Cohorts & geography (aggregates)

| File | Description |
|------|-------------|
| `first_product_cohorts_full.csv` / `first_product_cohorts_top40.csv` | Customers grouped by **first product purchased** — AOV, repeat rate, etc. |
| `postcode_cohorts_full.csv` / `postcode_top30_spend.csv` | **Billing ZIP** rollups from Woo (aggregate cohort, not order lines). |
| `annual_orders_subscriptions.csv` | **Year-level** orders merged with subscription event counts. |

## Order export pipeline (when `data/orders_export_no_pii.csv` exists)

| File | Description |
|------|-------------|
| `order_line_items_long.csv` | One row per line item: order id, product name, qty, customer key, billing state/ZIP, net. |
| `revenue_by_billing_state.csv` | **Completed** orders: net revenue and order count by state. |
| `revenue_by_month.csv` | **Completed** orders: net revenue by calendar month. |
| `apriori_frequent_itemsets.csv` | **Frequent itemsets** mined from real baskets (parsed line items). |
| `apriori_association_rules.csv` | **Association rules** from those itemsets (confidence, lift, etc.). |
| `lda_customer_topic_weights.csv` | Per-customer **topic mixture** from LDA over product counts. |
| `lda_topic_product_loadings.csv` | Topic → product weights (interpret personas / themes). |

## Analytics index (for LLM + dashboard)

| File | Description |
|------|-------------|
| `analytics_index.json` | Machine-readable list of datasets, columns, and row counts (regenerated with analysis). |

## GA4

| Path | Description |
|------|-------------|
| `ga_tables/*.csv` | Parsed sections from the GA snapshot export (users, channels, countries, etc.). |
| `ga_daily_active_users_series.csv` | Daily active users series when a matching block exists in the snapshot. |

## Figures (`outputs/figures/`)

PNG charts (annual revenue, subscription signups vs cancels, ZIP spend distribution, NMF factor bars, GA daily, state/month revenue from orders). Filenames match the analysis step that produced them.

## Advanced models (`outputs/advanced/`)

Generated when `data/orders_export_no_pii.csv` exists (plus product/postcode aggregates where noted).

| File | Description |
|------|-------------|
| `clv_rfm_summary.csv` / `clv_customer_estimates.csv` | **BG/NBD** survival + **Gamma–Gamma** monetary model (via `lifetimes`); **p(alive)**, expected purchases, **CLV** where GG fits. |
| `gmm_customer_segments_rfm.csv` | **Gaussian mixture** on log-scaled RFM-style features — soft segments. |
| `pca_customer_variance.csv` / `pca_customer_scores.csv` | **PCA** on customer × month spend matrix; scores for clustering. |
| `hierarchy_linkage_matrix.csv` | **Hierarchical (Ward)** linkage on PCA scores (customer level). |
| `hierarchy_postcode_linkage.csv` | **Hierarchical** linkage on numeric **ZIP cohort** columns. |
| `orders_anomaly_isolation_forest.csv` | **Isolation Forest** flags on log(order net, items, shipping). |
| `regression_ols_net.txt` / `regression_quantile_median_net.txt` | **OLS** and **median (LAD)** regression: Net ~ items, shipping, discount. |
| `regression_elastic_net_coefs.csv` | **Elastic Net** coefficients (same features). |
| `bootstrap_mean_net_order_95ci.csv` | **Bootstrap** 95% CI for mean net order. |
| `mannwhitney_top2_states_net.csv` | **Mann–Whitney** test: net order in top two states by volume. |
| `ts_monthly_stl_components.csv` | **STL** trend/seasonal/residual on monthly revenue. |
| `ts_linear_trend_forecast_3m.csv` | **Naive linear trend** 3-month extrapolation (not ARIMA — avoids fragile stacks). |
| `ts_changepoint_indices.csv` | **PELT** changepoint indices (`ruptures`) on monthly series. |
| `corr_product_numeric.csv` | Pearson **correlation** of numeric columns in the product export. |
