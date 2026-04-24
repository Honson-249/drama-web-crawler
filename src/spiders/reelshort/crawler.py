from __future__ import annotations

from datetime import date, datetime
import json
import re

from src.core.base import BaseCrawler
from src.core.models import DramaRecord, EpisodePreview
from src.core.normalize import clean_text, infer_audience_type, limit_episode_previews, normalize_datetime, parse_count


class ReelShortCrawler(BaseCrawler):
    site_name = "reelshort"
    base_url = "https://www.reelshort.com"

    def crawl(self, crawl_date: date) -> list[DramaRecord]:
        return list(self.crawl_iter(crawl_date))

    def crawl_iter(self, crawl_date: date, max_items: int | None = None):
        """Yield records one by one for streaming writes."""
        max_items = max_items or self.settings.max_debug_items
        count = 0
        for detail_url in self.fetch_seed_urls():
            try:
                record = self.fetch_record(detail_url, crawl_date)
            except Exception as exc:
                self.logger.warning("failed to crawl %s: %s", detail_url, exc)
                continue
            if record:
                yield record
                count += 1
            if max_items is not None and count >= max_items:
                break

    def fetch_seed_urls(self) -> list[str]:
        current_url = self.settings.reelshort_all_movies_url
        detail_urls: list[str] = []
        seen_urls: set[str] = set()

        while current_url:
            response = self.http.get(current_url)

            for match in re.findall(r'href="(/movie/[^"]+)"', response.text):
                absolute = self.absolute_url(match)
                if absolute not in seen_urls:
                    seen_urls.add(absolute)
                    detail_urls.append(absolute)
                if self.reached_debug_limit(len(detail_urls)):
                    return detail_urls

            next_match = re.search(r'<link rel="next" href="([^"]+)"', response.text)
            current_url = next_match.group(1) if next_match else ""

        return detail_urls

    def fetch_record(self, detail_url: str, crawl_date: date) -> DramaRecord | None:
        response = self.http.get(detail_url)
        payload = self.extract_next_data(response.text)
        data = payload["props"]["pageProps"]["data"]

        site_drama_id = str(data["book_id"])
        title = clean_text(data.get("book_title"))
        tags = self._normalize_terms(data.get("tag_list")) or self._normalize_terms(data.get("tag"))
        categories = self._normalize_terms(data.get("tag"))
        slug = detail_url.rstrip("/").split("/")[-1].rsplit("-", 1)[0]
        episodes = self.build_episodes(data.get("online_base", []), slug, site_drama_id)

        if not title:
            return None

        return DramaRecord(
            site="ReelShort",
            site_drama_id=site_drama_id,
            title=title,
            summary=clean_text(data.get("special_desc")),
            cover_url=data.get("book_pic"),
            detail_url=detail_url,
            tag_list=tags,
            category_list=categories,
            audience_type=infer_audience_type(tags, categories, self.settings.audience_type_map),
            publish_date_std=normalize_datetime(data.get("publish_at") or data.get("online_at"), self.settings.timezone),
            play_count=parse_count(data.get("read_count")),
            collect_count=parse_count(data.get("collect_count")),
            like_count=None,
            episode_count=len(data.get("online_base", [])) or None,
            episodes_preview=limit_episode_previews(episodes),
            metric_source="page",
            crawl_date=crawl_date,
            crawled_at=datetime.now().isoformat(timespec="seconds"),
        )

    def build_episodes(self, items: list[dict], slug: str, site_drama_id: str) -> list[EpisodePreview]:
        episodes: list[EpisodePreview] = []
        for item in items:
            chapter_id = item.get("chapter_id")
            if not chapter_id:
                continue
            episode_type = "episode" if item.get("chapter_type") == 1 else "trailer"
            episodes.append(
                EpisodePreview(
                    episode_id=str(chapter_id),
                    episode_no=item.get("serial_number"),
                    episode_type=episode_type,
                    episode_url=self.absolute_url(f"/episodes/{episode_type}-{slug}-{site_drama_id}-{chapter_id}"),
                    like_count=parse_count(item.get("like_count")),
                )
            )
        return episodes

    @staticmethod
    def extract_next_data(text: str) -> dict:
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text, re.S)
        if not match:
            raise ValueError("missing __NEXT_DATA__ payload")
        return json.loads(match.group(1))

    @staticmethod
    def _normalize_terms(raw_value: object) -> list[str]:
        if raw_value is None:
            return []
        if isinstance(raw_value, str):
            value = clean_text(raw_value)
            return [value] if value else []
        if isinstance(raw_value, list):
            normalized: list[str] = []
            for item in raw_value:
                if isinstance(item, str):
                    value = clean_text(item)
                elif isinstance(item, dict):
                    value = clean_text(
                        item.get("text") or item.get("name") or item.get("label") or item.get("value")
                    )
                else:
                    value = clean_text(str(item))
                if value:
                    normalized.append(value)
            return normalized
        if isinstance(raw_value, dict):
            value = clean_text(
                raw_value.get("text") or raw_value.get("name") or raw_value.get("label") or raw_value.get("value")
            )
            return [value] if value else []
        value = clean_text(str(raw_value))
        return [value] if value else []
