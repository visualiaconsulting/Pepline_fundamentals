from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

from config.settings import settings
from ingestion.ticker_discovery import DiscoveryCandidate
from utils import ticker_library
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
        include_global_sp500: bool = False,
        include_global_europe: bool = False,
        include_global_hk: bool = False,
    ) -> UniverseBuildResult:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Combinar manuales con libreria global segun flags
        base_tickers = list(manual_tickers)
        library_mapping = []
        if include_global_sp500:
            library_mapping.extend([(t, "library_sp500") for t in ticker_library.SP500_TOP_200])
        if include_global_europe:
            library_mapping.extend([(t, "library_europe") for t in ticker_library.EUROPE_TOP_100])
        if include_global_hk:
            library_mapping.extend([(t, "library_hk") for t in ticker_library.HK_TOP_100])

        manual_clean = self._dedupe(base_tickers)
        manual_set = set(manual_clean)
        blocklist_set = {ticker.strip().upper() for ticker in blocklist if ticker.strip()}

        accepted_expanded: List[str] = []
        origin_by_ticker: Dict[str, str] = {ticker: "manual" for ticker in manual_clean}
        
        log_rows = []
        for ticker in manual_clean:
            log_rows.append({
                "run_timestamp": timestamp,
                "ticker": ticker,
                "source": "manual",
                "status": "included",
                "reason": "preferred_universe",
            })

        # Procesar tickers de la libreria
        for ticker, source_name in library_mapping:
            ticker = ticker.strip().upper()
            if not ticker or ticker in blocklist_set or ticker in manual_set or ticker in accepted_expanded:
                continue
            
            accepted_expanded.append(ticker)
            origin_by_ticker[ticker] = source_name
            log_rows.append({
                "run_timestamp": timestamp,
                "ticker": ticker,
                "source": source_name,
                "status": "included",
                "reason": "global_market_expansion",
            })

        accepted_discovery: List[str] = []
        # Procesar candidatos descubiertos (Finviz, etc)
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

            if ticker in manual_set or ticker in accepted_expanded:
                # No actualizamos origin aqui para mantener la fuente de la libreria si ya estaba
                row["status"] = "excluded"
                row["reason"] = "already_in_universe"
                log_rows.append(row)
                continue

            if ticker in accepted_discovery:
                row["status"] = "excluded"
                row["reason"] = "duplicate_discovered_ticker"
                log_rows.append(row)
                continue

            if len(accepted_discovery) >= max_new_tickers:
                row["status"] = "excluded"
                row["reason"] = "max_new_tickers_reached"
                log_rows.append(row)
                continue

            accepted_discovery.append(ticker)
            origin_by_ticker[ticker] = "discovered"
            log_rows.append(row)

        final_tickers = manual_clean + accepted_expanded + accepted_discovery
        discovery_log = pd.DataFrame(log_rows)

        self.logger.info(
            "Universe build completed: %s manual + %s library + %s discovery = %s total",
            len(manual_clean),
            len(accepted_expanded),
            len(accepted_discovery),
            len(final_tickers),
        )

        return UniverseBuildResult(
            final_tickers=final_tickers,
            origin_by_ticker=origin_by_ticker,
            discovery_log=discovery_log,
            accepted_discovered_count=len(accepted_expanded) + len(accepted_discovery),
        )

    def export_discovery_log(self, result: UniverseBuildResult, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.discovery_log.to_csv(output_path, index=False)
        self.logger.info("Discovery log exported to %s", output_path)
