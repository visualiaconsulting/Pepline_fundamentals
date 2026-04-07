from __future__ import annotations

import pandas as pd

from config.settings import settings
from utils.helpers import clamp
from utils.logger import setup_logger


class FundamentalAnalyzer:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    @staticmethod
    def _quality_score(row: pd.Series) -> float:
        roic = float(row.get("roic", 0))
        gross_margin = float(row.get("gross_margin", 0))
        fcf = float(row.get("free_cash_flow", 0))

        score = 0.0
        if roic > 15:
            score += 45
        elif roic > 8:
            score += 30
        else:
            score += 10

        if gross_margin > 50:
            score += 35
        elif gross_margin > 30:
            score += 20
        else:
            score += 8

        if fcf > 0:
            score += 20

        return clamp(score, 0, 100)

    @staticmethod
    def _growth_score(row: pd.Series) -> float:
        growth = float(row.get("revenue_growth_yoy", 0))

        if growth > 25:
            return 95
        if growth > 15:
            return 80
        if growth > 8:
            return 60
        if growth > 0:
            return 40
        return 20

    @staticmethod
    def _profitability_score(row: pd.Series) -> float:
        op_margin = float(row.get("operating_margin", 0))
        net_margin = float(row.get("net_margin", 0))

        score = 0.0
        score += 55 if op_margin > 20 else 35 if op_margin > 10 else 15
        score += 45 if net_margin > 15 else 30 if net_margin > 7 else 10

        return clamp(score, 0, 100)

    @staticmethod
    def _risk_score(row: pd.Series) -> float:
        debt_to_equity = float(row.get("debt_to_equity", 0))
        capex_to_revenue = float(row.get("capex_to_revenue", 0))

        score = 100.0
        if debt_to_equity > 2:
            score -= 55
        elif debt_to_equity > 1:
            score -= 30
        elif debt_to_equity > 0.5:
            score -= 15

        if capex_to_revenue > 30:
            score -= 20
        elif capex_to_revenue > 20:
            score -= 12

        return clamp(score, 0, 100)

    @staticmethod
    def _valuation_score(row: pd.Series) -> float:
        pe = float(row.get("valuation_pe", 0))

        if pe <= 0:
            return 50
        if pe < 15:
            return 90
        if pe < 25:
            return 70
        if pe < 40:
            return 50
        return 25

    @staticmethod
    def _qualitative_label(row: pd.Series) -> str:
        roic = float(row.get("roic", 0))
        debt_to_equity = float(row.get("debt_to_equity", 0))
        growth = float(row.get("revenue_growth_yoy", 0))

        if roic > 15 and debt_to_equity < 1 and growth > 15:
            return "Negocio de alta calidad con crecimiento sostenible"
        if debt_to_equity > 2:
            return "Riesgo financiero elevado por apalancamiento"
        if growth < 0:
            return "Desaceleracion o contraccion de ingresos"
        return "Fundamentales mixtos con potencial selectivo"

    def analyze(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        if feature_df.empty:
            self.logger.warning("Received empty feature dataset in analysis")
            return feature_df

        df = feature_df.copy()
        df["quality_score"] = df.apply(self._quality_score, axis=1)
        df["growth_score"] = df.apply(self._growth_score, axis=1)
        df["profitability_score"] = df.apply(self._profitability_score, axis=1)
        df["risk_score"] = df.apply(self._risk_score, axis=1)
        df["valuation_score"] = df.apply(self._valuation_score, axis=1)
        df["fundamental_view"] = df.apply(self._qualitative_label, axis=1)

        self.logger.info("Fundamental analysis finished for %s companies", len(df))
        return df
