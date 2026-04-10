from __future__ import annotations

import json
from typing import Dict, List, Tuple

import requests


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_headlines: int,
        api_key: str = "",
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

    def health_check(self) -> Tuple[bool, str]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                headers=self._headers(),
                timeout=min(self.timeout, 10),
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
            models = payload.get("models", []) if isinstance(payload, dict) else []
            names = {item.get("name", "") for item in models if isinstance(item, dict)}
            if self.model in names:
                return True, "ok"
            return False, f"modelo {self.model} no disponible"
        except Exception as exc:
            return False, str(exc)

    def generate_summary(self, ticker: str, headlines: List[str], facts: Dict[str, object]) -> Dict[str, str]:
        prompt = self._build_prompt(
            ticker=ticker,
            headlines=headlines,
            facts=facts,
            max_headlines=self.max_headlines,
        )
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json() if response.content else {}
        text = payload.get("response", "") if isinstance(payload, dict) else ""
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
            "Eres un analista fundamental senior con enfoque buy-side y sell-side. "
            "Evalua si el perfil actual del ticker sugiere oportunidad alcista, bajista o neutral usando fundamentales y noticias recientes. "
            "Responde SIEMPRE en espanol. "
            "Responde SOLO un JSON valido con exactamente estas llaves: business_overview, investment_thesis, key_risks, executive_summary, near_term_outlook. "
            "No uses markdown. No agregues texto fuera del JSON. No inventes llaves adicionales. "
            "Usa este formato exacto: {\"business_overview\":\"...\",\"investment_thesis\":\"...\",\"key_risks\":\"...\",\"executive_summary\":\"...\",\"near_term_outlook\":\"...\"}. "
            "business_overview debe explicar en 1 o 2 frases que hace la empresa y como gana dinero. "
            "investment_thesis debe tener 2 o 3 frases y conectar metricas con noticias. "
            "key_risks debe resumir 2 o 3 riesgos materiales para los proximos 6 a 12 meses. "
            "executive_summary debe ser una sola frase breve y especifica del ticker. "
            "near_term_outlook debe resumir en 1 o 2 frases el sesgo esperado para las proximas semanas usando solo noticias recientes; si la senal no es clara, indica un sesgo neutral. "
            "Considera ROIC alto como senal positiva de calidad y ventaja economica. "
            "Considera Debt/Equity alto como riesgo de apalancamiento. "
            "Considera crecimiento bajo o deterioro de margenes como senal de debilidad o maduracion. "
            "Si los datos son mixtos, refleja el balance entre fortalezas y riesgos. "
            "Evita frases genericas que podrian aplicar a cualquier empresa.\n"
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
            f"Noticias: {joined_headlines}"
        )
