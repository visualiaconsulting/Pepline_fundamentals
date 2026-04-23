from __future__ import annotations

import importlib
import json
from typing import Dict, List

import pandas as pd
import requests

from analysis.gemini_cli_client import GeminiCLIClient
from analysis.ollama_client import OllamaClient
from config.settings import settings
from utils.logger import setup_logger


class LMStudioClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: int,
        max_headlines: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = max(10, min(timeout_seconds, 90))
        self.max_headlines = max(1, max_headlines)
        self.api_key = api_key.strip()

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def health_check(self) -> tuple[bool, str]:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=min(self.timeout, 10),
            )
            response.raise_for_status()
            return True, "ok"
        except Exception as exc:
            return False, str(exc)

    def generate_summary(
        self, ticker: str, headlines: List[str], facts: Dict[str, object]
    ) -> Dict[str, str]:
        prompt = self._build_prompt(ticker, headlines, facts, self.max_headlines)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un analista fundamental senior con enfoque buy-side y sell-side. "
                        "Responde SIEMPRE en espanol. "
                        "Responde SOLO un JSON valido con exactamente estas llaves: business_overview, investment_thesis, key_risks, executive_summary, near_term_outlook. "
                        "No uses markdown. No agregues texto fuera del JSON. No inventes llaves adicionales. "
                        "Usa este formato exacto: {\"business_overview\":\"...\",\"investment_thesis\":\"...\",\"key_risks\":\"...\",\"executive_summary\":\"...\",\"near_term_outlook\":\"...\"}. "
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={**self._headers(), "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()
        text = ""
        if isinstance(result, dict):
            choices = result.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message", {})
                text = msg.get("content", "")
        parsed = self._parse_json_payload(text)
        return {
            "business_overview": parsed.get("business_overview", ""),
            "investment_thesis": parsed.get("investment_thesis", ""),
            "key_risks": parsed.get("key_risks", ""),
            "executive_summary": parsed.get("executive_summary", ""),
            "near_term_outlook": parsed.get("near_term_outlook", ""),
        }

    @staticmethod
    def _parse_json_payload(text: str) -> Dict[str, str]:
        if not text:
            return {}
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return {str(k): str(v) for k, v in loaded.items()}
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidate = text[start : end + 1]
            try:
                loaded = json.loads(candidate)
                if isinstance(loaded, dict):
                    return {str(k): str(v) for k, v in loaded.items()}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _build_prompt(ticker: str, headlines: List[str], facts: Dict[str, object], max_headlines: int) -> str:
        joined_headlines = " | ".join(headlines[:max_headlines])
        if not joined_headlines:
            joined_headlines = "Sin noticias"
        return (
            f"Ticker: {ticker}\n"
            f"Empresa: {facts.get('company_name', '')}\n"
            f"Negocio: {facts.get('business_summary', '')}\n"
            f"Clasificacion: {facts.get('classification', 'Neutral')}\n"
            f"Revenue Growth YoY: {facts.get('revenue_growth_yoy', 0)}\n"
            f"ROIC: {facts.get('roic', 0)}\n"
            f"Debt/Equity: {facts.get('debt_to_equity', 0)}\n"
            f"Operating Margin: {facts.get('operating_margin', 0)}\n"
            f"Net Margin: {facts.get('net_margin', 0)}\n"
            f"FCF: {facts.get('free_cash_flow', 0)}\n"
            f"Noticias: {joined_headlines}\n"
            "business_overview debe explicar en 1 o 2 frases que hace la empresa y como gana dinero. "
            "investment_thesis debe tener 2 o 3 frases y conectar metricas con noticias. "
            "key_risks debe resumir 2 o 3 riesgos materiales para los proximos 6 a 12 meses. "
            "executive_summary debe ser una sola frase breve y especifica del ticker. "
            "near_term_outlook debe resumir en 1 o 2 frases el sesgo esperado para las proximas semanas usando solo noticias recientes; si la senal no es clara, indica un sesgo neutral. "
            "Considera ROIC alto como senal positiva de calidad y ventaja economica. "
            "Considera Debt/Equity alto como riesgo de apalancamiento. "
            "Considera crecimiento bajo o deterioro de margenes como senal de debilidad o maduracion. "
            "Si los datos son mixtos, refleja el balance entre fortalezas y riesgos. "
            "Evita frases genericas que podrian aplicar a cualquier empresa."
        )


class LLMSummaryGenerator:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )
        self.provider = settings.llm_provider
        self.gemini_client = None
        self.openai_client = None
        self.lmstudio_client = None
        self.ollama_client = None

        if settings.enable_llm_summary:
            if settings.llm_provider == "gemini":
                self.gemini_client = GeminiCLIClient(
                    command=settings.gemini_cli_command,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    max_headlines=settings.ollama_max_headlines_per_ticker,
                )
            elif settings.llm_provider == "lmstudio":
                self.lmstudio_client = LMStudioClient(
                    base_url=settings.lmstudio_base_url,
                    model=settings.lmstudio_model,
                    api_key=settings.lmstudio_api_key,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    max_headlines=settings.ollama_max_headlines_per_ticker,
                )
            elif settings.llm_provider == "openai" and settings.openai_api_key:
                self.openai_client = self._build_openai_client()
            elif settings.llm_provider == "ollama":
                self.ollama_client = OllamaClient(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    max_headlines=settings.ollama_max_headlines_per_ticker,
                    api_key=settings.ollama_api_key,
                )

        self.lmstudio_health: tuple[bool, str] = (False, "lmstudio_not_checked")
        self.ollama_health: tuple[bool, str] = (False, "ollama_not_checked")
        self.gemini_health: tuple[bool, str] = (False, "gemini_not_checked")
        self.ollama_failures = 0
        self.gemini_failures = 0
        self.ollama_generation_disabled = False
        self.gemini_generation_disabled = False
        self.batch_top_n = settings.ollama_batch_top_n

        if settings.enable_llm_summary:
            if self.gemini_client is not None:
                self.gemini_health = self.gemini_client.health_check()
                if self.gemini_health[0]:
                    self.logger.info("Gemini CLI disponible")
                else:
                    self.logger.warning("Gemini CLI no disponible: %s", self.gemini_health[1])

            # Pre-cargar Ollama si se necesita como fallback o si es el principal
            if self.ollama_client is None and (settings.llm_provider == "gemini" or settings.llm_provider == "ollama"):
                 self.ollama_client = OllamaClient(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    max_headlines=settings.ollama_max_headlines_per_ticker,
                    api_key=settings.ollama_api_key,
                )

            if self.lmstudio_client is not None:
                self.lmstudio_health = self.lmstudio_client.health_check()
                if self.lmstudio_health[0]:
                    self.logger.info("LM Studio disponible con modelo %s", settings.lmstudio_model)
                else:
                    self.logger.warning("LM Studio no disponible: %s", self.lmstudio_health[1])
            
            if self.ollama_client is not None:
                self.ollama_health = self.ollama_client.health_check()
                if self.ollama_health[0]:
                    self.logger.info("Ollama disponible con modelo %s", settings.ollama_model)
                else:
                    self.logger.warning("Ollama no disponible: %s", self.ollama_health[1])

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

    def _gemini_narrative(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if self.gemini_client is None:
            return self._fallback_narrative(row, "gemini_client_unavailable")
        if self.gemini_generation_disabled:
            return self._fallback_narrative(row, "gemini_degraded_after_failures")

        healthy, reason = self.gemini_health
        if not healthy:
            return self._fallback_narrative(row, f"gemini_unhealthy:{reason}")

        try:
            parsed = self.gemini_client.generate_summary(
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
                return self._fallback_narrative(row, "gemini_empty_response")
            parsed["llm_provider_used"] = "gemini"
            parsed["llm_status"] = "ok"
            parsed["llm_fallback_reason"] = ""
            self.gemini_failures = 0
            return parsed
        except Exception as exc:
            self.logger.warning("Gemini narrative fallback for %s: %s", row.get("ticker"), exc)
            self.gemini_failures += 1
            if self.gemini_failures >= 3:
                self.gemini_generation_disabled = True
            return self._fallback_narrative(row, f"gemini_error:{exc}")

    def _lmstudio_narrative(self, row: pd.Series, headlines: List[str]) -> Dict[str, str]:
        if self.lmstudio_client is None:
            return self._fallback_narrative(row, "lmstudio_client_unavailable")

        try:
            parsed = self.lmstudio_client.generate_summary(
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
                return self._fallback_narrative(row, "lmstudio_empty_response")
            parsed["llm_provider_used"] = "lmstudio"
            parsed["llm_status"] = "ok"
            parsed["llm_fallback_reason"] = ""
            return parsed
        except Exception as exc:
            self.logger.warning("LM Studio narrative fallback for %s: %s", row.get("ticker"), exc)
            return self._fallback_narrative(row, f"lmstudio_error:{exc}")

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

        if provider == "gemini":
            result = self._gemini_narrative(row, headlines)
            if result.get("llm_status") == "ok":
                return result
            
            self.logger.warning("Gemini CLI fallo (%s), intentando Ollama como fallback", result.get("llm_fallback_reason"))
            result_ollama = self._ollama_narrative(row, headlines)
            if result_ollama.get("llm_status") == "ok":
                result_ollama["llm_fallback_reason"] = (
                    f"gemini_fallback:{result.get('llm_fallback_reason', 'unknown')}"
                )
                return result_ollama
            return self._fallback_narrative(
                row, f"chain_failed: gemini:{result.get('llm_fallback_reason')} -> ollama:{result_ollama.get('llm_fallback_reason')}"
            )

        if provider == "lmstudio":
            result = self._lmstudio_narrative(row, headlines)
            if result.get("llm_status") == "ok":
                return result
            self.logger.warning("LM Studio fallo, intentando Ollama como fallback")
            result_ollama = self._ollama_narrative(row, headlines)
            if result_ollama.get("llm_status") == "ok":
                result_ollama["llm_fallback_reason"] = (
                    f"lmstudio_fallback:{result.get('llm_fallback_reason', 'unknown')}"
                )
                return result_ollama
            return self._fallback_narrative(
                row, f"chain_failed: lmstudio:{result.get('llm_fallback_reason')} -> ollama:{result_ollama.get('llm_fallback_reason')}"
            )

        if provider == "ollama":
            result = self._ollama_narrative(row, headlines)
            if result.get("llm_status") == "ok":
                return result
            return self._fallback_narrative(row, f"ollama_failed:{result.get('llm_fallback_reason')}")

        if provider == "openai":
            return self._openai_narrative(row, headlines)

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
