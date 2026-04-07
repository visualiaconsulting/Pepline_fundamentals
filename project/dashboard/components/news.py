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

_CATALYST_RULES = [
    ("Resultados", {"earnings", "eps", "revenue", "guidance", "quarter", "q1", "q2", "q3", "q4"}),
    ("Analistas", {"upgrade", "upgraded", "downgrade", "downgraded", "target", "rating", "buy", "sell"}),
    ("M&A", {"acquisition", "acquire", "merger", "takeover", "buyout"}),
    ("Producto/IA", {"launch", "product", "chip", "ai", "model", "platform", "release"}),
    ("Regulatorio/Legal", {"investigation", "lawsuit", "regulator", "fine", "penalty", "antitrust"}),
    ("Contratos", {"contract", "deal", "partnership", "award", "agreement"}),
    ("Dividendos/Capital", {"dividend", "buyback", "repurchase", "offering", "issuance"}),
]


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


def classify_catalyst(title: str) -> str:
    """Classify the likely catalyst category from a headline."""
    words = set(re.findall(r"\b\w+\b", title.lower()))
    for category, keywords in _CATALYST_RULES:
        if words & keywords:
            return category
    return "General"


def _compute_forward_returns(price_df: pd.DataFrame, published_value: str) -> tuple[str, str]:
    """Estimate +1d and +5d returns from the next available close after publication."""
    if price_df.empty or not published_value or published_value == "—":
        return "—", "—"

    try:
        pub_dt = pd.to_datetime(published_value, errors="coerce")
        if pd.isna(pub_dt):
            return "—", "—"

        # Compare at date level against trading sessions.
        trading_dates = pd.to_datetime(price_df.index).normalize()
        target_date = pub_dt.normalize()
        start_positions = [i for i, d in enumerate(trading_dates) if d >= target_date]
        if not start_positions:
            return "—", "—"

        start_idx = start_positions[0]
        closes = price_df["Close"].astype(float).tolist()
        base = closes[start_idx]
        if base <= 0:
            return "—", "—"

        ret_1d = "—"
        ret_5d = "—"
        if start_idx + 1 < len(closes):
            r1 = (closes[start_idx + 1] / base - 1.0) * 100.0
            ret_1d = f"{r1:+.2f}%"
        if start_idx + 5 < len(closes):
            r5 = (closes[start_idx + 5] / base - 1.0) * 100.0
            ret_5d = f"{r5:+.2f}%"
        return ret_1d, ret_5d
    except Exception:
        return "—", "—"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_for_tickers(tickers: tuple[str, ...]) -> Dict[str, pd.DataFrame]:
    """Fetch Yahoo Finance news for a list of tickers. Cached for 30 minutes.

    Returns a dict {ticker: DataFrame(title, publisher, link, published, sentiment, icon)}.
    """
    results: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            # Daily prices are used to estimate simple post-news impact.
            downloaded = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
            price_df = downloaded if downloaded is not None else pd.DataFrame()
            raw = yf.Ticker(ticker).news or []
            if not raw:
                results[ticker] = pd.DataFrame()
                continue

            rows = []
            for item in raw:
                # yfinance >= 1.x nests data under item["content"]
                # older versions had flat keys at item level — support both
                content = item.get("content") or item

                title = content.get("title", "")
                if not title:
                    continue

                label, icon, color = classify_sentiment(title)
                catalyst = classify_catalyst(title)

                # Publisher: new format → content["provider"]["displayName"]
                provider = content.get("provider") or {}
                publisher = (
                    provider.get("displayName")
                    or item.get("publisher")
                    or "—"
                )

                # Link: new format → content["canonicalUrl"]["url"]
                canonical = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
                link = canonical.get("url") or item.get("link", "")

                # Published date: new format → ISO string "2026-04-07T20:20:00Z"
                pub = (
                    content.get("pubDate")
                    or item.get("providerPublishTime")
                    or item.get("published")
                )
                if isinstance(pub, (int, float)):
                    pub_str = datetime.fromtimestamp(pub).strftime("%Y-%m-%d %H:%M")
                elif isinstance(pub, str) and pub:
                    # ISO format → trim to date+time
                    pub_str = pub[:16].replace("T", " ")
                else:
                    pub_str = "—"

                impact_1d, impact_5d = _compute_forward_returns(price_df, pub_str)

                rows.append({
                    "sentiment_icon": icon,
                    "sentiment":      label,
                    "catalyst":       catalyst,
                    "title":          title,
                    "publisher":      publisher,
                    "link":           link,
                    "published":      pub_str,
                    "impact_1d":      impact_1d,
                    "impact_5d":      impact_5d,
                    "_color":         color,
                })
            results[ticker] = pd.DataFrame(rows)
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


