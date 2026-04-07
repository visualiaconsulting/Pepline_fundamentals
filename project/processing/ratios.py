from __future__ import annotations

from typing import Iterable

import pandas as pd

from ingestion.financial_data import CompanyFinancialBundle
from utils.helpers import safe_float


class RatioCalculator:
    @staticmethod
    def _get_latest_and_previous(columns: Iterable) -> tuple:
        ordered = sorted(columns, reverse=True)
        latest = ordered[0] if len(ordered) >= 1 else None
        previous = ordered[1] if len(ordered) >= 2 else None
        return latest, previous

    @staticmethod
    def _extract_value(statement_df: pd.DataFrame, aliases: list[str], column) -> float:
        if statement_df.empty or column is None:
            return 0.0

        alias_set = {alias.strip().lower() for alias in aliases}
        for idx in statement_df.index:
            name = str(idx).strip().lower()
            if name in alias_set:
                return safe_float(statement_df.loc[idx, column])
        return 0.0

    @classmethod
    def compute_metrics(cls, bundle: CompanyFinancialBundle) -> dict:
        income = bundle.income_statement
        balance = bundle.balance_sheet
        cashflow = bundle.cashflow

        latest_col, prev_col = cls._get_latest_and_previous(income.columns)
        bal_latest_col, _ = cls._get_latest_and_previous(balance.columns)
        cash_latest_col, _ = cls._get_latest_and_previous(cashflow.columns)

        revenue = cls._extract_value(income, ["Total Revenue", "Revenue"], latest_col)
        revenue_prev = cls._extract_value(income, ["Total Revenue", "Revenue"], prev_col)
        gross_profit = cls._extract_value(income, ["Gross Profit"], latest_col)
        operating_income = cls._extract_value(income, ["Operating Income", "EBIT"], latest_col)
        net_income = cls._extract_value(income, ["Net Income"], latest_col)
        pretax_income = cls._extract_value(income, ["Pretax Income", "Income Before Tax"], latest_col)
        income_tax = cls._extract_value(income, ["Tax Provision", "Income Tax Expense"], latest_col)

        operating_cashflow = cls._extract_value(
            cashflow,
            ["Operating Cash Flow", "Total Cash From Operating Activities"],
            cash_latest_col,
        )
        capex_raw = cls._extract_value(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures"],
            cash_latest_col,
        )
        capex_spend = abs(capex_raw)
        fcf = operating_cashflow - capex_spend

        total_debt = cls._extract_value(
            balance,
            ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
            bal_latest_col,
        )
        equity = cls._extract_value(
            balance,
            ["Stockholders Equity", "Total Stockholder Equity", "Total Equity Gross Minority Interest"],
            bal_latest_col,
        )
        cash_equivalents = cls._extract_value(
            balance,
            ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
            bal_latest_col,
        )

        revenue_growth_yoy = ((revenue - revenue_prev) / abs(revenue_prev) * 100) if revenue_prev else 0.0
        gross_margin = (gross_profit / revenue * 100) if revenue else 0.0
        operating_margin = (operating_income / revenue * 100) if revenue else 0.0
        net_margin = (net_income / revenue * 100) if revenue else 0.0
        debt_to_equity = (total_debt / equity) if equity else 0.0
        capex_to_revenue = (capex_spend / revenue * 100) if revenue else 0.0

        effective_tax_rate = (income_tax / pretax_income) if pretax_income else 0.21
        effective_tax_rate = min(max(effective_tax_rate, 0.0), 0.35)
        nopat = operating_income * (1 - effective_tax_rate)
        invested_capital = total_debt + equity - cash_equivalents
        roic = (nopat / invested_capital * 100) if invested_capital else 0.0

        pe = bundle.trailing_pe if bundle.trailing_pe > 0 else bundle.forward_pe

        return {
            "ticker": bundle.ticker,
            "sector": bundle.sector,
            "industry": bundle.industry,
            "market_cap": bundle.market_cap,
            "currency": bundle.currency,
            "revenue_growth_yoy": revenue_growth_yoy,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
            "free_cash_flow": fcf,
            "roic": roic,
            "debt_to_equity": debt_to_equity,
            "capex_to_revenue": capex_to_revenue,
            "trailing_pe": bundle.trailing_pe,
            "forward_pe": bundle.forward_pe,
            "ev_to_ebitda": bundle.ev_to_ebitda,
            "valuation_pe": pe,
        }
