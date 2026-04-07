from __future__ import annotations

import re
from datetime import datetime
from typing import Dict

import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------------------------
# Keyword lists for rule-based sentiment classification
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "record", "profit", "growth", "upgrade",
    "upgraded", "raise", "raised", "buy", "bullish", "exceeds", "exceed",
    "rally", "rallies", "gain", "gains", "strong", "outperform", "outperforms",
    "breakout", "high", "higher", "positive", "better", "top", "boost", "boosted",
    "deal", "partnership", "contract", "award", "approval", "approved",
    "dividend", "buyback", "acquisition",
}

_NEGATIVE_WORDS = {
    "miss", "misses", "fall", "falls", "fell", "decline", "declines", "declined",
    "cut", "cuts", "loss", "losses", "downgrade", "downgraded", "sell", "bearish",
    "below", "warning", "layoff", "layoffs", "investigation", "fraud", "lawsuit",
    "recall", "weak", "lower", "worse", "risk", "concern", "concerns", "drop",
    "drops", "dropped", "slump", "slumps", "plunge", "plunges", "halt",
    "suspended", "penalty", "fine", "fined", "bankruptcy", "default",
}

_SENTIMENT_META = {
    "Positivo": ("🟢", "#3fb950"),
    "Negativo": ("🔴", "#f85149"),
    "Neutral":  ("🟡", "#d29922"),
}


def classify_sentiment(title: str) -> tuple[str, str, str]:
    """Return (label, icon, color) for a news headline using keyword matching."""
    words = set(re.findall(r"\b\w+\b", title.lower()))
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    if pos > neg:
        label = "Positivo"
    elif neg > pos:
        label = "Negativo"
    else:
        label = "Neutral"
    icon, color = _SENTIMENT_META[label]
    return label, icon, color


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_for_tickers(tickers: tuple[str, ...]) -> Dict[str, pd.DataFrame]:
    """Fetch Yahoo Finance news for a list of tickers. Cached for 30 minutes.

    Returns a dict {ticker: DataFrame(title, publisher, link, published, sentiment, icon)}.
    """
    results: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            raw = yf.Ticker(ticker).news or []
            if not raw:
                results[ticker] = pd.DataFrame()
                continue

            rows = []
            for item in raw:
                title = item.get("title", "")
                label, icon, color = classify_sentiment(title)
                # published can be epoch int or None
                pub = item.get("providerPublishTime") or item.get("published")
                if isinstance(pub, (int, float)):
                    pub_str = datetime.fromtimestamp(pub).strftime("%Y-%m-%d %H:%M")
                else:
                    pub_str = str(pub) if pub else "—"

                rows.append({
                    "sentiment_icon": icon,
                    "sentiment":      label,
                    "title":          title,
                    "publisher":      item.get("publisher", "—"),
                    "link":           item.get("link", ""),
                    "published":      pub_str,
                    "_color":         color,
                })
            df = pd.DataFrame(rows)
            results[ticker] = df
        except Exception:
            results[ticker] = pd.DataFrame()
    return results


def _sentiment_bar(df: pd.DataFrame) -> str:
    """Return a mini summary string with sentiment counts."""
    if df.empty:
        return "Sin datos"
    counts = df["sentiment"].value_counts()
    pos = counts.get("Positivo", 0)
    neu = counts.get("Neutral", 0)
    neg = counts.get("Negativo", 0)
    return f"🟢 {pos} Positivas  ·  🟡 {neu} Neutrales  ·  🔴 {neg} Negativas"


