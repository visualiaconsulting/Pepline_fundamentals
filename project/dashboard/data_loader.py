from __future__ import annotations

from typing import Tuple

import pandas as pd
import streamlit as st

from dashboard.config import DATA_FILE, TOP10_FILE


NUMERIC_COLUMNS = [
    "market_cap",
    "revenue_growth_yoy",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "free_cash_flow",
    "roic",
    "debt_to_equity",
    "capex_to_revenue",
    "valuation_pe",
    "quality_score",
    "growth_score",
    "profitability_score",
    "risk_score",
    "valuation_score",
    "total_score",
    "rank",
]


@st.cache_data(show_spinner=False)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {DATA_FILE}")

    ranking_df = pd.read_csv(DATA_FILE)
    top10_df = pd.read_csv(TOP10_FILE) if TOP10_FILE.exists() else ranking_df.head(10).copy()

    for col in NUMERIC_COLUMNS:
        if col in ranking_df.columns:
            ranking_df[col] = pd.to_numeric(ranking_df[col], errors="coerce")

    ranking_df["sector"] = ranking_df.get("sector", "N/A").fillna("N/A")
    ranking_df["classification"] = ranking_df.get("classification", "Neutral").fillna("Neutral")
    ranking_df["ticker_origin"] = ranking_df.get("ticker_origin", "manual").fillna("manual")

    ranking_df = ranking_df.sort_values("rank", ascending=True).reset_index(drop=True)

    return ranking_df, top10_df


def apply_filters(
    df: pd.DataFrame,
    sectors: list[str],
    classifications: list[str],
    origins: list[str],
    score_range: tuple[float, float],
    market_cap_range: tuple[float, float],
) -> pd.DataFrame:
    filtered = df.copy()
    filtered = filtered[filtered["sector"].isin(sectors)]
    filtered = filtered[filtered["classification"].isin(classifications)]
    filtered = filtered[filtered["ticker_origin"].isin(origins)]
    filtered = filtered[
        (filtered["total_score"] >= score_range[0]) & (filtered["total_score"] <= score_range[1])
    ]
    filtered = filtered[
        (filtered["market_cap"] >= market_cap_range[0])
        & (filtered["market_cap"] <= market_cap_range[1])
    ]
    return filtered.reset_index(drop=True)
