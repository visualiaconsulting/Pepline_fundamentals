from __future__ import annotations

import pandas as pd

from config.settings import settings
from utils.helpers import clamp
from utils.logger import setup_logger


class CompanyScorer:
    WEIGHTS = {
        "quality_score": 0.30,
        "growth_score": 0.25,
        "profitability_score": 0.20,
        "risk_score": 0.15,
        "valuation_score": 0.10,
    }

    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    @staticmethod
    def classify(score: float) -> str:
        if score >= 80:
            return "Excelente"
        if score >= 65:
            return "Buena"
        if score >= 50:
            return "Neutral"
        return "Riesgosa"

    def score(self, analyzed_df: pd.DataFrame) -> pd.DataFrame:
        if analyzed_df.empty:
            self.logger.warning("Received empty dataframe in scoring")
            return analyzed_df

        df = analyzed_df.copy()

        weighted_score = 0
        for col, weight in self.WEIGHTS.items():
            weighted_score += df[col] * weight

        df["total_score"] = weighted_score.apply(lambda x: clamp(float(x), 0, 100))
        df["classification"] = df["total_score"].apply(self.classify)

        self.logger.info("Scoring calculated for %s companies", len(df))
        return df
