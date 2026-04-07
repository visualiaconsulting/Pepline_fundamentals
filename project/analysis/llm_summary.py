from __future__ import annotations

import importlib
from typing import Dict, List

import pandas as pd

from config.settings import settings
from utils.logger import setup_logger


class LLMSummaryGenerator:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )
        self.client = None
        if settings.enable_llm_summary and settings.openai_api_key:
            self.client = self._build_openai_client()

    def _build_openai_client(self):
        try:
            openai_module = importlib.import_module("openai")
            openai_client = getattr(openai_module, "OpenAI", None)
            if openai_client is None:
                return None
            return openai_client(api_key=settings.openai_api_key)
        except Exception:
            self.logger.warning("OpenAI SDK not available, using rule-based summaries")
            return None

    @staticmethod
    def _default_narrative(row: pd.Series) -> Dict[str, str]:
        growth = float(row.get("revenue_growth_yoy", 0))
        roic = float(row.get("roic", 0))
        debt = float(row.get("debt_to_equity", 0))
        classification = str(row.get("classification", "Neutral"))

        thesis = (
            "Compania con perfil de crecimiento y rentabilidad competitivo en su industria."
            if growth > 15 and roic > 12
            else "Compania con fundamentales mixtos y necesidad de seguimiento trimestral."
        )

        risks = (
            "Riesgo financiero elevado por apalancamiento y posible presion en costos de capital."
            if debt > 2
            else "Riesgos principales: ciclo economico, competencia y ejecucion operativa."
        )

        executive = (
            f"{row.get('ticker')} clasifica como {classification} con crecimiento YoY de {growth:.1f}% "
            f"y ROIC de {roic:.1f}%."
        )

        return {
            "investment_thesis": thesis,
            "key_risks": risks,
            "executive_summary": executive,
        }

    def _llm_narrative(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if self.client is None:
            return self._default_narrative(row)

        try:
            prompt = (
                "Eres un analista fundamental buy-side senior.\n"
                "Genera respuesta JSON compacta con campos: investment_thesis, key_risks, executive_summary.\n"
                "No uses markdown.\n"
                f"Ticker: {row.get('ticker')}\n"
                f"Sector: {row.get('sector')}\n"
                f"Revenue Growth YoY: {row.get('revenue_growth_yoy'):.2f}\n"
                f"ROIC: {row.get('roic'):.2f}\n"
                f"Debt/Equity: {row.get('debt_to_equity'):.2f}\n"
                f"Operating Margin: {row.get('operating_margin'):.2f}\n"
                f"Net Margin: {row.get('net_margin'):.2f}\n"
                f"FCF: {row.get('free_cash_flow'):.2f}\n"
                f"Clasificacion: {row.get('classification')}\n"
                f"Noticias: {' | '.join(headlines[:5]) if headlines else 'Sin noticias'}"
            )

            response = self.client.responses.create(
                model=settings.openai_model,
                input=prompt,
                temperature=0.2,
            )
            text = response.output_text.strip()

            parsed = {
                "investment_thesis": text,
                "key_risks": "Ver narrativa LLM",
                "executive_summary": text[:350],
            }
            return parsed
        except Exception as exc:
            self.logger.warning("LLM narrative fallback activated for %s: %s", row.get("ticker"), exc)
            return self._default_narrative(row)

    def enrich_dataframe(self, ranking_df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
        if ranking_df.empty:
            return ranking_df

        enriched = ranking_df.copy()
        investment_thesis = []
        key_risks = []
        executive_summary = []

        for _, row in enriched.iterrows():
            ticker = row.get("ticker")
            headlines = []
            if not news_df.empty:
                headlines = (
                    news_df.loc[news_df["ticker"] == ticker, "title"]
                    .fillna("")
                    .astype(str)
                    .head(5)
                    .tolist()
                )

            narrative = self._llm_narrative(row, headlines)
            investment_thesis.append(narrative["investment_thesis"])
            key_risks.append(narrative["key_risks"])
            executive_summary.append(narrative["executive_summary"])

        enriched["investment_thesis"] = investment_thesis
        enriched["key_risks"] = key_risks
        enriched["executive_summary"] = executive_summary
        return enriched
