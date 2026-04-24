from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import logging
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from src.core.export import write_records_to_csv, write_records_to_csv_iter
from src.core.interpolate_dates import interpolate_csv_file
from src.core.logging import configure_logging
from src.core.settings import Settings, get_settings
from src.core.storage import export_file_path
from src.spiders.registry import SITE_ORDER, build_crawlers


def crawl_single_site(
    site_name: str,
    crawler,
    crawl_date: date,
    settings: Settings,
) -> tuple[str, int | None, Exception | None]:
    """Crawl a single site and write to CSV. Returns (site_name, record_count, error)."""
    logger = logging.getLogger("daily_crawl")
    started_at = datetime.now()
    logger.info("site=%s start=%s", site_name, started_at.isoformat(timespec="seconds"))

    try:
        output_path = export_file_path(settings, site_name, crawl_date)
        # Use streaming write with crawl_iter
        record_count = write_records_to_csv_iter(crawler.crawl_iter(crawl_date), output_path)
        logger.info(
            "site=%s status=success records=%s output=%s end=%s",
            site_name,
            record_count,
            output_path,
            datetime.now().isoformat(timespec="seconds"),
        )

        # 对 NetShort 数据进行发布日期插值
        if site_name.lower() == "netshort":
            interpolated_count = interpolate_csv_file(Path(output_path))
            if interpolated_count > 0:
                logger.info(
                    "site=%s interpolated %d missing publish dates",
                    site_name,
                    interpolated_count,
                )

        return site_name, record_count, None
    except Exception as exc:
        logger.exception(
            "site=%s status=failed reason=%s end=%s",
            site_name,
            exc,
            datetime.now().isoformat(timespec="seconds"),
        )
        return site_name, None, exc


def run_daily_crawl(
    *,
    crawl_date: date,
    selected_site: str = "all",
    settings: Settings | None = None,
    parallel: bool = True,
    max_workers: int = 4,
) -> int:
    settings = settings or get_settings()
    configure_logging(settings, crawl_date)
    logger = logging.getLogger("daily_crawl")
    crawlers = build_crawlers(settings)
    site_names = SITE_ORDER if selected_site == "all" else [selected_site]
    failures = 0

    if parallel and len(site_names) > 1:
        # Parallel execution with ThreadPoolExecutor
        logger.info("running crawlers in parallel with %d workers", min(max_workers, len(site_names)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(crawl_single_site, site_name, crawlers[site_name], crawl_date, settings): site_name
                for site_name in site_names
            }
            for future in as_completed(futures):
                site_name, record_count, error = future.result()
                if error is not None:
                    failures += 1
    else:
        # Sequential execution
        logger.info("running crawlers sequentially")
        for site_name in site_names:
            _, _, error = crawl_single_site(site_name, crawlers[site_name], crawl_date, settings)
            if error is not None:
                failures += 1

    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily crawls and export csv files.")
    parser.add_argument(
        "--site",
        choices=["all", *SITE_ORDER],
        default="all",
        help="Select a single site or run all crawlers.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Override crawl date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run crawlers sequentially instead of in parallel.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers when running in parallel mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    crawl_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(ZoneInfo(settings.timezone)).date()
    )
    return run_daily_crawl(
        crawl_date=crawl_date,
        selected_site=args.site,
        settings=settings,
        parallel=not args.sequential,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
