"""Symmetric product–product co-occurrence matrix + NMF latent factors."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF


def build_cooccurrence_matrix(
    pairs_df: pd.DataFrame,
    products_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[int]]:
    """
    Off-diagonal: summed co-purchase counts. Diagonal: net_orders (orders containing SKU).
    """
    pid_to_idx: dict[int, int] = {}
    ids = sorted(products_df["product_id"].dropna().astype(int).unique().tolist())
    for i, p in enumerate(ids):
        pid_to_idx[p] = i
    n = len(ids)
    M = np.zeros((n, n), dtype=float)

    orders = products_df.set_index("product_id")["net_orders"].reindex(ids).fillna(0)
    for i, p in enumerate(ids):
        M[i, i] = max(float(orders.loc[p]), 0.0)

    col_co = "co_count" if "co_count" in pairs_df.columns else "Times Bought Together"
    for _, r in pairs_df.iterrows():
        a, b = int(r["Product A Id"]), int(r["Product B Id"])
        co = float(r[col_co])
        if a not in pid_to_idx or b not in pid_to_idx:
            continue
        ia, ib = pid_to_idx[a], pid_to_idx[b]
        if ia != ib:
            M[ia, ib] += co
            M[ib, ia] += co

    mat = pd.DataFrame(M, index=ids, columns=ids)
    return mat, ids


def nmf_factors(
    co_mat: pd.DataFrame,
    n_components: int = 8,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    W: products x K loadings, H: K x products (sklearn uses X ~ W @ H).
    Returns long-form factor loadings for products (W normalized rows optional).
    """
    X = co_mat.values.astype(float)
    X = np.maximum(X, 1e-6)
    xm = float(X.max())
    if xm > 0:
        X = X / xm
    n_comp = min(n_components, X.shape[0] - 1, X.shape[1])
    n_comp = max(2, n_comp)
    model = NMF(
        n_components=n_comp,
        init="random",
        random_state=random_state,
        max_iter=400,
        l1_ratio=0.0,
    )
    W = model.fit_transform(X)
    H = model.components_

    product_ids = co_mat.index.astype(int).tolist()
    W_df = pd.DataFrame(
        W,
        index=product_ids,
        columns=[f"factor_{k+1}" for k in range(W.shape[1])],
    )
    W_df.insert(0, "title", "")
    return W_df, pd.DataFrame(H, columns=product_ids)
