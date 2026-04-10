from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis.llm_summary import LLMSummaryGenerator
from config.settings import settings
from reporting.document_builder import DocumentBuilder


def _top_filtered(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    ordered = df.copy()
    if "total_score" in ordered.columns:
        ordered["total_score"] = pd.to_numeric(ordered["total_score"], errors="coerce")
        ordered = ordered.sort_values("total_score", ascending=False)
    elif "rank" in ordered.columns:
        ordered["rank"] = pd.to_numeric(ordered["rank"], errors="coerce")
        ordered = ordered.sort_values("rank", ascending=True)

    return ordered.head(top_n).reset_index(drop=True)


def _load_news_for_top(top_df: pd.DataFrame) -> pd.DataFrame:
    if top_df.empty:
        return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

    news_path = settings.data_dir / "top20_news.csv"
    if not news_path.exists():
        return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

    news_df = pd.read_csv(news_path)
    if news_df.empty or "ticker" not in news_df.columns:
        return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

    selected = set(top_df["ticker"].fillna("").astype(str).tolist())
    return news_df[news_df["ticker"].fillna("").astype(str).isin(selected)].copy()


def _extract_headlines(news_df: pd.DataFrame, ticker: str) -> list[str]:
    if news_df.empty:
        return []
    if "ticker" not in news_df.columns or "title" not in news_df.columns:
        return []

    ticker_news = news_df[news_df["ticker"].fillna("").astype(str) == ticker]
    if ticker_news.empty:
        return []

    return (
        ticker_news["title"]
        .fillna("")
        .astype(str)
        .head(settings.ollama_max_headlines_per_ticker)
        .tolist()
    )


def _render_llm_block(row: pd.Series, news_df: pd.DataFrame) -> None:
    ticker = str(row.get("ticker", "")).strip()
    provider = str(row.get("llm_provider_used", "")).strip() or "N/A"
    status = str(row.get("llm_status", "")).strip() or "N/A"
    fallback = str(row.get("llm_fallback_reason", "")).strip()
    company_name = str(row.get("company_name", ticker)).strip() or ticker
    exchange = str(row.get("exchange", "")).strip() or "N/A"
    currency = str(row.get("currency", "USD")).strip() or "USD"
    previous_close = pd.to_numeric(row.get("previous_close"), errors="coerce")
    target_price = pd.to_numeric(row.get("target_price"), errors="coerce")
    previous_close_date = str(row.get("previous_close_date", "")).strip() or "N/D"

    st.markdown(f"**{company_name}**")
    st.caption(f"Exchange: {exchange}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Proveedor", provider)
    c2.metric("Estado", status)
    c3.metric("Config", settings.llm_provider)

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Cierre previo",
        f"{float(previous_close):,.2f} {currency}" if not pd.isna(previous_close) else "N/D",
        help=f"Fecha: {previous_close_date}",
    )
    m2.metric(
        "Target consenso",
        f"{float(target_price):,.2f} {currency}" if not pd.isna(target_price) and float(target_price) > 0 else "N/D",
    )
    m3.metric("Exchange", exchange)

    if fallback:
        st.caption(f"Fallback: {fallback}")

    st.write(str(row.get("executive_summary", "")).strip() or "Sin resumen ejecutivo")
    st.markdown(
        f"**Outlook proximo:** {str(row.get('near_term_outlook', '')).strip() or 'Sin outlook cercano'}"
    )
    st.markdown(f"**Tesis:** {str(row.get('investment_thesis', '')).strip() or 'Sin tesis'}")
    st.markdown(f"**Riesgos:** {str(row.get('key_risks', '')).strip() or 'Sin riesgos'}")

    if not settings.ollama_enable_dashboard_summary:
        return

    key = f"ai_reports_live_{ticker}"
    if st.button(f"Regenerar IA para {ticker}", key=f"ai_reports_btn_{ticker}"):
        generator = LLMSummaryGenerator()
        headlines = _extract_headlines(news_df, ticker)
        with st.spinner("Generando analisis IA..."):
            st.session_state[key] = generator.generate_for_row(row, headlines)

    live = st.session_state.get(key)
    if live:
        st.divider()
        st.caption(
            f"Resultado on-demand | Proveedor: {live.get('llm_provider_used', 'rule-based')}"
            f" | Estado: {live.get('llm_status', 'fallback')}"
        )
        if live.get("llm_fallback_reason"):
            st.caption(f"Motivo fallback: {live['llm_fallback_reason']}")
        st.write(live.get("executive_summary", "Sin resumen"))
        st.markdown(f"**Tesis:** {live.get('investment_thesis', 'Sin tesis')}")
        st.markdown(f"**Riesgos:** {live.get('key_risks', 'Sin riesgos')}")


