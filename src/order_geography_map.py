"""Geographic heatmap of orders by billing state (bubble map on state centroids)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from src.state_geo import (
    CONUS_STATES,
    FIREFLY_FARM_LABEL,
    FIREFLY_FARM_LAT,
    FIREFLY_FARM_LON,
    STATE_CENTROIDS,
    normalize_state_abbrev,
)


def plot_order_geography_heatmap(
    state_revenue: pd.DataFrame,
    out: Path,
    state_col: str | None = None,
    revenue_col: str = "net_revenue",
    orders_col: str = "n_orders",
    dpi: int = 150,
) -> bool:
    """
    Bubble map: position = state center, color = net revenue, size = order count.
    Highlights FireFly Farms in western Maryland.
    """
    if state_revenue is None or state_revenue.empty:
        return False
    df = state_revenue.copy()
    if state_col is None:
        state_col = df.columns[0]
    df["_abbr"] = df[state_col].apply(normalize_state_abbrev)
    df = df[df["_abbr"].notna()]
    if df.empty:
        return False

    plot_df = df[df["_abbr"].isin(CONUS_STATES)].copy()
    if plot_df.empty:
        plot_df = df.copy()

    lon = []
    lat = []
    rev = []
    n_ord = []
    labels = []
    for _, r in plot_df.iterrows():
        abbr = r["_abbr"]
        lo, la = STATE_CENTROIDS[abbr]
        lon.append(lo)
        lat.append(la)
        rev.append(float(pd.to_numeric(r.get(revenue_col), errors="coerce") or 0.0))
        n_ord.append(float(pd.to_numeric(r.get(orders_col), errors="coerce") or 0.0))
        labels.append(abbr)

    lon = np.array(lon)
    lat = np.array(lat)
    rev = np.array(rev)
    n_ord = np.array(n_ord)

    n_max = float(n_ord.max()) if n_ord.size and n_ord.max() > 0 else 1.0
    sizes = 80.0 + 700.0 * (n_ord / n_max)

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_facecolor("#e8eef2")

    vmax = max(float(rev.max()), 1.0)
    sc = ax.scatter(
        lon,
        lat,
        s=sizes,
        c=rev,
        cmap="YlOrRd",
        alpha=0.85,
        edgecolors="#333333",
        linewidths=0.6,
        zorder=3,
        vmin=0.0,
        vmax=vmax,
    )

    fig.colorbar(sc, ax=ax, shrink=0.7, label="Net revenue ($) — completed orders")

    for lo, la, ab, rr, nn in zip(lon, lat, labels, rev, n_ord):
        ax.annotate(
            ab,
            (lo, la),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="#1a1a1a",
            zorder=4,
        )

    ax.scatter(
        [FIREFLY_FARM_LON],
        [FIREFLY_FARM_LAT],
        s=420,
        marker="*",
        c="#c41e3a",
        edgecolors="white",
        linewidths=1.6,
        zorder=6,
        label=FIREFLY_FARM_LABEL,
    )
    ax.annotate(
        "Farm",
        (FIREFLY_FARM_LON, FIREFLY_FARM_LAT),
        textcoords="offset points",
        xytext=(8, -12),
        fontsize=9,
        fontweight="bold",
        color="#c41e3a",
        zorder=7,
    )

    alaska_hi_note = []
    for special in ("AK", "HI"):
        if special in df["_abbr"].values and special not in plot_df["_abbr"].values:
            row = df[df["_abbr"] == special].iloc[0]
            alaska_hi_note.append(
                f"{special}: {int(row.get(orders_col, 0))} orders, "
                f"${float(row.get(revenue_col, 0)):,.0f} net"
            )

    ax.set_xlim(-127, -65)
    ax.set_ylim(23, 51)
    ax.set_xlabel("Longitude (°W)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("Where orders ship — billing state volume & revenue (bubble heat)")
    ax.grid(True, alpha=0.35, linestyle="--")
    ax.set_aspect("equal", adjustable="box")

    legend_elems = [
        Line2D(
            [0],
            [0],
            marker="*",
            color="w",
            markerfacecolor="#c41e3a",
            markersize=16,
            markeredgecolor="white",
            label=FIREFLY_FARM_LABEL,
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#d95f02",
            markersize=10,
            markeredgecolor="#333",
            label="Bubble size ∝ order count; color ∝ net revenue",
        ),
    ]
    ax.legend(handles=legend_elems, loc="lower left", framealpha=0.92)

    if alaska_hi_note:
        fig.text(
            0.5,
            0.02,
            " • ".join(alaska_hi_note),
            ha="center",
            fontsize=8,
            style="italic",
        )

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close()
    return True
