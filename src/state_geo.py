"""US state centroids, farm location, and JSON for web heatmaps (no matplotlib)."""
from __future__ import annotations

import pandas as pd

# FireFly Farms Creamery — Accident, Garrett County, MD (visit center)
FIREFLY_FARM_LAT = 39.6280
FIREFLY_FARM_LON = -79.3197
FIREFLY_FARM_LABEL = "FireFly Farms (Accident, MD)"

# USPS abbreviation -> (longitude, latitude) approximate geographic center
STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AL": (-86.8287, 32.7895),
    "AK": (-149.4937, 64.2008),
    "AZ": (-111.6602, 34.2744),
    "AR": (-92.4426, 34.8938),
    "CA": (-119.7731, 36.7783),
    "CO": (-105.7821, 39.1130),
    "CT": (-72.7273, 41.5978),
    "DE": (-75.5277, 38.9897),
    "DC": (-77.0268, 38.9133),
    "FL": (-82.4572, 27.6648),
    "GA": (-83.7143, 32.6781),
    "HI": (-155.5828, 19.8968),
    "ID": (-114.6444, 44.3893),
    "IL": (-89.3985, 40.3495),
    "IN": (-86.2583, 39.8494),
    "IA": (-93.2151, 42.0115),
    "KS": (-98.4842, 38.5266),
    "KY": (-85.2983, 37.6681),
    "LA": (-91.8749, 30.9843),
    "ME": (-69.2478, 45.2538),
    "MD": (-76.8021, 39.0639),
    "MA": (-71.5376, 42.2352),
    "MI": (-85.6024, 43.3266),
    "MN": (-94.6859, 45.6945),
    "MS": (-89.6678, 32.7416),
    "MO": (-92.2884, 38.4561),
    "MT": (-110.4544, 46.9219),
    "NE": (-99.9018, 41.4925),
    "NV": (-116.4194, 38.8026),
    "NH": (-71.5653, 43.4525),
    "NJ": (-74.5210, 40.2989),
    "NM": (-106.2485, 34.5199),
    "NY": (-74.9481, 42.1657),
    "NC": (-79.3877, 35.6301),
    "ND": (-101.0020, 47.5289),
    "OH": (-82.7649, 40.3887),
    "OK": (-97.5085, 35.5653),
    "OR": (-122.0709, 43.8041),
    "PA": (-77.2098, 41.2033),
    "RI": (-71.5118, 41.6809),
    "SC": (-80.9066, 33.8569),
    "SD": (-99.9018, 44.2998),
    "TN": (-86.7816, 35.7478),
    "TX": (-99.9018, 31.0545),
    "UT": (-111.8926, 40.1500),
    "VT": (-72.7317, 44.0459),
    "VA": (-78.1694, 37.7693),
    "WA": (-121.4944, 47.4009),
    "WV": (-80.9696, 38.4752),
    "WI": (-89.6165, 44.2619),
    "WY": (-107.3025, 42.7557),
}

CONUS_STATES = frozenset(STATE_CENTROIDS) - {"AK", "HI"}

_LONG_TO_ABBR = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}


def normalize_state_abbrev(s: str) -> str | None:
    if not s or not isinstance(s, str):
        return None
    t = s.strip().upper()
    if len(t) == 2 and t in STATE_CENTROIDS:
        return t
    return _LONG_TO_ABBR.get(t)


def heatmap_json_from_state_revenue(
    df: pd.DataFrame,
    state_col: str | None = None,
    revenue_col: str = "net_revenue",
    orders_col: str = "n_orders",
    weight_by: str = "orders",
) -> dict:
    """
    Build JSON for web map heat layers: state centroids with intensity.
    weight_by: 'orders' | 'revenue' — drives heat blur intensity.
    """
    farm = {
        "lat": FIREFLY_FARM_LAT,
        "lng": FIREFLY_FARM_LON,
        "title": FIREFLY_FARM_LABEL,
    }
    if df is None or df.empty:
        return {"points": [], "farm": farm}
    d = df.copy()
    if state_col is None:
        state_col = d.columns[0]
    d["_abbr"] = d[state_col].apply(normalize_state_abbrev)
    d = d[d["_abbr"].notna()]
    points: list[dict] = []
    for _, r in d.iterrows():
        abbr = r["_abbr"]
        if abbr not in STATE_CENTROIDS:
            continue
        lon, lat = STATE_CENTROIDS[abbr]
        n_o = float(pd.to_numeric(r.get(orders_col), errors="coerce") or 0.0)
        n_net = float(pd.to_numeric(r.get(revenue_col), errors="coerce") or 0.0)
        if weight_by == "revenue":
            w = max(n_net, 1.0)
        else:
            w = max(n_o, 1.0)
        points.append(
            {
                "lat": lat,
                "lng": lon,
                "weight": float(w),
                "state": abbr,
                "n_orders": int(n_o),
                "net_revenue": round(n_net, 2),
            }
        )
    return {"points": points, "farm": farm}
