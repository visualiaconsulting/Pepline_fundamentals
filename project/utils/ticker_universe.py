from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

from config.settings import settings
from ingestion.ticker_discovery import DiscoveryCandidate
from utils.logger import setup_logger


@dataclass
class UniverseBuildResult:
    final_tickers: List[str]
    origin_by_ticker: Dict[str, str]
    discovery_log: pd.DataFrame
    accepted_discovered_count: int


class TickerUniverseBuilder:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for value in values:
            clean_value = value.strip().upper()
            if not clean_value or clean_value in seen:
                continue
            seen.add(clean_value)
            deduped.append(clean_value)
        return deduped

    def build(
        self,
        manual_tickers: List[str],
        discovered_candidates: List[DiscoveryCandidate],
        blocklist: List[str],
        max_new_tickers: int,
    ) -> UniverseBuildResult:
        timestamp = datetime.now(timezone.utc).isoformat()
        manual_clean = self._dedupe(manual_tickers)
        blocklist_set = {ticker.strip().upper() for ticker in blocklist if ticker.strip()}
        manual_set = set(manual_clean)

        accepted_new: List[str] = []
        origin_by_ticker: Dict[str, str] = {ticker: "manual" for ticker in manual_clean}
        log_rows = [
            {
                "run_timestamp": timestamp,
                "ticker": ticker,
                "source": "manual",
                "status": "included",
                "reason": "preferred_universe",
            }
            for ticker in manual_clean
        ]

        for candidate in discovered_candidates:
            ticker = candidate.ticker.strip().upper()
            if not ticker:
                continue

            row = {
                "run_timestamp": timestamp,
                "ticker": ticker,
                "source": candidate.source,
                "status": "included",
                "reason": candidate.discovery_reason,
            }

            if ticker in blocklist_set:
                row["status"] = "excluded"
                row["reason"] = "blocklist"
                log_rows.append(row)
                continue

            if ticker in manual_set:
                origin_by_ticker[ticker] = "manual+discovered"
                row["status"] = "excluded"
                row["reason"] = "already_in_manual_universe"
                log_rows.append(row)
                continue

            if ticker in accepted_new:
                row["status"] = "excluded"
                row["reason"] = "duplicate_discovered_ticker"
                log_rows.append(row)
                continue

            if len(accepted_new) >= max_new_tickers:
                row["status"] = "excluded"
                row["reason"] = "max_new_tickers_reached"
                log_rows.append(row)
                continue

            accepted_new.append(ticker)
            origin_by_ticker[ticker] = "discovered"
            log_rows.append(row)

        final_tickers = manual_clean + accepted_new
        discovery_log = pd.DataFrame(log_rows)

        self.logger.info(
            "Universe build completed: %s manual + %s discovered accepted = %s total",
            len(manual_clean),
            len(accepted_new),
            len(final_tickers),
        )

        return UniverseBuildResult(
            final_tickers=final_tickers,
            origin_by_ticker=origin_by_ticker,
            discovery_log=discovery_log,
            accepted_discovered_count=len(accepted_new),
        )

    def export_discovery_log(self, result: UniverseBuildResult, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.discovery_log.to_csv(output_path, index=False)
        self.logger.info("Discovery log exported to %s", output_path)