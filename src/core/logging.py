from __future__ import annotations

from datetime import date
import logging

from src.core.settings import Settings
from src.core.storage import ensure_directory


def configure_logging(settings: Settings, crawl_date: date) -> None:
    ensure_directory(settings.logs_dir)
    log_file = settings.logs_dir / f"{crawl_date.isoformat()}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
