from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.config import CLASSIFICATION_COLORS, SCORE_COMPONENTS, WEIGHT_MAP


def classification_bar(df: pd.DataFrame):
    agg = (
        df.groupby("classification", as_index=False)["ticker"]
        .count()
        .rename(columns={"ticker": "count"})
    )
    fig = px.bar(
        agg,
        x="classification",
        y="count",
        color="classification",
        color_discrete_map=CLASSIFICATION_COLORS,
        title="Distribucion por Clasificacion",
    )
    fig.update_layout(height=350, showlegend=False)
    return fig


def sector_treemap(df: pd.DataFrame):
    agg = (
        df.groupby("sector", as_index=False)
        .agg(companies=("ticker", "count"), total_market_cap=("market_cap", "sum"))
        .sort_values("companies", ascending=False)
    )
    fig = px.treemap(
        agg,
        path=["sector"],
        values="companies",
        color="total_market_cap",
        color_continuous_scale="Blues",
        title="Cobertura por Sector",
    )
    fig.update_layout(height=380)
    return fig


def growth_vs_roic(df: pd.DataFrame):
    fig = px.scatter(
        df,
        x="revenue_growth_yoy",
        y="roic",
        size="market_cap",
        color="classification",
        hover_data=["ticker", "sector", "total_score"],
        color_discrete_map=CLASSIFICATION_COLORS,
        title="Growth vs ROIC",
    )
    fig.update_layout(height=420)
    return fig


def risk_quality_matrix(df: pd.DataFrame):
    fig = px.scatter(
        df,
        x="risk_score",
        y="quality_score",
        size="market_cap",
        color="valuation_score",
        hover_data=["ticker", "sector", "debt_to_equity", "total_score"],
        color_continuous_scale="RdYlGn",
        title="Matriz Calidad vs Riesgo",
    )
    fig.update_layout(height=420)
    return fig


def score_components_heatmap(df: pd.DataFrame):
    top = df.nsmallest(20, "rank")[["ticker", *SCORE_COMPONENTS]].set_index("ticker")
    fig = go.Figure(
        data=go.Heatmap(
            z=top.values,
            x=top.columns,
            y=top.index,
            colorscale="Blues",
            colorbar={"title": "Score"},
        )
    )
    fig.update_layout(title="Top 20: Heatmap de Componentes", height=520)
    return fig


def weighted_contribution(df: pd.DataFrame):
    contributions = []
    for col, weight in WEIGHT_MAP.items():
        value = (df[col] * weight).mean() if not df.empty else 0
        contributions.append({"component": col, "weighted_points": value})

    cont_df = pd.DataFrame(contributions)
    fig = px.bar(
        cont_df,
        x="component",
        y="weighted_points",
        title="Contribucion Promedio al Score Total",
        color="weighted_points",
        color_continuous_scale="Teal",
    )
    fig.update_layout(height=360, showlegend=False)
    return fig
