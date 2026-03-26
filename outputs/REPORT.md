# FireFly Farms — automated analysis report

Generated from bundled WooCommerce + GA exports (aggregate + order-level where available).



- **Total orders (all years in export):** 1214

- **ZIP cohorts:** 389 postcodes; total spend ≈ $112,645

- **Association rules:** 361 pairs scored; 62 after filter (min 15 orders each side, min 5 co-purchases).

- **NMF** on product co-occurrence (+ diagonal net orders): see `outputs/nmf_product_loadings.csv`.

- **GA tables parsed:** 16 sections saved under `outputs/ga_tables/`.

- **Order export:** 1767 rows; exploded line rows: 5837.

- **Apriori (from parsed line items):** 70 frequent itemsets; 29 rules.

- **LDA (customer purchase personas):** 243 customers × 35 products; 6 topics.

- **Correlation (product export numerics):** `outputs/advanced/corr_product_numeric.csv`.

- **ZIP feature clustering:** linkage saved to `outputs/advanced/hierarchy_postcode_linkage.csv`.

- **CLV (BG/NBD + Gamma-Gamma):** 537 customers; see `outputs/advanced/clv_customer_estimates.csv`.

- **GMM (RFM features):** 5 segments; `outputs/advanced/gmm_customer_segments_rfm.csv`.

- **PCA + hierarchical (Ward):** see `outputs/advanced/pca_customer_*.csv` and `hierarchy_linkage_matrix.csv`.

- **Isolation Forest:** 60 flagged unusual orders; `outputs/advanced/orders_anomaly_isolation_forest.csv`.

- **Median regression (quantile 0.5):** see `outputs/advanced/regression_quantile_median_net.txt`.

- **Elastic Net:** coefficients in `outputs/advanced/regression_elastic_net_coefs.csv`.

- **Bootstrap 95% CI (mean net order):** `outputs/advanced/bootstrap_mean_net_order_95ci.csv`.

- **Mann–Whitney (net order, MD vs PA):** `outputs/advanced/mannwhitney_top2_states_net.csv`.

- **STL decomposition (monthly revenue):** `outputs/advanced/ts_monthly_stl_components.csv`, figure `figures/adv_monthly_stl.png`.

- **Monthly trend forecast:** 3-step linear extrapolation in `outputs/advanced/ts_linear_trend_forecast_3m.csv`.

- **Changepoints (PELT):** see `outputs/advanced/ts_changepoint_indices.csv`.