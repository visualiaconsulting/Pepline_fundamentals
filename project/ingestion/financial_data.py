from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    company_name: str
    sector: str
    industry: str
    business_summary: str
    exchange: str
    market_cap: float
    currency: str
    trailing_pe: float
    forward_pe: float
    ev_to_ebitda: float
    previous_close: float
    previous_close_date: str
    current_price: float
    target_price: float
    analyst_count: int
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

    @staticmethod
    def _format_history_date(value: object) -> str:
        if value is None:
            return ""

        try:
            timestamp = pd.Timestamp(value)
        except Exception:
            return ""

        if pd.isna(timestamp):
            return ""

        try:
            if timestamp.tzinfo is not None:
                timestamp = timestamp.tz_convert(None)
        except Exception:
            pass

        return timestamp.strftime("%Y-%m-%d")

    def _extract_market_snapshot(self, ticker_obj: yf.Ticker) -> Dict[str, object]:
        history = pd.DataFrame()
        try:
            history = ensure_dataframe(ticker_obj.history(period="5d", auto_adjust=False))
        except Exception as exc:
            self.logger.warning("Failed to fetch price history for %s: %s", ticker_obj.ticker, exc)

        if history.empty:
            return {
                "previous_close": 0.0,
                "previous_close_date": "",
                "current_price": 0.0,
            }

        close_series = pd.to_numeric(history.get("Close"), errors="coerce").dropna()
        if close_series.empty:
            return {
                "previous_close": 0.0,
                "previous_close_date": "",
                "current_price": 0.0,
            }

        latest_idx = close_series.index[-1]
        latest_close = safe_float(close_series.iloc[-1])

        return {
            "previous_close": latest_close,
            "previous_close_date": self._format_history_date(latest_idx),
            "current_price": latest_close,
        }

    def _extract_company_info(self, ticker_obj: yf.Ticker) -> Dict:
        info = ticker_obj.info or {}
        fast_info = getattr(ticker_obj, "fast_info", {}) or {}
        snapshot = self._extract_market_snapshot(ticker_obj)

        current_price = safe_float(
            info.get(
                "currentPrice",
                fast_info.get("lastPrice", snapshot.get("current_price", 0)),
            )
        )
        previous_close = safe_float(
            info.get(
                "previousClose",
                fast_info.get("previousClose", snapshot.get("previous_close", 0)),
            )
        )

        target_price_raw = info.get("targetMeanPrice", info.get("targetMedianPrice", 0))
        analyst_count_raw = info.get("numberOfAnalystOpinions", info.get("numberOfAnalysts", 0))

        return {
            "company_name": str(
                info.get("shortName")
                or info.get("longName")
                or getattr(ticker_obj, "ticker", "")
            ),
            "sector": str(info.get("sector", "Unknown")),
            "industry": str(info.get("industry", "Unknown")),
            "business_summary": str(info.get("longBusinessSummary", "")).strip(),
            "exchange": str(info.get("fullExchangeName") or info.get("exchange") or "Unknown"),
            "market_cap": safe_float(info.get("marketCap", fast_info.get("marketCap", 0))),
            "currency": str(info.get("currency", "USD")),
            "trailing_pe": safe_float(info.get("trailingPE", 0)),
            "forward_pe": safe_float(info.get("forwardPE", 0)),
            "ev_to_ebitda": safe_float(info.get("enterpriseToEbitda", 0)),
            "previous_close": previous_close,
            "previous_close_date": str(snapshot.get("previous_close_date", "")),
            "current_price": current_price,
            "target_price": safe_float(target_price_raw, default=0.0),
            "analyst_count": int(pd.to_numeric(analyst_count_raw, errors="coerce") or 0),
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
                company_name=info["company_name"],
                sector=info["sector"],
                industry=info["industry"],
                business_summary=info["business_summary"],
                exchange=info["exchange"],
                market_cap=info["market_cap"],
                currency=info["currency"],
                trailing_pe=info["trailing_pe"],
                forward_pe=info["forward_pe"],
                ev_to_ebitda=info["ev_to_ebitda"],
                previous_close=info["previous_close"],
                previous_close_date=info["previous_close_date"],
                current_price=info["current_price"],
                target_price=info["target_price"],
                analyst_count=info["analyst_count"],
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
