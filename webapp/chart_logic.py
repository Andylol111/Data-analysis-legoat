"""Turn two columns from a dataframe into Chart.js-friendly payloads."""
from __future__ import annotations

import pandas as pd


def compute_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    chart: str,
    agg: str = "none",
    limit: int = 80,
) -> dict:
    if x not in df.columns or y not in df.columns:
        raise ValueError(f"Columns not found: {x}, {y}")

    d = df[[x, y]].copy()
    d[y] = pd.to_numeric(d[y], errors="coerce")
    d = d.dropna(subset=[y])

    if chart == "bar":
        if agg in ("sum", "mean"):
            g = d.groupby(x, dropna=False)[y].agg(agg).reset_index()
            g = g.sort_values(y, ascending=False).head(limit)
        else:
            g = d.sort_values(y, ascending=False).head(limit)
        return {
            "type": "bar",
            "labels": [str(v) for v in g[x].tolist()],
            "values": [float(v) for v in g[y].tolist()],
        }

    if chart == "line":
        g = d.sort_values(x).head(min(limit * 5, 2000))
        return {
            "type": "line",
            "labels": [str(v) for v in g[x].tolist()],
            "values": [float(v) for v in g[y].tolist()],
        }

    if chart == "scatter":
        g = d.dropna(subset=[x])
        g[x] = pd.to_numeric(g[x], errors="coerce")
        g = g.dropna(subset=[x, y]).head(min(2000, len(d)))
        return {
            "type": "scatter",
            "points": [
                {"x": float(r[x]), "y": float(r[y])} for _, r in g.iterrows()
            ],
        }

    raise ValueError(f"Unknown chart type: {chart}")
