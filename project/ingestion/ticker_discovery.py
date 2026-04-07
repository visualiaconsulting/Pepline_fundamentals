from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from typing import List

import pandas as pd

from config.settings import settings
from utils.helpers import normalize_text, safe_float
from utils.logger import setup_logger


@dataclass
class DiscoveryCandidate:
    ticker: str
    company: str
    sector: str
    industry: str
    country: str
    market_cap: float
    source: str
    discovery_reason: str


class TickerDiscoveryEngine:
    FINVIZ_SECTOR_MAP = {
        "technology": ["Technology"],
        "semiconductors": ["Technology"],
        "energy": ["Energy"],
        "oil & gas": ["Energy"],
        "renewable energy": ["Energy", "Utilities"],
        "defense": ["Industrials"],
        "aerospace": ["Industrials"],
        "mining": ["Basic Materials"],
        "gold": ["Basic Materials"],
        "copper": ["Basic Materials"],
        "lithium": ["Basic Materials"],
        "rare earth": ["Basic Materials"],
        "metals & mining": ["Basic Materials"],
        "automation": ["Industrials", "Technology"],
        "industrials": ["Industrials"],
    }

    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )
        self.overview_cls = self._load_overview_class()

    @staticmethod
    def _load_overview_class():
        try:
            module = importlib.import_module("finvizfinance.screener.overview")
            return getattr(module, "Overview")
        except Exception:
            return None

    def _map_discovery_sectors(self, sector_keywords: List[str]) -> List[str]:
        mapped: List[str] = []
        for keyword in sector_keywords:
            clean_keyword = normalize_text(keyword)
            for source_keyword, finviz_sectors in self.FINVIZ_SECTOR_MAP.items():
                if source_keyword in clean_keyword:
                    mapped.extend(finviz_sectors)

        unique_mapped: List[str] = []
        for sector in mapped:
            if sector not in unique_mapped:
                unique_mapped.append(sector)

        return unique_mapped or ["Technology", "Energy", "Industrials", "Basic Materials"]

    @staticmethod
    def _growth_filter_label(threshold: float) -> str:
        if threshold >= 30:
            return "Over 30%"
        if threshold >= 25:
            return "Over 25%"
        if threshold >= 20:
            return "Over 20%"
        if threshold >= 15:
            return "Over 15%"
        if threshold >= 10:
            return "Over 10%"
        if threshold >= 5:
            return "Over 5%"
        return "Positive (>0%)"

    def _fetch_sector_candidates(self, finviz_sector: str, limit: int) -> List[DiscoveryCandidate]:
        if self.overview_cls is None:
            self.logger.warning("finvizfinance is not available, skipping ticker discovery")
            return []

        overview = self.overview_cls()
        growth_filter = self._growth_filter_label(settings.discovery_min_sales_growth)
        filters_dict = {
            "Sector": finviz_sector,
            "Sales growthqtr over qtr": growth_filter,
        }

        try:
            overview.set_filter(filters_dict=filters_dict)
            screener_df = overview.screener_view(
                order="Sales growth qtr over qtr",
                limit=limit,
                verbose=0,
                ascend=False,
            )
        except Exception as exc:
            self.logger.warning("Discovery query failed for sector %s: %s", finviz_sector, exc)
            return []

        if screener_df is None or screener_df.empty:
            return []

        candidates: List[DiscoveryCandidate] = []
        for _, row in screener_df.iterrows():
            market_cap = safe_float(row.get("Market Cap"), 0)
            if market_cap < settings.discovery_min_market_cap:
                continue
            if market_cap > settings.discovery_max_market_cap:
                continue

            ticker = str(row.get("Ticker", "")).strip().upper()
            if not ticker:
                continue

            candidates.append(
                DiscoveryCandidate(
                    ticker=ticker,
                    company=str(row.get("Company", "")).strip(),
                    sector=str(row.get("Sector", finviz_sector)).strip(),
                    industry=str(row.get("Industry", "")).strip(),
                    country=str(row.get("Country", "")).strip(),
                    market_cap=market_cap,
                    source="finviz",
                    discovery_reason=(
                        f"sector={finviz_sector};sales_growth_filter={growth_filter};"
                        f"market_cap_between={int(settings.discovery_min_market_cap)}-"
                        f"{int(settings.discovery_max_market_cap)}"
                    ),
                )
            )

        return candidates

    def discover_tickers(self) -> List[DiscoveryCandidate]:
        if not settings.ticker_discovery_enabled:
            return []

        if settings.discovery_source != "finviz":
            self.logger.warning(
                "Unsupported discovery source '%s'. Falling back to manual universe only.",
                settings.discovery_source,
            )
            return []

        finviz_sectors = self._map_discovery_sectors(settings.discovery_sectors)
        per_sector_limit = max(settings.discovery_max_new_tickers * 3, 20)

        candidates: List[DiscoveryCandidate] = []
        seen = set()
        for finviz_sector in finviz_sectors:
            sector_candidates = self._fetch_sector_candidates(finviz_sector, per_sector_limit)
            for candidate in sector_candidates:
                if candidate.ticker in seen:
                    continue
                seen.add(candidate.ticker)
                candidates.append(candidate)

        self.logger.info(
            "Ticker discovery returned %s raw candidates across %s mapped sectors",
            len(candidates),
            len(finviz_sectors),
        )
        return candidates

    @staticmethod
    def candidates_to_frame(candidates: List[DiscoveryCandidate]) -> pd.DataFrame:
        if not candidates:
            return pd.DataFrame(
                columns=[
                    "ticker",
                    "company",
                    "sector",
                    "industry",
                    "country",
                    "market_cap",
                    "source",
                    "discovery_reason",
                ]
            )
        return pd.DataFrame([asdict(candidate) for candidate in candidates])