def render_news_tab(filtered_df: pd.DataFrame) -> None:
    """Render the full Noticias tab content."""

    # --- Top 20 tickers by score from the currently filtered universe ---
    top20_tickers = (
        filtered_df
        .sort_values("total_score", ascending=False)
        .head(20)["ticker"]
        .tolist()
    )

    if not top20_tickers:
        st.info("No hay tickers con los filtros actuales. Ajusta los filtros del sidebar.")
        return

    # --- Refresh button (clears only news cache) ---
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.caption(
            f"Noticias en vivo desde Yahoo Finance para los **Top {len(top20_tickers)} tickers** "
            "del universo filtrado. Caché: 30 minutos."
        )
    with col_btn:
        if st.button("🔄 Actualizar", help="Limpia el caché y recarga las noticias"):
            st.cache_data.clear()
            st.rerun()

    # --- Fetch news (cached) ---
    with st.spinner("Cargando noticias..."):
        news_dict = fetch_news_for_tickers(tuple(top20_tickers))

    # --- Ticker selector ---
    # Build a lookup dict for ticker metadata to avoid repeated loc calls
    meta = (
        filtered_df[filtered_df["ticker"].isin(top20_tickers)]
        .set_index("ticker")[["classification", "total_score"]]
    )

    ticker_labels = {
        t: (
            f"{t}  —  "
            f"{meta.at[t, 'classification']}  "
            f"| Score {meta.at[t, 'total_score']:.1f}"
        )
        for t in top20_tickers
        if t in meta.index
    }

    view_mode = st.radio(
        "Vista",
        options=["Todos los tickers (acordeón)", "Ticker específico"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view_mode == "Ticker específico":
        selected = st.selectbox(
            "Selecciona un ticker",
            options=list(ticker_labels.keys()),
            format_func=lambda t: ticker_labels.get(t) or t,
        )
        if selected:
            _render_ticker_news(selected, filtered_df, news_dict)
    else:
        for ticker in top20_tickers:
            row = filtered_df.loc[filtered_df["ticker"] == ticker]
            if row.empty:
                continue
            score = row["total_score"].values[0]
            clf = row["classification"].values[0]
            sector = row["sector"].values[0]
            df_news = news_dict.get(ticker, pd.DataFrame())
            sentiment_summary = _sentiment_bar(df_news)
            label = f"**{ticker}** · {clf} · Score {score:.1f} · {sector}  — {sentiment_summary}"
            with st.expander(label, expanded=False):
                _render_news_table(ticker, df_news)


def _render_ticker_news(ticker: str, filtered_df: pd.DataFrame, news_dict: dict) -> None:
    """Render detailed news view for a single ticker."""
    row = filtered_df.loc[filtered_df["ticker"] == ticker]
    if row.empty:
        st.warning(f"No se encontró información para {ticker}.")
        return

    score = row["total_score"].values[0]
    clf = row["classification"].values[0]
    sector = row["sector"].values[0]
    df_news = news_dict.get(ticker, pd.DataFrame())

    # Header
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ticker", ticker)
    c2.metric("Score", f"{score:.1f} / 100")
    c3.metric("Clasificación", clf)
    c4.metric("Sector", sector)

    st.markdown(f"**Sentimiento:** {_sentiment_bar(df_news)}")
    st.divider()
    _render_news_table(ticker, df_news)


def _render_news_table(ticker: str, df_news: pd.DataFrame) -> None:
    """Render a formatted table of news items for one ticker."""
    if df_news.empty:
        st.info(f"No se encontraron noticias recientes para **{ticker}**.")
        return

    for _, item in df_news.iterrows():
        icon = item["sentiment_icon"]
        color = item["_color"]
        title = item["title"]
        link = item["link"]
        publisher = item["publisher"]
        published = item["published"]

        title_md = f'<a href="{link}" target="_blank">{title}</a>' if link else title
        st.markdown(
            f"""<div style="
                border-left: 3px solid {color};
                padding: 6px 12px;
                margin-bottom: 8px;
                background: rgba(255,255,255,0.03);
                border-radius: 4px;
            ">
            {icon} &nbsp; {title_md}<br>
            <small style="color:#8b949e;">{publisher} &nbsp;·&nbsp; {published}</small>
            </div>""",
            unsafe_allow_html=True,
        )
