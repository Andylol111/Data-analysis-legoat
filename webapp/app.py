#!/usr/bin/env python3
"""Local dashboard for FireFly Farms analysis outputs."""
from __future__ import annotations

import io
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, abort, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import markdown as md_lib

    HAS_MD = True
except ImportError:
    HAS_MD = False

from webapp.chart_logic import compute_chart
from webapp.context_build import build_llm_context, ollama_chat, system_prompt

OUTPUT = ROOT / "outputs"
DOCS = ROOT / "docs"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


def _md_file(path: Path) -> str:
    if not path.exists():
        return "<p>Missing document.</p>"
    text = path.read_text(encoding="utf-8", errors="replace")
    if HAS_MD:
        return md_lib.markdown(text, extensions=["tables", "fenced_code"])
    return f"<pre>{text}</pre>"


def _safe_output_path(rel: str) -> Path | None:
    if ".." in rel or rel.startswith("/"):
        return None
    p = (OUTPUT / rel).resolve()
    try:
        p.relative_to(OUTPUT.resolve())
    except ValueError:
        return None
    if not p.is_file():
        return None
    return p


def _walk_outputs() -> list[dict]:
    import os

    rows = []
    if not OUTPUT.exists():
        return rows
    for dirpath, _dirnames, filenames in os.walk(OUTPUT):
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(OUTPUT).as_posix()
            ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
            rows.append(
                {
                    "rel": rel,
                    "name": name,
                    "ext": ext,
                    "size_kb": round(full.stat().st_size / 1024, 1),
                }
            )
    return sorted(rows, key=lambda x: (x["ext"], x["rel"]))


@app.route("/")
def index():
    report_html = ""
    report_path = OUTPUT / "REPORT.md"
    if report_path.exists() and HAS_MD:
        text = report_path.read_text(encoding="utf-8", errors="replace")
        report_html = md_lib.markdown(text, extensions=["tables", "fenced_code"])
    elif report_path.exists():
        report_html = f"<pre>{report_path.read_text(encoding='utf-8', errors='replace')}</pre>"

    files = _walk_outputs()
    figures = [f for f in files if f["ext"] == "png"]
    tables = [f for f in files if f["ext"] == "csv"]
    other = [f for f in files if f["ext"] not in ("png", "csv", "md")]

    return render_template(
        "index.html",
        report_html=report_html,
        figures=figures,
        tables=tables,
        other=other,
    )


@app.route("/guide")
def guide():
    return render_template(
        "page_md.html",
        title="Data dictionary",
        body_html=_md_file(DOCS / "DATA_DICTIONARY.md"),
    )


@app.route("/methods")
def methods():
    return render_template(
        "page_md.html",
        title="Eleven methods — status",
        body_html=_md_file(DOCS / "METHODS_STATUS.md"),
    )


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/preview/<path:rel>")
def preview_csv(rel: str):
    p = _safe_output_path(rel)
    if not p or p.suffix.lower() != ".csv":
        abort(404)
    try:
        df = pd.read_csv(p, low_memory=False)
    except Exception as e:
        return f"<pre>Error reading CSV: {e}</pre>", 500
    n = len(df)
    head = df.head(500)
    html = head.to_html(
        classes="data-table",
        index=False,
        border=0,
        justify="left",
        escape=True,
    )
    title = p.name
    return render_template(
        "preview.html",
        title=title,
        rel=rel,
        table_html=html,
        total_rows=n,
        shown=min(500, n),
    )


@app.route("/raw/<path:rel>")
def raw_file(rel: str):
    p = _safe_output_path(rel)
    if not p:
        abort(404)
    return send_file(p, as_attachment=False)


@app.route("/download/<path:rel>")
def download(rel: str):
    p = _safe_output_path(rel)
    if not p:
        abort(404)
    return send_file(p, as_attachment=True, download_name=p.name)


