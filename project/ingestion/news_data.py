from __future__ import annotations

from typing import Dict, List

import pandas as pd
import yfinance as yf

from config.settings import settings
from utils.logger import setup_logger


class NewsDataIngestor:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    def fetch_company_news(self, ticker: str, max_items: int = 15) -> pd.DataFrame:
        try:
            news_items = yf.Ticker(ticker).news or []
            if not news_items:
                return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

            records: List[Dict] = []
            for item in news_items[:max_items]:
                content = item.get("content", {})
                records.append(
                    {
                        "ticker": ticker,
                        "title": content.get("title") or item.get("title", ""),
                        "publisher": content.get("provider", {}).get("displayName", ""),
                        "link": content.get("canonicalUrl", {}).get("url", ""),
                        "published": content.get("pubDate") or item.get("providerPublishTime"),
                    }
                )

            df = pd.DataFrame.from_records(records)
            return df
        except Exception as exc:
            self.logger.exception("Failed to fetch news for %s: %s", ticker, exc)
            return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

    def fetch_universe_news(self, tickers: List[str], max_items: int = 15) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []

        for ticker in tickers:
            df = self.fetch_company_news(ticker, max_items=max_items)
            if not df.empty:
                frames.append(df)

        if not frames:
            self.logger.warning("No news records were collected for the provided universe")
            return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])

        news_df = pd.concat(frames, ignore_index=True)
        self.logger.info("Fetched %s news rows", len(news_df))
        return news_df
