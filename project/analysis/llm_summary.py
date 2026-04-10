from __future__ import annotations

import importlib
import json
from typing import Dict, List

import pandas as pd

from analysis.ollama_client import OllamaClient
from config.settings import settings
from utils.logger import setup_logger


class LLMSummaryGenerator:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )
        self.provider = settings.llm_provider
        self.openai_client = None
        self.ollama_client = (
            OllamaClient(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
                max_headlines=settings.ollama_max_headlines_per_ticker,
                api_key=settings.ollama_api_key,
            )
            if settings.enable_llm_summary
            else None
        )
        self.ollama_health: tuple[bool, str] = (False, "ollama_not_checked")
        self.ollama_failures = 0
        self.ollama_generation_disabled = False

        if settings.enable_llm_summary and self.provider == "openai" and settings.openai_api_key:
            self.openai_client = self._build_openai_client()
        if settings.enable_llm_summary and self.provider == "ollama" and self.ollama_client is not None:
            self.ollama_health = self.ollama_client.health_check()
        self.batch_top_n = settings.ollama_batch_top_n

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

    def _fallback_narrative(self, row: pd.Series, reason: str) -> Dict[str, str]:
        narrative = self._default_narrative(row)
        narrative["llm_provider_used"] = "rule-based"
        narrative["llm_status"] = "fallback"
        narrative["llm_fallback_reason"] = reason
        return narrative

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
            "business_overview": (
                f"{row.get('company_name', row.get('ticker', 'La compania'))} opera en {row.get('sector', 'su sector')} "
                f"y participa principalmente en {row.get('industry', 'su industria')}."
            ),
            "investment_thesis": thesis,
            "key_risks": risks,
            "executive_summary": executive,
            "near_term_outlook": "Sin senal concluyente de muy corto plazo; conviene seguir noticias y proximos resultados."
            if classification == "Neutral"
            else "El sesgo cercano depende de si las noticias recientes confirman la fortaleza operativa observada."
        }

    @staticmethod
    def _safe_float(row: pd.Series, key: str) -> float:
        return float(pd.to_numeric(row.get(key, 0), errors="coerce") or 0.0)

    def _openai_narrative(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if self.openai_client is None:
            return self._fallback_narrative(row, "openai_client_unavailable")

        try:
            prompt = (
                "Eres un analista fundamental buy-side senior.\n"
                "Responde SIEMPRE en espanol.\n"
                "Genera respuesta JSON compacta con campos: business_overview, investment_thesis, key_risks, executive_summary, near_term_outlook.\n"
                "No uses markdown.\n"
                f"Ticker: {row.get('ticker')}\n"
                f"Empresa: {row.get('company_name', '')}\n"
                f"Sector: {row.get('sector')}\n"
                f"Negocio: {row.get('business_summary', '')}\n"
                f"Revenue Growth YoY: {self._safe_float(row, 'revenue_growth_yoy'):.2f}\n"
                f"ROIC: {self._safe_float(row, 'roic'):.2f}\n"
                f"Debt/Equity: {self._safe_float(row, 'debt_to_equity'):.2f}\n"
                f"Operating Margin: {self._safe_float(row, 'operating_margin'):.2f}\n"
                f"Net Margin: {self._safe_float(row, 'net_margin'):.2f}\n"
                f"FCF: {self._safe_float(row, 'free_cash_flow'):.2f}\n"
                f"Clasificacion: {row.get('classification')}\n"
                f"Noticias: {' | '.join(headlines[:5]) if headlines else 'Sin noticias'}\n"
                "business_overview debe explicar en 1 o 2 frases que hace la empresa y de donde viene su negocio principal.\n"
                "near_term_outlook debe describir el posible comportamiento de corto plazo sin inventar precios ni catalysts no observados."
            )

            response = self.openai_client.responses.create(
                model=settings.openai_model,
                input=prompt,
                temperature=0.2,
            )
            text = response.output_text.strip()

            parsed = self._parse_openai_text(text)
            parsed["llm_provider_used"] = "openai"
            parsed["llm_status"] = "ok"
            parsed["llm_fallback_reason"] = ""
            return parsed
        except Exception as exc:
            self.logger.warning("OpenAI narrative fallback for %s: %s", row.get("ticker"), exc)
            return self._fallback_narrative(row, f"openai_error:{exc}")

    @staticmethod
    def _parse_openai_text(text: str) -> Dict[str, str]:
        if not text:
            return {
                "investment_thesis": "",
                "key_risks": "",
                "executive_summary": "",
            }

        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return {
                    "business_overview": str(loaded.get("business_overview", "")),
                    "investment_thesis": str(loaded.get("investment_thesis", "")),
                    "key_risks": str(loaded.get("key_risks", "")),
                    "executive_summary": str(loaded.get("executive_summary", "")),
                    "near_term_outlook": str(loaded.get("near_term_outlook", "")),
                }
        except json.JSONDecodeError:
            pass

        return {
            "business_overview": text[:220],
            "investment_thesis": text,
            "key_risks": "Ver narrativa LLM",
            "executive_summary": text[:350],
            "near_term_outlook": "No se pudo estructurar outlook de corto plazo desde la respuesta del modelo.",
        }

    def _ollama_narrative(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if self.ollama_client is None:
            return self._fallback_narrative(row, "ollama_client_unavailable")
        if self.ollama_generation_disabled:
            return self._fallback_narrative(row, "ollama_degraded_after_failures")

        healthy, reason = self.ollama_health
        if not healthy:
            return self._fallback_narrative(row, f"ollama_unhealthy:{reason}")

        try:
            parsed = self.ollama_client.generate_summary(
                ticker=str(row.get("ticker", "")),
                headlines=headlines,
                facts={
                    "company_name": row.get("company_name", ""),
                    "business_summary": row.get("business_summary", ""),
                    "classification": row.get("classification", "Neutral"),
                    "revenue_growth_yoy": self._safe_float(row, "revenue_growth_yoy"),
                    "roic": self._safe_float(row, "roic"),
                    "debt_to_equity": self._safe_float(row, "debt_to_equity"),
                    "operating_margin": self._safe_float(row, "operating_margin"),
                    "net_margin": self._safe_float(row, "net_margin"),
                    "free_cash_flow": self._safe_float(row, "free_cash_flow"),
                },
            )
            if (
                not parsed.get("business_overview")
                or not parsed.get("investment_thesis")
                or not parsed.get("key_risks")
                or not parsed.get("executive_summary")
                or not parsed.get("near_term_outlook")
            ):
                return self._fallback_narrative(row, "ollama_empty_response")
            parsed["llm_provider_used"] = "ollama"
            parsed["llm_status"] = "ok"
            parsed["llm_fallback_reason"] = ""
            self.ollama_failures = 0
            return parsed
        except Exception as exc:
            self.logger.warning("Ollama narrative fallback for %s: %s", row.get("ticker"), exc)
            self.ollama_failures += 1
            if self.ollama_failures >= 3:
                self.ollama_generation_disabled = True
            return self._fallback_narrative(row, f"ollama_error:{exc}")

    def generate_for_row(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if not settings.enable_llm_summary:
            return self._fallback_narrative(row, "llm_disabled")

        provider = settings.llm_provider
        if provider in {"rule-based", "rule_based"}:
            return self._fallback_narrative(row, "provider_rule_based")
        if provider == "openai":
            return self._openai_narrative(row, headlines)
        if provider == "ollama":
            return self._ollama_narrative(row, headlines)
        return self._fallback_narrative(row, f"unknown_provider:{provider}")

    def enrich_dataframe(self, ranking_df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
        if ranking_df.empty:
            return ranking_df

        enriched = ranking_df.copy()
        investment_thesis = []
        key_risks = []
        executive_summary = []
        business_overview = []
        near_term_outlook = []
        llm_provider_used = []
        llm_status = []
        llm_fallback_reason = []

        for idx, row in enriched.iterrows():
            ticker = row.get("ticker")
            headlines = []
            if not news_df.empty and {"ticker", "title"}.issubset(news_df.columns):
                ticker_news = news_df[news_df["ticker"] == ticker]
                title_series = pd.Series(ticker_news["title"], dtype="object")
                headlines = title_series.fillna("").astype(str).head(5).tolist()

            if settings.enable_llm_summary and settings.llm_provider == "ollama" and idx >= self.batch_top_n:
                narrative = self._fallback_narrative(row, "ollama_batch_scope_top10")
            else:
                narrative = self.generate_for_row(row, headlines)
            business_overview.append(narrative["business_overview"])
            investment_thesis.append(narrative["investment_thesis"])
            key_risks.append(narrative["key_risks"])
            executive_summary.append(narrative["executive_summary"])
            near_term_outlook.append(narrative["near_term_outlook"])
            llm_provider_used.append(narrative.get("llm_provider_used", "rule-based"))
            llm_status.append(narrative.get("llm_status", "fallback"))
            llm_fallback_reason.append(narrative.get("llm_fallback_reason", ""))

        enriched["business_overview"] = business_overview
        enriched["investment_thesis"] = investment_thesis
        enriched["key_risks"] = key_risks
        enriched["executive_summary"] = executive_summary
        enriched["near_term_outlook"] = near_term_outlook
        enriched["llm_provider_used"] = llm_provider_used
        enriched["llm_status"] = llm_status
        enriched["llm_fallback_reason"] = llm_fallback_reason
        return enriched