def _collect_csv_paths() -> list[tuple[Path, str]]:
    """Return (path, rel) for every CSV under outputs/."""
    out: list[tuple[Path, str]] = []
    if not OUTPUT.exists():
        return out
    for dirpath, _dirnames, filenames in os.walk(OUTPUT):
        for name in sorted(filenames):
            if not name.lower().endswith(".csv"):
                continue
            full = Path(dirpath) / name
            if not full.is_file():
                continue
            rel = full.relative_to(OUTPUT).as_posix()
            out.append((full, rel))
    return out


@app.route("/export/all-csvs.zip")
def export_all_csvs_zip():
    """Zip every CSV under outputs/."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in _collect_csv_paths():
            zf.write(full, arcname=rel)
    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"firefly_all_csvs_{ts}.zip"
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=fname,
        max_age=0,
    )


@app.route("/export/all-csvs-merged.csv")
def export_all_csvs_merged():
    """Download a single CSV with all outputs concatenated; rows tagged with _source column."""
    dfs: list[pd.DataFrame] = []
    for full, rel in _collect_csv_paths():
        try:
            df = pd.read_csv(full, low_memory=False)
            df.insert(0, "_source", rel)
            dfs.append(df)
        except Exception:
            continue
    if not dfs:
        abort(404)
    merged = pd.concat(dfs, axis=0, ignore_index=True)
    buf = io.BytesIO()
    merged.to_csv(buf, index=False, date_format="%Y-%m-%d")
    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"firefly_all_csvs_merged_{ts}.csv"
    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
        max_age=0,
    )


@app.route("/export/all-figures.zip")
def export_all_figures_zip():
    """Zip every PNG under outputs/ (figures + any other charts)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if OUTPUT.exists():
            for dirpath, _dirnames, filenames in os.walk(OUTPUT):
                for name in sorted(filenames):
                    if not name.lower().endswith(".png"):
                        continue
                    full = Path(dirpath) / name
                    if not full.is_file():
                        continue
                    rel = full.relative_to(OUTPUT).as_posix()
                    zf.write(full, arcname=rel)
    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"firefly_all_figures_{ts}.zip"
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=fname,
        max_age=0,
    )


# --- APIs ---


@app.route("/api/datasets")
def api_datasets():
    """List CSV datasets under outputs/ with columns."""
    idx = OUTPUT / "analytics_index.json"
    if idx.exists():
        import json

        return jsonify(json.loads(idx.read_text(encoding="utf-8")))
    # fallback: build on the fly
    from src.analytics_index import build_index

    return jsonify(build_index(OUTPUT))


@app.route("/api/chart-data", methods=["POST"])
def api_chart_data():
    body = request.get_json(force=True, silent=True) or {}
    rel = body.get("file") or body.get("rel")
    x = body.get("x")
    y = body.get("y")
    chart = (body.get("chart") or "bar").lower()
    agg = (body.get("agg") or "none").lower()
    limit = int(body.get("limit") or 80)
    if not rel or not x or not y:
        return jsonify({"error": "file, x, y required"}), 400
    p = _safe_output_path(rel)
    if not p:
        return jsonify({"error": "file not found"}), 404
    try:
        df = pd.read_csv(p, low_memory=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    try:
        payload = compute_chart(df, x, y, chart, agg=agg, limit=limit)
        payload["rows_available"] = len(df)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Local Ollama only; answers grounded in build_llm_context()."""
    body = request.get_json(force=True, silent=True) or {}
    user_msg = (body.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "message required"}), 400

    context = build_llm_context()
    messages = [
        {"role": "system", "content": system_prompt()},
        {
            "role": "user",
            "content": f"CONTEXT (authoritative — only use this for facts and file names):\n\n{context}\n\n---\nQUESTION:\n{user_msg}",
        },
    ]
    reply, err = ollama_chat(messages)
    if err:
        return jsonify(
            {
                "reply": None,
                "error": err,
                "hint": "Install and run Ollama locally, then: ollama pull llama3.2  (set OLLAMA_MODEL if needed)",
            }
        ), 503
    return jsonify({"reply": reply, "error": None})


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:5050  (outputs: {OUTPUT})")
    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=True)
