from __future__ import annotations

from typing import List

import pandas as pd

from config.settings import settings
from ingestion.financial_data import CompanyFinancialBundle
from processing.ratios import RatioCalculator
from utils.helpers import contains_any, normalize_text
from utils.logger import setup_logger


class FeatureEngineeringPipeline:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    def _is_target_sector(self, sector: str, industry: str) -> bool:
        sector_text = f"{normalize_text(sector)} {normalize_text(industry)}"
        return contains_any(sector_text, settings.target_sectors)

    def build_feature_dataset(self, bundles: List[CompanyFinancialBundle]) -> pd.DataFrame:
        rows = []
        for bundle in bundles:
            try:
                metrics = RatioCalculator.compute_metrics(bundle)
                metrics["is_target_sector"] = self._is_target_sector(
                    metrics.get("sector", ""), metrics.get("industry", "")
                )
                metrics["is_small_mid_cap"] = (
                    metrics.get("market_cap", 0) > 0
                    and metrics.get("market_cap", 0) < settings.small_mid_cap_threshold
                )
                metrics["high_potential_candidate"] = (
                    metrics["is_target_sector"]
                    and metrics["is_small_mid_cap"]
                    and metrics.get("revenue_growth_yoy", 0) > settings.high_growth_threshold
                )
                rows.append(metrics)
            except Exception as exc:
                self.logger.exception(
                    "Feature engineering failed for %s: %s", bundle.ticker, exc
                )

        if not rows:
            self.logger.warning("No features generated. Returning empty dataset")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.replace([float("inf"), float("-inf")], 0, inplace=True)

        numeric_columns = df.select_dtypes(include=["number"]).columns
        text_columns = df.select_dtypes(include=["object"]).columns

        if len(numeric_columns) > 0:
            df[numeric_columns] = df[numeric_columns].fillna(0)
        if len(text_columns) > 0:
            df[text_columns] = df[text_columns].fillna("")

        self.logger.info("Feature dataset generated with %s rows", len(df))
        return df
