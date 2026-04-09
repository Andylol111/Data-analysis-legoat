# FireFly Farms — aggregate data analysis

Runnable analytics on WooCommerce + GA4 exports, plus optional **`data/orders_export_no_pii.csv`** (sanitized orders with line items) for baskets, LDA, and geo/time summaries.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run (analysis only)

```bash
python3 run_analysis.py
```

## Local dashboard (analysis + web UI)

```bash
./startall.sh
```

Installs dependencies (in `.venv`), runs `run_analysis.py`, then serves **`http://127.0.0.1:5050`** with the report, charts, and browsable CSV previews from `outputs/`. On the **home** page, **Download all figures (ZIP)** grabs every PNG under `outputs/`. Stop with `Ctrl+C`.

### Order heatmap (interactive, free)

Open **`http://127.0.0.1:5050/map`** after analysis has produced `outputs/revenue_by_billing_state.csv`.

The map uses **[Leaflet](https://leafletjs.com/)** + **[OpenStreetMap](https://www.openstreetmap.org/)** tiles + a heat layer. **No API keys, no Google account, no map billing.** Use responsibly per the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/) (this app is a small local dashboard; for heavy traffic you’d host your own tile server).

## Outputs

Outputs land in **`outputs/`**:

| Output | Description |
|--------|-------------|
| `association_rules_all_pairs.csv` | Support, confidence, lift for every mined pair |
| `association_rules_filtered.csv` | Same metrics with **min 15 orders** per SKU and **min 5** co-purchases (reduces rare-SKU noise) |
| `co_purchase_top_edges.csv` / `co_purchase_centrality.csv` | Weighted graph summary |
| `product_cooccurrence_matrix.csv` | Symmetric co-occurrence + diagonal = net orders |
| `nmf_product_loadings.csv` | NMF factors over product affinity matrix |
| `annual_orders_subscriptions.csv` | Yearly orders joined to subscription events |
| `first_product_cohorts_*.csv` | First-product acquisition cohorts |
| `postcode_*.csv` | Billing ZIP aggregates |
| `ga_tables/*.csv` | Parsed GA4 snapshot sections |
| `figures/*.png` | Charts |
| `REPORT.md` | Short summary |
| `order_line_items_long.csv`, `revenue_by_month.csv`, … | Present when `orders_export_no_pii.csv` is in `data/` |
| `advanced/*.csv` (and related `.txt`) | **Extra models** on order + product + ZIP data: CLV (BG/NBD+GG), GMM, PCA, isolation forest, regressions, bootstrap, Mann–Whitney, STL, changepoints — see `docs/DATA_DICTIONARY.md` |

## Data

Place CSV exports in **`data/`** (see `src/config.py`). Use **`orders_export_no_pii.csv`** for the order-level file — it must be the **sanitized** export (no names, emails, phones, street addresses, or IPs). Replace that file when you refresh from WooCommerce.

## Custom charts & local LLM

- **`/dashboard`** — Pick any CSV under `outputs/`, choose **X** / **Y**, chart type (bar, line, scatter), optional aggregate. Renders in the browser via Chart.js. **Export all** downloads the current chart as **PNG** plus the plotted series as **CSV**.
- **Assistant** — Uses **[Ollama](https://ollama.com)** on `127.0.0.1` (default model `llama3.2`, override with `OLLAMA_MODEL`). The app injects **only** text built from `outputs/` + `docs/METHODS_STATUS.md` + sampled rows — it does not browse the web or use API keys. Install Ollama, run `ollama pull llama3.2`, then use **Custom charts** → ask a question.

## Production (WSGI)

Do **not** expose to the internet without TLS and authentication in front.

```bash
cd /path/to/Data-analysis-legoat
source .venv/bin/activate
pip install -r requirements.txt
python3 -m gunicorn -w 4 -b 127.0.0.1:5050 --timeout 120 "wsgi:app"
```

Use **`python3 -m gunicorn`** (not bare `gunicorn`) so the interpreter that has Gunicorn installed is the one that runs it. Or run **`./startprod.sh`**, which does that for you.

Or use a Unix socket + reverse proxy (nginx, Caddy). Entry point: **`wsgi:app`** at the repo root.

## Eleven methods

See **`docs/METHODS_STATUS.md`** and the in-app **11 methods status** page (`/methods`).
