from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from config.settings import settings
from utils.logger import setup_logger


class RankingModel:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    def rank(self, scored_df: pd.DataFrame) -> pd.DataFrame:
        if scored_df.empty:
            self.logger.warning("Empty dataframe received in ranking model")
            return scored_df

        ranking = scored_df.sort_values(
            by=["total_score", "revenue_growth_yoy", "roic"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

        ranking["rank"] = ranking.index + 1
        return ranking

    @staticmethod
    def _safe_text(value: object, default: str = "N/D") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text and text.lower() != "nan" else default

    @staticmethod
    def _safe_number(value: object) -> float | None:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return float(parsed)

    @classmethod
    def _format_number(cls, value: object, decimals: int = 2, suffix: str = "") -> str:
        number = cls._safe_number(value)
        if number is None:
            return "N/D"
        return f"{number:,.{decimals}f}{suffix}"

    @classmethod
    def _format_compact_money(cls, value: object, currency: str = "") -> str:
        number = cls._safe_number(value)
        if number is None:
            return "N/D"

        absolute = abs(number)
        if absolute >= 1_000_000_000_000:
            scaled = number / 1_000_000_000_000
            unit = "T"
        elif absolute >= 1_000_000_000:
            scaled = number / 1_000_000_000
            unit = "B"
        elif absolute >= 1_000_000:
            scaled = number / 1_000_000
            unit = "M"
        else:
            scaled = number
            unit = ""

        currency_text = f" {currency}" if currency else ""
        return f"{scaled:,.2f}{unit}{currency_text}"

    @staticmethod
    def _format_bool(value: object) -> str:
        return "Si" if bool(value) else "No"

    @staticmethod
    def _compact_summary(text: object, limit: int = 420) -> str:
        raw = str(text or "").strip()
        if not raw:
            return "N/D"
        clean = " ".join(raw.split())
        if len(clean) <= limit:
            return clean
        truncated = clean[: limit - 3].rsplit(" ", 1)[0].strip()
        return f"{truncated}..."

    @classmethod
    def _select_business_description(cls, row: pd.Series) -> str:
        overview = cls._safe_text(row.get("business_overview", ""), default="")
        if overview:
            return overview
        raw_summary = cls._compact_summary(row.get("business_summary", ""))
        if raw_summary != "N/D":
            return raw_summary
        company_name = cls._safe_text(row.get("company_name", row.get("ticker", "La compania")), default="La compania")
        sector = cls._safe_text(row.get("sector", "su sector"), default="su sector")
        industry = cls._safe_text(row.get("industry", "su industria"), default="su industria")
        return f"{company_name} opera en {sector} y participa principalmente en {industry}."

    def export_outputs(self, ranking_df: pd.DataFrame, news_df: pd.DataFrame) -> None:
        if ranking_df.empty:
            self.logger.warning("No ranking to export")
            return

        data_dir: Path = settings.data_dir
        reports_dir = data_dir / "reports"
        data_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        ranking_path = data_dir / "company_ranking.csv"
        top10_path = data_dir / "top10_opportunities.csv"
        top20_path = data_dir / "top20_opportunities.csv"
        top20_news_path = data_dir / "top20_news.csv"
        digest_top_n = settings.email_report_top_n
        top_digest_df = ranking_df.head(digest_top_n).copy()

        ranking_df.to_csv(ranking_path, index=False)
        ranking_df.head(10).to_csv(top10_path, index=False)
        top_digest_df.to_csv(top20_path, index=False)

        if not news_df.empty:
            digest_tickers = set(top_digest_df["ticker"].astype(str).tolist())
            digest_news_df = news_df[news_df["ticker"].astype(str).isin(digest_tickers)].copy()
            digest_news_df.to_csv(top20_news_path, index=False)
        else:
            pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"]).to_csv(
                top20_news_path, index=False
            )

        report_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        for _, row in ranking_df.iterrows():
            ticker = row["ticker"]
            company_news = news_df[news_df["ticker"] == ticker] if not news_df.empty else pd.DataFrame()

            headline = "Sin noticias recientes"
            if not company_news.empty:
                headline = str(company_news.iloc[0].get("title", "Sin noticias recientes"))

            news_lines = []
            if not company_news.empty:
                for idx, (_, news_row) in enumerate(company_news.head(settings.email_report_news_per_ticker).iterrows(), start=1):
                    title = str(news_row.get("title", "Sin titular"))
                    link = str(news_row.get("link", "")).strip()
                    publisher = str(news_row.get("publisher", "")).strip()
                    published = str(news_row.get("published", "")).strip()
                    line = f"{idx}. {title}"
                    if publisher:
                        line += f" | Fuente: {publisher}"
                    if published:
                        line += f" | Fecha: {published}"
                    if link:
                        line += f" | Link: {link}"
                    news_lines.append(line)

            news_block = "\n".join(news_lines) if news_lines else "Sin noticias recientes con link disponible"

            company_name = self._safe_text(row.get("company_name", ticker), default=str(ticker))
            currency = self._safe_text(row.get("currency", "USD"), default="USD")
            previous_close_date = self._safe_text(row.get("previous_close_date", ""))
            previous_close_value = self._format_number(row.get("previous_close"), suffix=f" {currency}")
            current_price_value = self._format_number(row.get("current_price"), suffix=f" {currency}")
            target_price_number = self._safe_number(row.get("target_price"))
            target_price_value = (
                self._format_number(target_price_number, suffix=f" {currency}")
                if target_price_number and target_price_number > 0
                else "N/D"
            )
            analyst_count_number = self._safe_number(row.get("analyst_count"))
            analyst_count_value = (
                str(int(analyst_count_number)) if analyst_count_number is not None and analyst_count_number > 0 else "N/D"
            )
            business_summary = self._select_business_description(row)
            report = (
                f"INFORME FUNDAMENTAL | {ticker}\n"
                f"Fecha de elaboracion: {report_generated_at}\n\n"
                f"[Identificacion]\n"
                f"Ticker: {ticker}\n"
                f"Empresa: {company_name}\n"
                f"Exchange: {self._safe_text(row.get('exchange', ''))}\n"
                f"Sector / Industria: {self._safe_text(row.get('sector', ''))} / {self._safe_text(row.get('industry', ''))}\n"
                f"Rank: {self._safe_text(row.get('rank', 'N/D'))}\n"
                f"Score total: {self._format_number(row.get('total_score'))}\n"
                f"Clasificacion: {self._safe_text(row.get('classification', ''))}\n\n"
                f"[Negocio]\n"
                f"Descripcion de la empresa: {business_summary}\n"
                f"Lectura breve del negocio: {self._safe_text(row.get('executive_summary', ''))}\n\n"
                f"[Mercado y Valuacion]\n"
                f"Precio actual de referencia: {current_price_value}\n"
                f"Cierre previo consultado: {previous_close_value}\n"
                f"Fecha del cierre previo: {previous_close_date}\n"
                f"Precio objetivo consenso: {target_price_value}\n"
                f"Analistas considerados: {analyst_count_value}\n"
                f"Market Cap: {self._format_compact_money(row.get('market_cap'), currency=currency)}\n"
                f"Trailing PE: {self._format_number(row.get('trailing_pe'))}\n"
                f"Forward PE: {self._format_number(row.get('forward_pe'))}\n"
                f"EV/EBITDA: {self._format_number(row.get('ev_to_ebitda'))}\n"
                f"Moneda: {currency}\n\n"
                f"[Fundamentales]\n"
                f"Crecimiento de ingresos YoY: {self._format_number(row.get('revenue_growth_yoy'), suffix='%')}\n"
                f"ROIC: {self._format_number(row.get('roic'), suffix='%')}\n"
                f"Margen operativo: {self._format_number(row.get('operating_margin'), suffix='%')}\n"
                f"Margen neto: {self._format_number(row.get('net_margin'), suffix='%')}\n"
                f"Debt / Equity: {self._format_number(row.get('debt_to_equity'))}\n"
                f"Free Cash Flow: {self._format_compact_money(row.get('free_cash_flow'), currency=currency)}\n"
                f"Candidato de alto potencial: {self._format_bool(row.get('high_potential_candidate', False))}\n"
                f"Tesis preliminar: {self._safe_text(row.get('fundamental_view', ''))}\n\n"
                f"[Lectura de Noticias]\n"
                f"Titular clave: {headline}\n"
                f"Outlook proximo: {self._safe_text(row.get('near_term_outlook', ''))}\n"
                f"Noticias relevantes:\n{news_block}\n\n"
                f"[Resumen AI]\n"
                f"Tesis de inversion: {self._safe_text(row.get('investment_thesis', ''))}\n"
                f"Riesgos clave: {self._safe_text(row.get('key_risks', ''))}\n"
                f"Proveedor LLM: {self._safe_text(row.get('llm_provider_used', ''))}\n"
                f"Estado LLM: {self._safe_text(row.get('llm_status', ''))}\n"
                f"Motivo fallback LLM: {self._safe_text(row.get('llm_fallback_reason', ''))}\n"
            )

            with open(reports_dir / f"{ticker}_report.txt", "w", encoding="utf-8") as file:
                file.write(report)

        self.logger.info("Outputs exported: %s, %s, %s and %s", ranking_path, top10_path, top20_path, top20_news_path)
