"""Product co-purchase graph from pair counts."""
from __future__ import annotations

import pandas as pd
import networkx as nx


def build_graph(pairs_df: pd.DataFrame, min_co: float = 5.0) -> nx.Graph:
    """
    pairs_df: columns Product A Id, Product B Id, co_count (or Times Bought Together)
    """
    col_co = "co_count" if "co_count" in pairs_df.columns else "Times Bought Together"
    G = nx.Graph()
    for _, r in pairs_df.iterrows():
        co = float(r[col_co])
        if co < min_co:
            continue
        a, b = int(r["Product A Id"]), int(r["Product B Id"])
        if a == b:
            continue
        G.add_edge(a, b, weight=co)
    return G


def graph_summary(G: nx.Graph, titles: dict[int, str]) -> pd.DataFrame:
    if G.number_of_nodes() == 0:
        return pd.DataFrame()
    deg = dict(G.degree(weight="weight"))
    btw = nx.betweenness_centrality(G, weight="weight")
    rows = []
    for n in G.nodes():
        rows.append(
            {
                "product_id": n,
                "title": titles.get(n, ""),
                "weighted_degree": deg.get(n, 0),
                "betweenness": btw.get(n, 0),
            }
        )
    return pd.DataFrame(rows).sort_values("weighted_degree", ascending=False)


def top_edges(G: nx.Graph, titles: dict[int, str], k: int = 40) -> pd.DataFrame:
    edges = sorted(
        G.edges(data=True), key=lambda e: e[2].get("weight", 0), reverse=True
    )[:k]
    rows = []
    for a, b, d in edges:
        rows.append(
            {
                "product_a_id": a,
                "product_b_id": b,
                "weight": d.get("weight", 0),
                "product_a": titles.get(a, ""),
                "product_b": titles.get(b, ""),
            }
        )
    return pd.DataFrame(rows)
