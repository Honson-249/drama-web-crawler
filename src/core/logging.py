from __future__ import annotations

from datetime import date, datetime
import logging
import time

from src.core.settings import Settings
from src.core.storage import ensure_directory


class LocalTimeFormatter(logging.Formatter):
    """Formatter that outputs timestamps in configured timezone."""

    def __init__(self, fmt: str, datefmt: str, timezone: str) -> None:
        super().__init__(fmt, datefmt)
        self._tz = timezone

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=datetime.now().astimezone().tzinfo)
        return dt.strftime(datefmt or self.default_time_format)


def configure_logging(settings: Settings, crawl_date: date) -> None:
    ensure_directory(settings.logs_dir)
    log_file = settings.logs_dir / f"{crawl_date.isoformat()}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = LocalTimeFormatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
        settings.timezone,
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
