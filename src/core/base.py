from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
import logging
from urllib.parse import urljoin
from typing import Iterator

from src.core.http import HttpClient
from src.core.models import DramaRecord
from src.core.settings import Settings


class SiteCrawler(ABC):
    site_name: str

    @abstractmethod
    def crawl(self, crawl_date: date) -> list[DramaRecord]:
        raise NotImplementedError

    def crawl_iter(self, crawl_date: date) -> Iterator[DramaRecord]:
        """Yield records one by one for streaming writes."""
        for record in self.crawl(crawl_date):
            yield record


class BaseCrawler(SiteCrawler):
    base_url: str = ""

    def __init__(self, settings: Settings, http_client: HttpClient | None = None) -> None:
        self.settings = settings
        self.http = http_client or HttpClient(settings)
        self.logger = logging.getLogger(self.site_name)

    def absolute_url(self, value: str) -> str:
        return urljoin(self.base_url, value)

    def limit_records(self, records: list[DramaRecord]) -> list[DramaRecord]:
        if self.settings.max_debug_items is None:
            return records
        return records[: self.settings.max_debug_items]

    def reached_debug_limit(self, count: int) -> bool:
        return self.settings.max_debug_items is not None and count >= self.settings.max_debug_items
