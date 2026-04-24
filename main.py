from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.settings import Settings, get_settings
from src.jobs.daily_crawl import run_daily_crawl


def create_background_scheduler(settings: Settings) -> BackgroundScheduler:
    """Create a background scheduler that runs daily crawl at configured time."""
    scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.timezone))

    def scheduled_job() -> None:
        crawl_date = datetime.now(ZoneInfo(settings.timezone)).date()
        logging.info("scheduled daily crawl starting for date=%s", crawl_date)
        run_daily_crawl(crawl_date=crawl_date, selected_site="all", settings=settings)

    scheduler.add_job(
        scheduled_job,
        trigger="cron",
        hour=settings.crawl_schedule_hour,
        minute=settings.crawl_schedule_minute,
        id="daily-drama-crawl",
        replace_existing=True,
    )
    logging.info(
        "background scheduler configured for daily crawl at %02d:%02d %s",
        settings.crawl_schedule_hour,
        settings.crawl_schedule_minute,
        settings.timezone,
    )
    return scheduler


def main() -> None:
    # Configure logging first
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    # Load settings
    settings = get_settings()

    # Start background scheduler
    scheduler = create_background_scheduler(settings)
    scheduler.start()

    logging.info("starting API server with background scheduler")
    logging.info("server listening on http://0.0.0.0:%d", settings.server_port)

    # Start API server
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=settings.server_port, reload=False)


if __name__ == "__main__":
    main()
