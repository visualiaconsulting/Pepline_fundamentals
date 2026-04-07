from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import settings
from utils.logger import setup_logger


class RankingModel:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )

    def rank(self, scored_df: pd.DataFrame) -> pd.DataFrame:
        if scored_df.empty:
            self.logger.warning("Empty dataframe received in ranking model")
            return scored_df

        ranking = scored_df.sort_values(
            by=["total_score", "revenue_growth_yoy", "roic"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

        ranking["rank"] = ranking.index + 1
        return ranking

    def export_outputs(self, ranking_df: pd.DataFrame, news_df: pd.DataFrame) -> None:
        if ranking_df.empty:
            self.logger.warning("No ranking to export")
            return

        data_dir: Path = settings.data_dir
        reports_dir = data_dir / "reports"
        data_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        ranking_path = data_dir / "company_ranking.csv"
        top10_path = data_dir / "top10_opportunities.csv"

        ranking_df.to_csv(ranking_path, index=False)
        ranking_df.head(10).to_csv(top10_path, index=False)

        for _, row in ranking_df.iterrows():
            ticker = row["ticker"]
            company_news = news_df[news_df["ticker"] == ticker] if not news_df.empty else pd.DataFrame()

            headline = "Sin noticias recientes"
            if not company_news.empty:
                headline = str(company_news.iloc[0].get("title", "Sin noticias recientes"))

            report = (
                f"Ticker: {ticker}\n"
                f"Rank: {row['rank']}\n"
                f"Score Total: {row['total_score']:.2f}\n"
                f"Clasificacion: {row['classification']}\n"
                f"Sector: {row.get('sector', 'N/A')}\n"
                f"Crecimiento YoY: {row.get('revenue_growth_yoy', 0):.2f}%\n"
                f"ROIC: {row.get('roic', 0):.2f}%\n"
                f"Debt/Equity: {row.get('debt_to_equity', 0):.2f}\n"
                f"FCF: {row.get('free_cash_flow', 0):,.2f}\n"
                f"High Potential Candidate: {bool(row.get('high_potential_candidate', False))}\n"
                f"Tesis preliminar: {row.get('fundamental_view', '')}\n"
                f"Investment Thesis: {row.get('investment_thesis', '')}\n"
                f"Key Risks: {row.get('key_risks', '')}\n"
                f"Executive Summary: {row.get('executive_summary', '')}\n"
                f"Titular clave: {headline}\n"
            )

            with open(reports_dir / f"{ticker}_report.txt", "w", encoding="utf-8") as file:
                file.write(report)

        self.logger.info("Outputs exported: %s and %s", ranking_path, top10_path)