def render_ai_reports_tab(filtered_df: pd.DataFrame) -> None:
    top_df = _top_filtered(filtered_df, top_n=20)
    if top_df.empty:
        st.info("No hay tickers para mostrar con los filtros actuales.")
        return

    st.caption("Informe IA para los 20 tickers con mayor score dentro de los filtros activos.")

    summary_cols = [
        col
        for col in [
            "rank",
            "ticker",
            "sector",
            "total_score",
            "classification",
            "llm_provider_used",
            "llm_status",
        ]
        if col in top_df.columns
    ]
    st.dataframe(top_df[summary_cols], use_container_width=True, hide_index=True)

    news_df = _load_news_for_top(top_df)

    st.divider()
    st.subheader("Documento diario")
    doc_top_n = int(
        st.selectbox(
            "Cantidad de tickers para el documento",
            options=[2, 5, 10, 20],
            index=3,
            key="ai_reports_doc_top_n",
        )
    )

    us_date = datetime.now().strftime("%m%d%Y")
    base_name = f"dashboard_top{doc_top_n}_{us_date}"

    builder = DocumentBuilder()
    markdown_doc = builder.build_markdown(
        ranking_df=top_df,
        news_df=news_df,
        top_n=doc_top_n,
        title=f"Reporte IA Top {doc_top_n} (filtros dashboard)",
    )
    text_doc = builder.markdown_to_text(markdown_doc)

    reports_dir_default = (settings.data_dir / "reports").resolve()
    browser_downloads = (Path.home() / "Downloads").resolve()
    snapshot_dir_input = st.text_input(
        "Carpeta local para guardar snapshot (.md y .txt)",
        value=str(reports_dir_default),
        key="ai_reports_snapshot_dir",
    )
    st.caption(
        f"Descarga del navegador: {base_name}.md / {base_name}.txt. "
        f"Carpeta de descargas del navegador (estimada): {browser_downloads}"
    )

    snapshot_dir = Path(snapshot_dir_input).expanduser()
    md_path = snapshot_dir / f"{base_name}.md"
    txt_path = snapshot_dir / f"{base_name}.txt"

    if st.button("Guardar snapshot del documento", key="save_dashboard_digest"):
        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            builder.write_snapshot(markdown_doc, md_path)
            builder.write_snapshot(text_doc, txt_path)
            st.success(f"Snapshot guardado en: {md_path} y {txt_path}")
        except Exception as exc:
            st.error(f"No se pudo guardar el snapshot: {exc}")

    st.download_button(
        "Descargar Markdown",
        data=markdown_doc,
        file_name=f"{base_name}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "Descargar TXT (correo)",
        data=text_doc,
        file_name=f"{base_name}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("Preview documento (Markdown)", expanded=False):
        st.markdown(markdown_doc)

    st.divider()
    st.subheader("Detalle por ticker")
    for _, row in top_df.iterrows():
        ticker = str(row.get("ticker", "")).strip() or "N/A"
        score = float(pd.to_numeric(row.get("total_score", 0), errors="coerce") or 0.0)
        classification = str(row.get("classification", "N/A")).strip() or "N/A"
        label = f"{ticker} | Score {score:.1f} | {classification}"
        with st.expander(label, expanded=False):
            _render_llm_block(row=row, news_df=news_df)

            ticker_news = pd.DataFrame()
            if not news_df.empty:
                ticker_news = news_df[news_df["ticker"].fillna("").astype(str) == ticker]

            if ticker_news.empty:
                st.caption("Sin noticias enlazadas para este ticker en el snapshot actual.")
                continue

            st.caption("Noticias asociadas")
            for idx, (_, item) in enumerate(ticker_news.head(settings.email_report_news_per_ticker).iterrows(), start=1):
                title = str(item.get("title", "Sin titular")).strip()
                link = str(item.get("link", "")).strip()
                publisher = str(item.get("publisher", "")).strip()
                published = str(item.get("published", "")).strip()
                meta_parts = [part for part in [publisher, published] if part]
                meta = f" ({' | '.join(meta_parts)})" if meta_parts else ""
                if link:
                    st.markdown(f"{idx}. [{title}]({link}){meta}")
                else:
                    st.markdown(f"{idx}. {title}{meta}")
