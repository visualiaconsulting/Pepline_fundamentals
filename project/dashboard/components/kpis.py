from __future__ import annotations

import pandas as pd
import streamlit as st


def render_kpis(df: pd.DataFrame) -> None:
    total_companies = len(df)
    avg_score = df["total_score"].mean() if total_companies else 0
    avg_roic = df["roic"].mean() if total_companies else 0
    excellent_pct = (
        (df["classification"].eq("Excelente").mean() * 100) if total_companies else 0
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Universo Analizado", f"{total_companies}")
    col2.metric("Score Promedio", f"{avg_score:.2f}")
    col3.metric("% Excelente", f"{excellent_pct:.1f}%")
    col4.metric("ROIC Promedio", f"{avg_roic:.2f}%")
