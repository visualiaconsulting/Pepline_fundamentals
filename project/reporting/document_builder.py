from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from config.settings import settings


class DocumentBuilder:
    def __init__(self) -> None:
        self.top_n = settings.email_report_top_n
        self.news_per_ticker = settings.email_report_news_per_ticker

    @staticmethod
    def _safe_text(value: object, default: str = "N/A") -> str:
        text = str(value).strip() if value is not None else ""
        return text if text else default

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return float(parsed)

    @classmethod
    def _format_number(cls, value: object, decimals: int = 2, suffix: str = "", default: str = "N/D") -> str:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return f"{float(parsed):,.{decimals}f}{suffix}"

    def _top_tickers(self, ranking_df: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
        if ranking_df.empty:
            return ranking_df.copy()

        selected_n = top_n if top_n is not None else self.top_n
        selected_n = max(1, int(selected_n))

        ordered = ranking_df.copy()
        if "total_score" in ordered.columns:
            ordered["total_score"] = pd.to_numeric(ordered["total_score"], errors="coerce")
            ordered = ordered.sort_values("total_score", ascending=False)
        elif "rank" in ordered.columns:
            ordered["rank"] = pd.to_numeric(ordered["rank"], errors="coerce")
            ordered = ordered.sort_values("rank", ascending=True)

        return ordered.head(selected_n).reset_index(drop=True)

    @staticmethod
    def _dedupe_news(news_df: pd.DataFrame) -> pd.DataFrame:
        if news_df.empty:
            return news_df.copy()

        dedupe_cols = [col for col in ["ticker", "title", "published", "link"] if col in news_df.columns]
        if dedupe_cols:
            return news_df.drop_duplicates(subset=dedupe_cols).copy()
        return news_df.copy()

    def build_markdown(
        self,
        ranking_df: pd.DataFrame,
        news_df: pd.DataFrame,
        *,
        top_n: int | None = None,
        title: str = "Reporte diario de oportunidades",
    ) -> str:
        selected_df = self._top_tickers(ranking_df, top_n=top_n)
        clean_news_df = self._dedupe_news(news_df)

        lines = [
            f"# {title}",
            "",
            f"- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- Empresas incluidas: {len(selected_df.index)}",
            "",
        ]

        if selected_df.empty:
            lines.append("No hay empresas disponibles para el reporte.")
            lines.append("")
            return "\n".join(lines).strip() + "\n"

        for pos, (_, row) in enumerate(selected_df.iterrows(), start=1):
            ticker = self._safe_text(row.get("ticker", ""))
            company_name = self._safe_text(row.get("company_name", ticker), default=ticker)
            classification = self._safe_text(row.get("classification", "Neutral"), default="Neutral")
            score = self._safe_float(row.get("total_score", 0))
            provider = self._safe_text(row.get("llm_provider_used", ""))
            llm_status = self._safe_text(row.get("llm_status", ""))
            summary = self._safe_text(row.get("executive_summary", ""))
            thesis = self._safe_text(row.get("investment_thesis", ""))
            risks = self._safe_text(row.get("key_risks", ""))
            near_term_outlook = self._safe_text(row.get("near_term_outlook", ""))
            exchange = self._safe_text(row.get("exchange", ""))
            previous_close_date = self._safe_text(row.get("previous_close_date", ""))
            currency = self._safe_text(row.get("currency", "USD"), default="USD")
            previous_close = self._format_number(row.get("previous_close"), suffix=f" {currency}")
            target_price_raw = pd.to_numeric(row.get("target_price"), errors="coerce")
            target_price = (
                self._format_number(target_price_raw, suffix=f" {currency}")
                if not pd.isna(target_price_raw) and float(target_price_raw) > 0
                else "N/D"
            )
            fallback = str(row.get("llm_fallback_reason", "") or "").strip()
            rank_value = row.get("rank", pos)

            lines.extend(
                [
                    f"## #{int(pd.to_numeric(rank_value, errors='coerce') or pos)} {ticker} - {company_name}",
                    f"- Score: {score:.2f}",
                    f"- Clasificacion: {classification}",
                    f"- Exchange: {exchange}",
                    f"- Cierre previo: {previous_close} | Fecha: {previous_close_date}",
                    f"- Precio objetivo consenso: {target_price}",
                    f"- LLM: {provider} | Estado: {llm_status}",
                    "",
                    "**Resumen ejecutivo**",
                    summary,
                    "",
                    "**Outlook proximo**",
                    near_term_outlook,
                    "",
                    "**Tesis de inversion**",
                    thesis,
                    "",
                    "**Riesgos clave**",
                    risks,
                    "",
                ]
            )

            if fallback:
                lines.append(f"- Fallback: {fallback}")
                lines.append("")

            ticker_news = pd.DataFrame()
            if not clean_news_df.empty and "ticker" in clean_news_df.columns:
                ticker_news = clean_news_df[
                    clean_news_df["ticker"].fillna("").astype(str) == ticker
                ]

            if ticker_news.empty:
                lines.append("**Noticias**")
                lines.append("- Sin noticias con links disponibles")
                lines.append("")
                continue

            lines.append("**Noticias**")
            for idx, (_, news_row) in enumerate(ticker_news.head(self.news_per_ticker).iterrows(), start=1):
                title_value = self._safe_text(news_row.get("title", "Sin titular"), default="Sin titular")
                link = str(news_row.get("link", "") or "").strip()
                publisher = str(news_row.get("publisher", "") or "").strip()
                published = str(news_row.get("published", "") or "").strip()

                meta_parts = [part for part in [publisher, published] if part]
                meta = f" ({' | '.join(meta_parts)})" if meta_parts else ""
                line = f"{idx}. {title_value}{meta}"
                if link:
                    line += f" -> {link}"
                lines.append(line)

            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def markdown_to_text(markdown_text: str) -> str:
        text = markdown_text
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = text.replace("**", "")
        text = text.replace("`", "")
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    @staticmethod
    def write_snapshot(content: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
