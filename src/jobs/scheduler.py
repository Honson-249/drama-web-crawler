from __future__ import annotations

from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from src.core.settings import Settings, get_settings
from src.jobs.daily_crawl import run_daily_crawl


def create_scheduler(settings: Settings | None = None) -> BlockingScheduler:
    settings = settings or get_settings()
    scheduler = BlockingScheduler(timezone=ZoneInfo(settings.timezone))

    def scheduled_job() -> None:
        crawl_date = datetime.now(ZoneInfo(settings.timezone)).date()
        run_daily_crawl(crawl_date=crawl_date, selected_site="all", settings=settings)

    scheduler.add_job(
        scheduled_job,
        trigger="cron",
        hour=0,
        minute=0,
        id="daily-drama-crawl",
        replace_existing=True,
    )
    return scheduler


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    scheduler = create_scheduler(settings)
    scheduler.start()


if __name__ == "__main__":
    main()
