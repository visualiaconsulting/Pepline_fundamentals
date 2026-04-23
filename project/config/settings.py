import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


def _get_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


def _get_csv_list(name: str, default: str = "") -> List[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass
class Settings:
    project_name: str = os.getenv("PROJECT_NAME", "Fundamental Research Pipeline")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    data_dir: Path = ROOT_DIR / "data"
    logs_dir: Path = ROOT_DIR / "logs"
    discovery_log_path: Path = data_dir / "discovery_log.csv"

    use_alpha_vantage: bool = _get_bool("USE_ALPHA_VANTAGE")
    alpha_vantage_api_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))

    manual_universe_tickers: List[str] = field(
        default_factory=lambda: [
            ticker.strip().upper()
            for ticker in _get_csv_list(
                "UNIVERSE_TICKERS",
                "NVDA,AMD,TSM,ASML,XOM,CVX,NEE,LMT,NOC,RHM.DE,RIO,FCX,ALB,CAT,ROK,ETN,SMCI,PLTR,CRDO",
            )
        ]
    )
    universe_tickers: List[str] = field(default_factory=list)

    target_sectors: List[str] = field(
        default_factory=lambda: [
            value.strip().lower()
            for value in _get_csv_list(
                "TARGET_SECTORS",
                "technology,semiconductors,energy,oil & gas,renewable energy,defense,aerospace,metals & mining,industrials",
            )
        ]
    )

    high_growth_threshold: float = float(os.getenv("HIGH_GROWTH_THRESHOLD", "15"))
    small_mid_cap_threshold: float = float(os.getenv("SMALL_MID_CAP_THRESHOLD", "10000000000"))

    ticker_discovery_enabled: bool = _get_bool("TICKER_DISCOVERY_ENABLED")
    discovery_source: str = os.getenv("DISCOVERY_SOURCE", "finviz").strip().lower()
    discovery_max_new_tickers: int = int(os.getenv("DISCOVERY_MAX_NEW_TICKERS", "10"))
    discovery_min_market_cap: float = float(os.getenv("DISCOVERY_MIN_MARKET_CAP", "100000000"))
    discovery_max_market_cap: float = float(os.getenv("DISCOVERY_MAX_MARKET_CAP", "10000000000"))
    discovery_min_sales_growth: float = float(
        os.getenv("DISCOVERY_MIN_SALES_GROWTH", os.getenv("HIGH_GROWTH_THRESHOLD", "15"))
    )
    discovery_sectors: List[str] = field(
        default_factory=lambda: [
            value.strip().lower()
            for value in _get_csv_list(
                "DISCOVERY_SECTORS",
                os.getenv(
                    "TARGET_SECTORS",
                    "technology,semiconductors,energy,oil & gas,renewable energy,defense,aerospace,metals & mining,industrials",
                ),
            )
        ]
    )
    ticker_blocklist: List[str] = field(
        default_factory=lambda: [ticker.strip().upper() for ticker in _get_csv_list("TICKER_BLOCKLIST", "")]
    )

    enable_llm_summary: bool = _get_bool("ENABLE_LLM_SUMMARY")
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    gemini_cli_command: str = os.getenv("GEMINI_CLI_COMMAND", "gemini").strip()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    lmstudio_base_url: str = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1").strip().rstrip("/")
    lmstudio_api_key: str = os.getenv("LMSTUDIO_API_KEY", "").strip()
    lmstudio_model: str = os.getenv("LMSTUDIO_MODEL", "gemma-4-e2b-it").strip()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
    ollama_api_key: str = os.getenv("OLLAMA_API_KEY", "").strip()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "minimax-m2.7:cloud").strip()
    ollama_timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    ollama_max_headlines_per_ticker: int = int(os.getenv("OLLAMA_MAX_HEADLINES_PER_TICKER", "8"))
    ollama_batch_top_n: int = int(os.getenv("OLLAMA_BATCH_TOP_N", "20"))
    ollama_enable_dashboard_summary: bool = _get_bool("OLLAMA_ENABLE_DASHBOARD_SUMMARY", "true")

    email_report_enabled: bool = _get_bool("EMAIL_REPORT_ENABLED")
    email_report_top_n: int = int(os.getenv("EMAIL_REPORT_TOP_N", "20"))
    email_report_news_per_ticker: int = int(os.getenv("EMAIL_REPORT_NEWS_PER_TICKER", "3"))
    email_report_subject_prefix: str = os.getenv("EMAIL_REPORT_SUBJECT_PREFIX", "Top oportunidades").strip()
    email_report_from: str = os.getenv("EMAIL_REPORT_FROM", "").strip()
    email_report_to: List[str] = field(default_factory=lambda: _get_csv_list("EMAIL_REPORT_TO", ""))
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "").strip()
    smtp_pass: str = os.getenv("SMTP_PASS", "").strip()
    smtp_use_tls: bool = _get_bool("SMTP_USE_TLS", "true")

    def __post_init__(self) -> None:
        self.universe_tickers = list(self.manual_universe_tickers)
        if self.llm_provider not in {"gemini", "openai", "ollama", "lmstudio", "rule-based", "rule_based"}:
            self.llm_provider = "gemini"
        self.ollama_batch_top_n = max(1, self.ollama_batch_top_n)
        self.email_report_top_n = max(1, self.email_report_top_n)
        self.email_report_news_per_ticker = max(1, self.email_report_news_per_ticker)


settings = Settings()
