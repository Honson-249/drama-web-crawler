from __future__ import annotations

from datetime import date
from pathlib import Path

from src.core.settings import Settings


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_directory(settings: Settings, site: str) -> Path:
    return ensure_directory(settings.exports_dir / site)


def export_file_path(settings: Settings, site: str, crawl_date: date, *, crawling: bool = False) -> Path:
    """Get the export file path for a site and date.

    Args:
        settings: Application settings
        site: Site name
        crawl_date: Crawl date
        crawling: If True, add .crawling suffix for in-progress files
    """
    base_path = export_directory(settings, site) / f"{site}_{crawl_date.isoformat()}.csv"
    if crawling:
        return Path(str(base_path) + ".crawling")
    return base_path


def latest_export_file(settings: Settings, site: str) -> Path | None:
    """Get the latest completed export file for a site.

    Files with .crawling suffix are excluded as they indicate incomplete writes.
    """
    directory = export_directory(settings, site)
    # Only match completed files (not .crawling)
    matches = sorted(directory.glob(f"{site}_*.csv"))
    # Filter out any .crawling files that might match
    matches = [p for p in matches if not p.name.endswith(".crawling")]
    return matches[-1] if matches else None


def export_file_for_date(settings: Settings, site: str, crawl_date: date) -> Path | None:
    """Get the export file for a specific date.

    Returns None if the file doesn't exist or is still being written (.crawling).
    """
    path = export_file_path(settings, site, crawl_date)
    return path if path.exists() else None
