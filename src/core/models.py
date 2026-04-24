from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
from typing import Any


CSV_HEADERS = [
    "site",
    "site_drama_id",
    "title",
    "summary",
    "cover_url",
    "detail_url",
    "tag_list",
    "category_list",
    "audience_type",
    "publish_date_std",
    "play_count",
    "collect_count",
    "like_count",
    "episode_count",
    "episodes_preview_json",
    "metric_source",
    "crawl_date",
    "crawled_at",
]


@dataclass(slots=True)
class EpisodePreview:
    episode_id: str | None = None
    episode_no: int | None = None
    episode_type: str | None = None
    episode_url: str | None = None
    is_locked: bool | None = None
    play_count: int | None = None
    collect_count: int | None = None
    like_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "episode_no": self.episode_no,
            "episode_type": self.episode_type,
            "episode_url": self.episode_url,
            "is_locked": self.is_locked,
            "play_count": self.play_count,
            "collect_count": self.collect_count,
            "like_count": self.like_count,
        }


@dataclass(slots=True)
class DramaRecord:
    site: str
    site_drama_id: str
    title: str
    summary: str | None
    cover_url: str | None
    detail_url: str
    tag_list: list[str] = field(default_factory=list)
    category_list: list[str] = field(default_factory=list)
    audience_type: str = "unknown"
    publish_date_std: str | None = None
    play_count: int | None = None
    collect_count: int | None = None
    like_count: int | None = None
    episode_count: int | None = None
    episodes_preview: list[EpisodePreview] = field(default_factory=list)
    metric_source: str = "page"
    crawl_date: date | None = None
    crawled_at: str | None = None

    def to_csv_row(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "site_drama_id": self.site_drama_id,
            "title": self.title,
            "summary": self.summary,
            "cover_url": self.cover_url,
            "detail_url": self.detail_url,
            "tag_list": "|".join(self.tag_list),
            "category_list": "|".join(self.category_list),
            "audience_type": self.audience_type,
            "publish_date_std": self.publish_date_std,
            "play_count": self.play_count,
            "collect_count": self.collect_count,
            "like_count": self.like_count,
            "episode_count": self.episode_count,
            "episodes_preview_json": json.dumps(
                [episode.to_dict() for episode in self.episodes_preview],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "metric_source": self.metric_source,
            "crawl_date": self.crawl_date.isoformat() if self.crawl_date else None,
            "crawled_at": self.crawled_at,
        }
