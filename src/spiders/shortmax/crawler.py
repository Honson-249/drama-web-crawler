from __future__ import annotations

from datetime import date, datetime
import re

from bs4 import BeautifulSoup

from src.core.base import BaseCrawler
from src.core.models import DramaRecord, EpisodePreview
from src.core.normalize import (
    clean_text,
    extract_date_from_url,
    infer_audience_type,
    limit_episode_previews,
    parse_count,
)


class ShortMaxCrawler(BaseCrawler):
    site_name = "shortmax"
    base_url = "https://www.shorttv.live"

    def crawl(self, crawl_date: date) -> list[DramaRecord]:
        return list(self.crawl_iter(crawl_date))

    def crawl_iter(self, crawl_date: date, max_items: int | None = None):
        """Yield records one by one for streaming writes."""
        max_items = max_items or self.settings.max_debug_items
        count = 0
        for seed_url in self.fetch_seed_urls():
            try:
                record = self.fetch_record(seed_url, crawl_date)
            except Exception as exc:
                self.logger.warning("failed to crawl %s: %s", seed_url, exc)
                continue
            if record:
                yield record
                count += 1
            if max_items is not None and count >= max_items:
                break

    def fetch_seed_urls(self) -> list[str]:
        queue = [self.settings.shortmax_dramas_url]
        seen_pages: set[str] = set()
        seen_episode_urls: set[str] = set()
        episode_urls: list[str] = []

        while queue:
            url = queue.pop(0)
            if url in seen_pages:
                continue
            seen_pages.add(url)
            response = self.http.get(url)
            text = response.text

            for match in re.findall(r'href="(/episode/[^"]+-1)"', text):
                absolute = self.absolute_url(match)
                if absolute not in seen_episode_urls:
                    seen_episode_urls.add(absolute)
                    episode_urls.append(absolute)
                if self.reached_debug_limit(len(episode_urls)):
                    return episode_urls

            # Full crawl should only walk the all-pages listing:
            #   /dramas, /dramas/2, /dramas/3, ...
            # Category routes under /dramas/<slug>-<id> introduce duplicates.
            for match in re.findall(r'href="(/dramas(?:/\d+)?)"', text):
                absolute = self.absolute_url(match)
                if absolute not in seen_pages:
                    queue.append(absolute)

        return episode_urls

    def fetch_record(self, seed_url: str, crawl_date: date) -> DramaRecord | None:
        response = self.http.get(seed_url)
        text = response.text

        primary_payload = self._extract_primary_payload(text)
        site_drama_id = primary_payload.get("site_drama_id")
        title = primary_payload.get("title")
        summary = primary_payload.get("summary")
        cover_url = primary_payload.get("cover_url")
        collect_count = parse_count(primary_payload.get("collect_count"))
        play_count = parse_count(primary_payload.get("play_count"))
        tags = self._extract_display_names(text, "labelList")
        categories = self._extract_display_names(text, "classList")
        episodes = self._extract_episodes(text, seed_url)
        detail_url = self._detail_url_from_seed(seed_url)

        if not site_drama_id or not title:
            title, summary = self._fallback_detail_page(detail_url)

        if not site_drama_id or not title:
            return None

        publish_date = extract_date_from_url(cover_url)
        metric_source = "mixed" if publish_date else "page"
        return DramaRecord(
            site="ShortMax",
            site_drama_id=site_drama_id,
            title=self._decode(title) or title,
            summary=clean_text(self._decode(summary)),
            cover_url=self._decode(cover_url),
            detail_url=detail_url,
            tag_list=tags,
            category_list=categories,
            audience_type=infer_audience_type(tags, categories, self.settings.audience_type_map),
            publish_date_std=publish_date,
            play_count=play_count,
            collect_count=collect_count,
            like_count=None,
            episode_count=len(episodes) or None,
            episodes_preview=limit_episode_previews(episodes),
            metric_source=metric_source,
            crawl_date=crawl_date,
            crawled_at=datetime.now().isoformat(timespec="seconds"),
        )

    def _extract_display_names(self, text: str, key: str) -> list[str]:
        match = re.search(rf'"{re.escape(key)}":\[(.*?)\](?:,"|}})', text, re.S)
        if match:
            direct_names = [
                self._decode(item) or ""
                for item in re.findall(r'"displayName":"((?:\\.|[^"])*)"', match.group(1))
            ]
            if direct_names:
                return direct_names

        if key == "labelList":
            pattern = (
                r'\{"id":\d+,"labelId":\d+,"labelName":\d+,"labelType":\d+,"displayName":\d+\},'
                r'\d+,\d+,"(?:\\.|[^"]*)",\d+,"((?:\\.|[^"])*)"'
            )
        elif key == "classList":
            pattern = (
                r'\{"id":\d+,"classId":\d+,"className":\d+,"displayName":\d+\},'
                r'\d+,(?:\d+,)?(?:"(?:\\.|[^"]*)",)?"((?:\\.|[^"])*)"'
            )
        else:
            return []

        return [self._decode(item) or "" for item in re.findall(pattern, text)]

    def _extract_primary_payload(self, text: str) -> dict[str, str | None]:
        direct = {
            "site_drama_id": self._extract_first(text, r'"shortPlayId":(\d+)'),
            "title": self._extract_first(text, r'"shortPlayName":"((?:\\.|[^"])*)"'),
            "summary": self._extract_first(text, r'"summary":"((?:\\.|[^"])*)"'),
            "cover_url": self._extract_first(text, r'"coverId":"((?:\\.|[^"])*)"'),
            "collect_count": self._extract_first(text, r'"collectNum":(\d+)'),
            "play_count": self._extract_first(text, r'"playNum":(\d+)'),
        }
        if all(direct.values()):
            return direct

        schema_match = re.search(
            (
                r'"shortPlayId":\d+,"shortPlayCode":\d+,"shortPlayName":\d+,"collectNum":\d+,'
                r'"convertCollectNum":\d+,"playNum":\d+,"convertPlayNum":\d+,"summary":\d+,'
                r'"coverId":\d+,"horizontalCoverId":\d+,"lockBegin":\d+.*?},'
                r'(\d+),"((?:\\.|[^"])*)","((?:\\.|[^"])*)",(\d+),"((?:\\.|[^"])*)",'
                r'(\d+),"((?:\\.|[^"])*)","((?:\\.|[^"])*)","((?:\\.|[^"])*)"'
            ),
            text,
            re.S,
        )
        if not schema_match:
            return direct

        return {
            "site_drama_id": schema_match.group(1),
            "title": schema_match.group(3),
            "summary": schema_match.group(8),
            "cover_url": schema_match.group(9),
            "collect_count": schema_match.group(4),
            "play_count": schema_match.group(6),
        }

    def _extract_episodes(self, text: str, seed_url: str) -> list[EpisodePreview]:
        episodes: list[EpisodePreview] = []
        slug = seed_url.rstrip("/").split("/")[-1].rsplit("-", 1)[0]
        for episode_no, play_count, cover_url in re.findall(
            r'"episodeNum":(\d+),"playNum":(\d+).*?"coverId":"((?:\\.|[^"])*)"',
            text,
        ):
            episodes.append(
                EpisodePreview(
                    episode_no=int(episode_no),
                    episode_type="episode",
                    episode_url=self.absolute_url(f"/episode/{slug}-{episode_no}"),
                    play_count=parse_count(play_count, zero_is_null=True),
                )
            )
        return episodes

    def _fallback_detail_page(self, detail_url: str) -> tuple[str | None, str | None]:
        response = self.http.get(detail_url, allow_statuses={200, 404})
        if response.status_code == 404:
            return None, None
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(strip=True).replace(" Dramas Watch Online - ShortMax", "") if soup.title else None
        description = None
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            description = meta.get("content")
        return title, description

    @staticmethod
    def _detail_url_from_seed(seed_url: str) -> str:
        return seed_url.replace("/episode/", "/drama/").rsplit("-", 1)[0]

    @staticmethod
    def _extract_first(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.S)
        return match.group(1) if match else None

    @staticmethod
    def _decode(value: str | None) -> str | None:
        if value is None:
            return None
        if "\\" not in value:
            return value
        if re.search(r'\\(u[0-9a-fA-F]{4}|["\\/bfnrt])', value):
            return bytes(value, "utf-8").decode("unicode_escape").replace("\\/", "/")
        return value
