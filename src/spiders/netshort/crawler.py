from __future__ import annotations

from datetime import date, datetime
import logging
import re
from urllib.parse import urlparse

from src.core.base import BaseCrawler
from src.core.models import DramaRecord, EpisodePreview
from src.core.normalize import (
    clean_text,
    decode_escaped_string,
    infer_audience_type,
    limit_episode_previews,
    normalize_datetime,
    parse_count,
)


class NetShortCrawler(BaseCrawler):
    site_name = "netshort"
    base_url = "https://netshort.com"

    def crawl(self, crawl_date: date) -> list[DramaRecord]:
        return list(self.crawl_iter(crawl_date))

    def crawl_iter(self, crawl_date: date, max_items: int | None = None):
        """Yield records one by one for streaming writes."""
        max_items = max_items or self.settings.max_debug_items
        count = 0
        seen_records: set[tuple[str, str]] = set()
        for detail_url in self.fetch_seed_urls():
            try:
                record = self.fetch_record(detail_url, crawl_date)
            except Exception as exc:
                self.logger.warning("failed to crawl %s: %s", detail_url, exc)
                continue
            if record:
                record_key = (record.site_drama_id, record.detail_url)
                if record_key in seen_records:
                    continue
                seen_records.add(record_key)
                yield record
                count += 1
            if max_items is not None and count >= max_items:
                break

    def fetch_seed_urls(self) -> list[str]:
        """Fetch all drama detail URLs by paginating through all-plots."""
        base_url = self.settings.netshort_all_plots_url.rstrip("/")
        detail_urls: list[str] = []
        seen_urls: set[str] = set()
        page = 0
        consecutive_empty = 0
        max_empty_pages = 3  # Stop after 3 consecutive empty pages

        while consecutive_empty < max_empty_pages:
            page += 1
            url = base_url if page == 1 else f"{base_url}/page/{page}"
            response = self.http.get(url, allow_statuses={200, 404})

            if response.status_code == 404:
                consecutive_empty += 1
                continue

            # The all-plots pages include both category links (/drama/...)
            # and actual drama detail links (/episode/...). Only the latter
            # should be used as crawl seeds.
            matches = re.findall(r'href="(/episode/[^"]+)"', response.text)
            if not matches:
                consecutive_empty += 1
                continue

            consecutive_empty = 0
            for match in matches:
                absolute = self.absolute_url(match)
                if absolute not in seen_urls:
                    seen_urls.add(absolute)
                    detail_urls.append(absolute)

            if self.reached_debug_limit(len(detail_urls)):
                break

        self.logger.info("fetched %d detail URLs from %d pages", len(detail_urls), page)
        return detail_urls

    def fetch_record(self, detail_url: str, crawl_date: date) -> DramaRecord | None:
        response = self.http.get(detail_url)
        text = response.text
        source = text.replace('\\"', '"')
        response_url = str(getattr(response, "url", detail_url))
        primary_source = self._extract_primary_source(source, urlparse(response_url).path)

        site_drama_id = self._extract_first(primary_source, r'"shortPlayId":"([^"]+)"')
        title = decode_escaped_string(self._extract_first(primary_source, r'"shortPlayName":"((?:\\.|[^"])*)"'))
        summary = decode_escaped_string(self._extract_first(primary_source, r'"shotIntroduce":"((?:\\.|[^"])*)"'))
        cover_url = decode_escaped_string(self._extract_first(primary_source, r'"shortPlayCover":"((?:\\.|[^"])*)"'))
        canonical_path = decode_escaped_string(self._extract_first(primary_source, r'"fullEpisodeNameUrl":"((?:\\.|[^"])*)"'))
        canonical_detail_url = self.absolute_url(canonical_path) if canonical_path else detail_url
        collect_count = parse_count(self._extract_first(primary_source, r'"totalChaseNums":"([^"]+)"'))
        like_count = parse_count(self._extract_first(primary_source, r'"totalLikeNums":"([^"]+)"'))
        tags = self._extract_short_play_labels(primary_source)
        episodes = self._extract_episodes(primary_source, canonical_detail_url)
        publish_date = self.fetch_publish_date(canonical_detail_url, site_drama_id)

        if not site_drama_id or not title:
            return None

        audience_type = infer_audience_type(tags, [], self.settings.audience_type_map)
        return DramaRecord(
            site="NetShort",
            site_drama_id=site_drama_id,
            title=title,
            summary=clean_text(summary),
            cover_url=cover_url,
            detail_url=canonical_detail_url,
            tag_list=tags,
            category_list=[],
            audience_type=audience_type,
            publish_date_std=publish_date,
            play_count=None,
            collect_count=collect_count,
            like_count=like_count,
            episode_count=len(episodes) or None,
            episodes_preview=limit_episode_previews(episodes),
            metric_source="page",
            crawl_date=crawl_date,
            crawled_at=datetime.now().isoformat(timespec="seconds"),
        )

    def fetch_publish_date(self, detail_url: str, site_drama_id: str | None) -> str | None:
        if not site_drama_id:
            return None
        slug = detail_url.rstrip("/").split("/")[-1]
        hotseries_url = self.absolute_url(f"/hotseries/{slug}-{site_drama_id}")
        response = self.http.get(hotseries_url, allow_statuses={200, 404})
        source = response.text.replace('\\"', '"')
        direct_match = re.search(
            r"Release date(?:<!-- -->)?：(?:<!-- -->)?(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)",
            source,
        )
        if direct_match:
            return normalize_datetime(direct_match.group(1), self.settings.timezone)
        timestamp = self._extract_first(source, r'"publishTime":(\d+)')
        return normalize_datetime(timestamp, self.settings.timezone)

    def _extract_object_keys(self, text: str, *, start: str, end: str) -> list[str]:
        pattern = re.escape(start) + r"(.*?)" + re.escape(end)
        match = re.search(pattern, text, re.S)
        if not match:
            return []
        return [decode_escaped_string(item) or "" for item in re.findall(r'"((?:\\.|[^"])*)":', match.group(1))]

    def _extract_short_play_labels(self, text: str) -> list[str]:
        match = re.search(r'"shortPlayLabels":\{(.*?)\}(?:,"labelIds":\[(.*?)\])?,"shotIntroduce"', text, re.S)
        if not match:
            return []
        return [decode_escaped_string(item) or "" for item in re.findall(r'"((?:\\.|[^"])*)":', match.group(1))]

    @staticmethod
    def _extract_primary_source(text: str, request_path: str) -> str:
        marker = f'"shortPlayUrl":"{request_path}"'
        path_index = text.find(marker)
        if path_index == -1:
            return text

        start = text.rfind('"shortPlayId":"', 0, path_index)
        if start == -1:
            return text

        # Keep a bounded slice around the matched object so subsequent regexes
        # target the current drama instead of unrelated recommendation payloads.
        return text[start : path_index + 12000]

    def _extract_episodes(self, text: str, detail_url: str) -> list[EpisodePreview]:
        episodes: list[EpisodePreview] = []
        seen_episode_keys: set[tuple[str | None, int | None]] = set()
        for episode_id, episode_no, is_lock in re.findall(
            r'"episodeId":"([^"]+)".*?"episodeNo":(\d+)(?:.*?"isLock":(true|false))?',
            text,
        ):
            slug = detail_url.rstrip("/").split("/")[-1]
            episode_no_int = int(episode_no)
            episode_key = (episode_id, episode_no_int)
            if episode_key in seen_episode_keys:
                continue
            seen_episode_keys.add(episode_key)
            episodes.append(
                EpisodePreview(
                    episode_id=episode_id,
                    episode_no=episode_no_int,
                    episode_type="episode",
                    episode_url=self.absolute_url(f"/episode/{slug}-{episode_id}"),
                    is_locked={"true": True, "false": False}.get(is_lock),
                )
            )
        return episodes

    @staticmethod
    def _extract_first(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.S)
        return match.group(1) if match else None
