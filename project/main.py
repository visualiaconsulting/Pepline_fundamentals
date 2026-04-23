from __future__ import annotations

import traceback

from analysis.fundamental_analysis import FundamentalAnalyzer
from analysis.llm_summary import LLMSummaryGenerator
from analysis.scoring import CompanyScorer
from config.settings import settings
from ingestion.financial_data import FinancialDataIngestor
from ingestion.news_data import NewsDataIngestor
from ingestion.ticker_discovery import TickerDiscoveryEngine
from models.ranking_model import RankingModel
from processing.feature_engineering import FeatureEngineeringPipeline
from utils.logger import setup_logger
from utils.ticker_universe import TickerUniverseBuilder


def run_pipeline() -> None:
    logger = setup_logger("main", settings.log_level, settings.logs_dir)

    logger.info("Starting pipeline: %s", settings.project_name)
    financial_ingestor = FinancialDataIngestor()
    news_ingestor = NewsDataIngestor()
    discovery_engine = TickerDiscoveryEngine()
    universe_builder = TickerUniverseBuilder()
    feature_pipeline = FeatureEngineeringPipeline()
    analyzer = FundamentalAnalyzer()
    scorer = CompanyScorer()
    llm_summary = LLMSummaryGenerator()
    ranking_model = RankingModel()

    try:
        final_universe = list(settings.manual_universe_tickers)
        origin_by_ticker = {ticker: "manual" for ticker in final_universe}

        if settings.ticker_discovery_enabled:
            discovered_candidates = discovery_engine.discover_tickers()
            universe_result = universe_builder.build(
                manual_tickers=settings.manual_universe_tickers,
                discovered_candidates=discovered_candidates,
                blocklist=settings.ticker_blocklist,
                max_new_tickers=settings.discovery_max_new_tickers,
                include_global_sp500=settings.include_global_sp500,
                include_global_europe=settings.include_global_europe,
                include_global_hk=settings.include_global_hk,
            )
            final_universe = universe_result.final_tickers
            origin_by_ticker = universe_result.origin_by_ticker
            universe_builder.export_discovery_log(universe_result, settings.discovery_log_path)
        else:
            logger.info("Ticker discovery disabled. Using manual universe only")

        settings.universe_tickers = final_universe
        logger.info("Universe size: %s tickers", len(final_universe))

        bundles = financial_ingestor.fetch_universe_financials(final_universe)
        if not bundles:
            logger.error("Pipeline stopped: no financial data was collected")
            return

        news_df = news_ingestor.fetch_universe_news(final_universe)
        feature_df = feature_pipeline.build_feature_dataset(bundles)

        if feature_df.empty:
            logger.error("Pipeline stopped: feature engineering returned empty dataframe")
            return

        feature_df["ticker_origin"] = feature_df["ticker"].map(origin_by_ticker).fillna("manual")

        analyzed_df = analyzer.analyze(feature_df)
        scored_df = scorer.score(analyzed_df)
        ranking_df = ranking_model.rank(scored_df)
        ranking_df = llm_summary.enrich_dataframe(ranking_df, news_df)

        ranking_model.export_outputs(ranking_df, news_df)

        top10 = ranking_df[["rank", "ticker", "total_score", "classification"]].head(10)
        logger.info("Top 10 opportunities:\n%s", top10.to_string(index=False))

        logger.info("Pipeline completed successfully")

    except Exception as exc:
        logger.error("Unhandled pipeline error: %s", exc)
        logger.debug(traceback.format_exc())
        raise


if __name__ == "__main__":
    run_pipeline()
