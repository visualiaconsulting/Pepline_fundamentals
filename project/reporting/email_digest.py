from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
import smtplib

import pandas as pd

from config.settings import settings
from reporting.document_builder import DocumentBuilder
from utils.logger import setup_logger


class EmailDigestSender:
    def __init__(self) -> None:
        self.logger = setup_logger(
            self.__class__.__name__, settings.log_level, settings.logs_dir
        )
        self.data_dir = settings.data_dir
        self.reports_dir = self.data_dir / "reports"
        self.ranking_path = self.data_dir / "top20_opportunities.csv"
        self.news_path = self.data_dir / "top20_news.csv"
        self.builder = DocumentBuilder()
        self.snapshot_md_path = self.reports_dir / "daily_email_digest.md"
        self.snapshot_path = self.reports_dir / "daily_email_digest.txt"

    def run(self) -> None:
        if not settings.email_report_enabled:
            self.logger.info("Email digest disabled. Skipping send.")
            return

        self._validate_config()
        ranking_df = self._load_csv(self.ranking_path, required=True)
        news_df = self._load_csv(self.news_path, required=False)
        markdown = self.builder.build_markdown(ranking_df, news_df, top_n=settings.email_report_top_n)
        body = self.builder.markdown_to_text(markdown)
        self._write_snapshots(markdown, body)
        self._send_email(body)
        self.logger.info(
            "Email digest snapshots generated: md=%s txt=%s",
            self.snapshot_md_path,
            self.snapshot_path,
        )
        self.logger.info("Email digest sent to %s", ", ".join(settings.email_report_to))

    def _validate_config(self) -> None:
        missing = []
        if not settings.email_report_to:
            missing.append("EMAIL_REPORT_TO")
        if not settings.email_report_from:
            missing.append("EMAIL_REPORT_FROM")
        if not settings.smtp_host:
            missing.append("SMTP_HOST")
        if not settings.smtp_user:
            missing.append("SMTP_USER")
        if not settings.smtp_pass:
            missing.append("SMTP_PASS")

        if missing:
            raise ValueError(f"Email digest misconfigured. Missing: {', '.join(missing)}")

    @staticmethod
    def _load_csv(path: Path, required: bool) -> pd.DataFrame:
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required report file not found: {path}")
            return pd.DataFrame(columns=["ticker", "title", "publisher", "link", "published"])
        return pd.read_csv(path)

    def _write_snapshots(self, markdown: str, body: str) -> None:
        self.builder.write_snapshot(markdown, self.snapshot_md_path)
        self.builder.write_snapshot(body, self.snapshot_path)

    def _send_email(self, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.email_report_from
        message["To"] = ", ".join(settings.email_report_to)
        message["Subject"] = (
            f"{settings.email_report_subject_prefix} - {datetime.now().strftime('%Y-%m-%d')}"
        )
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(message)


def main() -> None:
    sender = EmailDigestSender()
    sender.run()


if __name__ == "__main__":
    main()