def _impact_summary(df: pd.DataFrame) -> str:
    """Return average +1d and +5d impact from parsed percentage strings."""
    if df.empty:
        return "Impacto: sin datos"

    temp = df.copy()
    temp["impact_1d_num"] = pd.to_numeric(temp["impact_1d"].str.replace("%", "", regex=False), errors="coerce")
    temp["impact_5d_num"] = pd.to_numeric(temp["impact_5d"].str.replace("%", "", regex=False), errors="coerce")
    m1 = temp["impact_1d_num"].mean(skipna=True)
    m5 = temp["impact_5d_num"].mean(skipna=True)

    if pd.isna(m1) and pd.isna(m5):
        return "Impacto: sin datos"
    left = f"+1d promedio {m1:+.2f}%" if not pd.isna(m1) else "+1d promedio —"
    right = f"+5d promedio {m5:+.2f}%" if not pd.isna(m5) else "+5d promedio —"
    return f"Impacto: {left}  ·  {right}"


def _impact_to_float(value: str) -> float:
    """Convert formatted impact string like '+1.23%' to float, NaN when unavailable."""
    if not isinstance(value, str) or value.strip() in {"", "—"}:
        return float("nan")
    parsed = pd.to_numeric(value.replace("%", ""), errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def _build_cross_ticker_news_frame(news_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Flatten ticker->news mapping into one table for global ranking and alerts."""
    rows: list[dict] = []
    for ticker, df_news in news_dict.items():
        if df_news is None or df_news.empty:
            continue
        for _, item in df_news.iterrows():
            rows.append(
                {
                    "ticker": ticker,
                    "sentiment": item.get("sentiment", "Neutral"),
                    "catalyst": item.get("catalyst", "General"),
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", "—"),
                    "published": item.get("published", "—"),
                    "impact_1d": item.get("impact_1d", "—"),
                    "impact_5d": item.get("impact_5d", "—"),
                    "link": item.get("link", ""),
                }
            )
    if not rows:
        return pd.DataFrame()
    df_all = pd.DataFrame(rows)
    df_all["impact_1d_num"] = df_all["impact_1d"].apply(_impact_to_float)
    df_all["impact_5d_num"] = df_all["impact_5d"].apply(_impact_to_float)
    return df_all


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

    # --- Global alerts and top movers across all news in Top 20 ---
    df_all_news = _build_cross_ticker_news_frame(news_dict)
    if not df_all_news.empty:
        severe = df_all_news[
            (df_all_news["impact_1d_num"].notna() & (df_all_news["impact_1d_num"] <= -3.0))
            | (df_all_news["impact_5d_num"].notna() & (df_all_news["impact_5d_num"] <= -5.0))
        ].sort_values(["impact_1d_num", "impact_5d_num"], ascending=True)

        if not severe.empty:
            st.warning(
                f"Se detectaron {len(severe)} noticias con impacto negativo relevante "
                "(umbral: +1d <= -3% o +5d <= -5%)."
            )
            alert_table = severe[[
                "ticker", "published", "sentiment", "catalyst", "impact_1d", "impact_5d", "title"
            ]].head(12)
            st.dataframe(alert_table, use_container_width=True, hide_index=True)
        else:
            st.success("Sin alertas negativas fuertes en las noticias analizadas del Top 20.")

        movers = df_all_news.copy()
        movers[["impact_1d_num", "impact_5d_num"]] = movers[["impact_1d_num", "impact_5d_num"]].apply(
            pd.to_numeric,
            errors="coerce",
        )
        movers["move_abs"] = movers[["impact_1d_num", "impact_5d_num"]].abs().max(axis=1)
        movers = movers[movers["move_abs"].notna()].sort_values("move_abs", ascending=False).head(15)
        if not movers.empty:
            st.caption("Noticias que más movieron precio (Top 15 por magnitud de impacto)")
            movers_table = movers[[
                "ticker", "published", "sentiment", "catalyst", "impact_1d", "impact_5d", "title"
            ]]
            st.dataframe(movers_table, use_container_width=True, hide_index=True)
    else:
        st.info("No se pudieron construir alertas globales porque no hay noticias disponibles en este ciclo.")

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
            impact_summary = _impact_summary(df_news)
            label = f"**{ticker}** · {clf} · Score {score:.1f} · {sector}  — {sentiment_summary} · {impact_summary}"
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
    st.markdown(f"**{_impact_summary(df_news)}**")

    if not df_news.empty and "catalyst" in df_news.columns:
        catalyst_counts = df_news["catalyst"].value_counts().head(5)
        st.caption("Catalizadores principales")
        st.bar_chart(catalyst_counts)

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
        catalyst = item.get("catalyst", "General")
        impact_1d = item.get("impact_1d", "—")
        impact_5d = item.get("impact_5d", "—")

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
            <small style="color:#8b949e;">{publisher} &nbsp;·&nbsp; {published} &nbsp;·&nbsp; {catalyst} &nbsp;·&nbsp; +1d {impact_1d} &nbsp;·&nbsp; +5d {impact_5d}</small>
            </div>""",
            unsafe_allow_html=True,
        )
