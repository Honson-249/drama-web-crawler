from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file at project root
load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    data_dir: Path
    exports_dir: Path
    logs_dir: Path
    timezone: str
    http_timeout: float
    http_delay_seconds: float
    http_max_retries: int
    user_agent: str
    max_debug_items: int | None
    netshort_all_plots_url: str
    netshort_home_url: str
    dramabox_base_url: str
    reelshort_all_movies_url: str
    shortmax_dramas_url: str
    audience_type_map: dict[str, list[str]]
    # Server and scheduler settings
    server_port: int
    crawl_schedule_hour: int
    crawl_schedule_minute: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "src" / "config" / "audience_type_map.json"
    audience_type_map: dict[str, list[str]] = json.loads(config_path.read_text(encoding="utf-8"))
    data_dir = Path(os.getenv("DRAMA_DATA_DIR", project_root / "data"))
    exports_dir = Path(os.getenv("DRAMA_EXPORTS_DIR", data_dir / "exports"))
    logs_dir = Path(os.getenv("DRAMA_LOGS_DIR", project_root / "logs"))
    max_debug_items_raw = os.getenv("DRAMA_MAX_ITEMS")

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        exports_dir=exports_dir,
        logs_dir=logs_dir,
        timezone=os.getenv("DRAMA_TIMEZONE", "Asia/Shanghai"),
        http_timeout=_env_float("DRAMA_HTTP_TIMEOUT", 20.0),
        http_delay_seconds=_env_float("DRAMA_HTTP_DELAY_SECONDS", 0.0),
        http_max_retries=_env_int("DRAMA_HTTP_MAX_RETRIES", 2),
        user_agent=os.getenv(
            "DRAMA_USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            ),
        ),
        max_debug_items=int(max_debug_items_raw) if max_debug_items_raw else None,
        netshort_all_plots_url=os.getenv("NETSHORT_ALL_PLOTS_URL", "https://netshort.com/drama/all-plots"),
        netshort_home_url=os.getenv("NETSHORT_HOME_URL", "https://netshort.com/"),
        dramabox_base_url=os.getenv("DRAMABOX_BASE_URL", "https://www.dramabox.com"),
        reelshort_all_movies_url=os.getenv(
            "REELSHORT_ALL_MOVIES_URL",
            "https://www.reelshort.com/movie-genres/all-movies",
        ),
        shortmax_dramas_url=os.getenv("SHORTMAX_DRAMAS_URL", "https://www.shorttv.live/dramas"),
        audience_type_map=audience_type_map,
        # Server and scheduler settings
        server_port=_env_int("DRAMA_SERVER_PORT", 9000),
        crawl_schedule_hour=_env_int("DRAMA_CRAWL_HOUR", 0),
        crawl_schedule_minute=_env_int("DRAMA_CRAWL_MINUTE", 0),
    )
