from __future__ import annotations

from src.core.base import SiteCrawler
from src.core.settings import Settings
from src.spiders.dramabox.crawler import DramaBoxCrawler
from src.spiders.netshort.crawler import NetShortCrawler
from src.spiders.reelshort.crawler import ReelShortCrawler
from src.spiders.shortmax.crawler import ShortMaxCrawler


SITE_ORDER = ["netshort", "dramabox", "reelshort", "shortmax"]


def build_crawlers(settings: Settings) -> dict[str, SiteCrawler]:
    return {
        "netshort": NetShortCrawler(settings),
        "dramabox": DramaBoxCrawler(settings),
        "reelshort": ReelShortCrawler(settings),
        "shortmax": ShortMaxCrawler(settings),
    }
