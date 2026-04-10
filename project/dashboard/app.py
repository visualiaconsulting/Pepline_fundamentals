from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

import streamlit as st

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.components.charts import (
    classification_bar,
    growth_vs_roic,
    risk_quality_matrix,
    score_components_heatmap,
    sector_treemap,
    weighted_contribution,
)
from dashboard.components.ai_reports import render_ai_reports_tab
from dashboard.components.kpis import render_kpis
from dashboard.components.news import render_news_tab
from dashboard.config import CLASSIFICATION_ORDER
from dashboard.data_loader import apply_filters, load_data
from config.settings import settings


st.set_page_config(
    page_title="Equity Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
)

ranking_df, top10_df = load_data()

st.title("Equity Intelligence Dashboard")
st.caption(
    "Vista ejecutiva de analisis fundamental y ranking cuantitativo. "
    f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

with st.sidebar:
    st.header("Filtros Globales")

    sector_options = sorted(ranking_df["sector"].dropna().unique().tolist())
    class_options = [c for c in CLASSIFICATION_ORDER if c in ranking_df["classification"].unique()]
    origin_options = sorted(ranking_df["ticker_origin"].dropna().unique().tolist())

    selected_sectors = st.multiselect("Sector", sector_options, default=sector_options)
    selected_classes = st.multiselect("Clasificacion", class_options, default=class_options)
    selected_origins = st.multiselect("Origen Ticker", origin_options, default=origin_options)

    min_score = float(ranking_df["total_score"].min())
    max_score = float(ranking_df["total_score"].max())
    score_range = st.slider("Rango Score", min_score, max_score, (min_score, max_score))

    min_mc = float(ranking_df["market_cap"].min())
    max_mc = float(ranking_df["market_cap"].max())
    market_cap_range = st.slider(
        "Rango Market Cap",
        min_value=min_mc,
        max_value=max_mc,
        value=(min_mc, max_mc),
        format="%.0f",
    )

filtered_df = apply_filters(
    ranking_df,
    selected_sectors,
    selected_classes,
    selected_origins,
    score_range,
    market_cap_range,
)

render_kpis(filtered_df)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Resumen Ejecutivo",
        "Fundamentales",
        "Riesgo y Valuacion",
        "Scoring",
        "📰 Noticias",
        "🤖 Informes IA Top 20",
    ]
)

with tab1:
    st.subheader("Top Oportunidades")
    top_view = filtered_df[[
        "rank",
        "ticker",
        "sector",
        "total_score",
        "classification",
        "revenue_growth_yoy",
        "roic",
        "ticker_origin",
    ]].sort_values("rank").head(25)
    st.dataframe(top_view, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    c1.plotly_chart(classification_bar(filtered_df), use_container_width=True)
    c2.plotly_chart(sector_treemap(filtered_df), use_container_width=True)

with tab2:
    c1, c2 = st.columns([1.5, 1])
    c1.plotly_chart(growth_vs_roic(filtered_df), use_container_width=True)

    margins = filtered_df[["ticker", "gross_margin", "operating_margin", "net_margin"]].copy()
    c2.subheader("Margenes (Top 15)")
    c2.dataframe(margins.head(15), use_container_width=True, hide_index=True)

with tab3:
    c1, c2 = st.columns(2)
    c1.plotly_chart(risk_quality_matrix(filtered_df), use_container_width=True)

    debt_tbl = filtered_df[["ticker", "debt_to_equity", "risk_score", "valuation_pe", "classification"]].copy()
    debt_tbl = debt_tbl.sort_values("debt_to_equity", ascending=False).head(20)
    c2.subheader("Top Riesgo por Apalancamiento")
    c2.dataframe(debt_tbl, use_container_width=True, hide_index=True)

with tab4:
    c1, c2 = st.columns(2)
    c1.plotly_chart(score_components_heatmap(filtered_df), use_container_width=True)
    c2.plotly_chart(weighted_contribution(filtered_df), use_container_width=True)

with tab5:
    st.caption(
        f"IA configurada: provider={settings.llm_provider} | "
        f"enabled={settings.enable_llm_summary} | modelo_ollama={settings.ollama_model}"
    )
    render_news_tab(filtered_df)

with tab6:
    render_ai_reports_tab(filtered_df)

st.divider()
st.subheader("Top 10 Oficial del Pipeline")
st.dataframe(top10_df, use_container_width=True, hide_index=True)
