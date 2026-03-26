"""Customer-level LDA on product purchase counts (bag-of-products)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation


def customer_product_matrix(
    lines: pd.DataFrame,
    min_customer_lines: int = 3,
    min_product_count: int = 15,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Rows = customer_id, columns = product_name (counts).
    Drops sparse customers and rare products for stability.
    """
    df = lines.dropna(subset=["product_name", "customer_id"])
    df = df[df["customer_id"].astype(str).str.len() > 0]
    df = df.groupby(["customer_id", "product_name"], as_index=False)["quantity"].sum()

    cust_tot = df.groupby("customer_id")["quantity"].sum()
    keep_c = cust_tot[cust_tot >= min_customer_lines].index
    df = df[df["customer_id"].isin(keep_c)]

    prod_tot = df.groupby("product_name")["quantity"].sum()
    keep_p = prod_tot[prod_tot >= min_product_count].index
    df = df[df["product_name"].isin(keep_p)]

    wide = df.pivot_table(
        index="customer_id",
        columns="product_name",
        values="quantity",
        aggfunc="sum",
        fill_value=0,
    )
    products = list(wide.columns)
    customers = list(wide.index)
    return wide, customers, products


def fit_lda(
    count_matrix: pd.DataFrame,
    n_topics: int = 6,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, LatentDirichletAllocation]:
    """Returns (customer_topic_weights, product_topic_loadings, model)."""
    X = count_matrix.values.astype(float)
    n_topics = min(n_topics, X.shape[0] - 1, X.shape[1])
    n_topics = max(2, n_topics)
    model = LatentDirichletAllocation(
        n_components=n_topics,
        max_iter=30,
        learning_method="online",
        random_state=random_state,
        n_jobs=1,
    )
    doc_topic = model.fit_transform(X)

    cust_df = pd.DataFrame(
        doc_topic,
        index=count_matrix.index,
        columns=[f"topic_{i+1}" for i in range(n_topics)],
    )

    # components_ is n_topics x n_words — "topic" distribution over products
    topic_words = pd.DataFrame(
        model.components_,
        columns=count_matrix.columns,
        index=[f"topic_{i+1}" for i in range(n_topics)],
    )
    return cust_df, topic_words, model
