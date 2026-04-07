from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf

from config.settings import settings
from utils.helpers import ensure_dataframe, safe_float
from utils.logger import setup_logger


@dataclass
class CompanyFinancialBundle:
    ticker: str
    sector: str
    industry: str
    market_cap: float
    currency: str
    trailing_pe: float
    forward_pe: float
    ev_to_ebitda: float
    income_statement: pd.DataFrame
    balance_sheet: pd.DataFrame
    cashflow: pd.DataFrame


class FinancialDataIngestor:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    def _fetch_alpha_vantage_income_statement(self, ticker: str) -> Optional[pd.DataFrame]:
        if not settings.use_alpha_vantage or not settings.alpha_vantage_api_key:
            return None

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": ticker,
            "apikey": settings.alpha_vantage_api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=settings.request_timeout)
            response.raise_for_status()
            data = response.json().get("annualReports", [])
            if not data:
                return None
            df = pd.DataFrame(data)
            return df
        except Exception as exc:
            self.logger.warning("Alpha Vantage fallback failed for %s: %s", ticker, exc)
            return None

    def _safe_ticker(self, ticker: str) -> yf.Ticker:
        return yf.Ticker(ticker)

    def _extract_company_info(self, ticker_obj: yf.Ticker) -> Dict:
        info = ticker_obj.info or {}
        fast_info = getattr(ticker_obj, "fast_info", {}) or {}

        return {
            "sector": str(info.get("sector", "Unknown")),
            "industry": str(info.get("industry", "Unknown")),
            "market_cap": safe_float(info.get("marketCap", fast_info.get("marketCap", 0))),
            "currency": str(info.get("currency", "USD")),
            "trailing_pe": safe_float(info.get("trailingPE", 0)),
            "forward_pe": safe_float(info.get("forwardPE", 0)),
            "ev_to_ebitda": safe_float(info.get("enterpriseToEbitda", 0)),
        }

    def fetch_company_financials(self, ticker: str) -> Optional[CompanyFinancialBundle]:
        try:
            ticker_obj = self._safe_ticker(ticker)

            income_statement = ensure_dataframe(ticker_obj.financials)
            balance_sheet = ensure_dataframe(ticker_obj.balance_sheet)
            cashflow = ensure_dataframe(ticker_obj.cashflow)

            if income_statement.empty and settings.use_alpha_vantage:
                alpha_income = self._fetch_alpha_vantage_income_statement(ticker)
                if alpha_income is not None and not alpha_income.empty:
                    self.logger.info("Using Alpha Vantage income statement for %s", ticker)

            info = self._extract_company_info(ticker_obj)

            if income_statement.empty or balance_sheet.empty or cashflow.empty:
                self.logger.warning(
                    "Incomplete financial statements for %s. income=%s balance=%s cashflow=%s",
                    ticker,
                    not income_statement.empty,
                    not balance_sheet.empty,
                    not cashflow.empty,
                )

            bundle = CompanyFinancialBundle(
                ticker=ticker,
                sector=info["sector"],
                industry=info["industry"],
                market_cap=info["market_cap"],
                currency=info["currency"],
                trailing_pe=info["trailing_pe"],
                forward_pe=info["forward_pe"],
                ev_to_ebitda=info["ev_to_ebitda"],
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cashflow=cashflow,
            )
            return bundle
        except Exception as exc:
            self.logger.exception("Failed to fetch financial data for %s: %s", ticker, exc)
            return None

    def fetch_universe_financials(self, tickers: List[str]) -> List[CompanyFinancialBundle]:
        bundles: List[CompanyFinancialBundle] = []

        for ticker in tickers:
            company_bundle = self.fetch_company_financials(ticker)
            if company_bundle is not None:
                bundles.append(company_bundle)

        self.logger.info("Fetched financial bundles for %s/%s tickers", len(bundles), len(tickers))
        return bundles
