from __future__ import annotations

from datetime import date, datetime
import json
import re

from bs4 import BeautifulSoup

from src.core.base import BaseCrawler
from src.core.curl_http import CurlHttpClient
from src.core.models import DramaRecord
from src.core.normalize import clean_text, infer_audience_type, normalize_datetime, parse_count


class DramaBoxCrawler(BaseCrawler):
    site_name = "dramabox"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.base_url = settings.dramabox_base_url
        self.curl_http = CurlHttpClient(settings)

    def crawl(self, crawl_date: date) -> list[DramaRecord]:
        return list(self.crawl_iter(crawl_date))

    def crawl_iter(self, crawl_date: date, max_items: int | None = None):
        """Yield records one by one for streaming writes."""
        max_items = max_items or self.settings.max_debug_items
        count = 0
        detail_urls = self.fetch_seed_urls()
        for detail_url in detail_urls:
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
        seen_details: set[str] = set()
        detail_urls: list[str] = []

        # 获取所有 tag 列表
        tag_ids = self.fetch_all_tag_ids()
        self.logger.info("fetched %d tag IDs", len(tag_ids))

        # 遍历每个 tag 的所有分页
        for tag_idx, tag_id in enumerate(tag_ids, 1):
            self.logger.info("[%d/%d] crawling tag_id=%s", tag_idx, len(tag_ids), tag_id)
            page = 1
            total_pages: int | None = None

            while total_pages is None or page <= total_pages:
                url = f"{self.base_url}/browse/{tag_id}" if page == 1 else f"{self.base_url}/browse/{tag_id}/{page}"
                self.logger.info("  fetching page %d...", page)
                text = self.curl_http.get(url)
                next_data = self._extract_next_data(text)
                page_props = next_data.get("props", {}).get("pageProps", {})
                if total_pages is None:
                    total_pages = int(page_props.get("pages") or 1)
                    self.logger.info("  total pages: %d", total_pages)

                for match in re.findall(r'href="(/drama/\d+/[^"]+)"', text):
                    absolute = self.absolute_url(match)
                    if absolute not in seen_details:
                        seen_details.add(absolute)
                        detail_urls.append(absolute)
                    if self.reached_debug_limit(len(detail_urls)):
                        self.logger.info("reached debug limit, returning %d URLs", len(detail_urls))
                        return detail_urls

                page += 1

        self.logger.info("finished crawling, total %d URLs", len(detail_urls))
        return detail_urls

    def fetch_all_tag_ids(self) -> list[str]:
        """获取所有 tag ID 列表"""
        url = f"{self.base_url}/browse/0"
        text = self.curl_http.get(url)
        next_data = self._extract_next_data(text)
        page_props = next_data.get("props", {}).get("pageProps", {})

        # 从 pageProps 中获取 tags 或 categories 信息
        tags = page_props.get("tags", []) or page_props.get("categories", [])

        if tags:
            # 提取 tag ID，排除 "0"（all）标签，去重
            seen_ids: set[str] = set()
            unique_tag_ids: list[str] = []
            for tag in tags:
                tag_id = str(tag.get("id") or tag.get("tagId"))
                if tag_id != "0" and tag_id not in seen_ids:
                    seen_ids.add(tag_id)
                    unique_tag_ids.append(tag_id)
            return unique_tag_ids

        # 如果没有 tags 数据，尝试从 HTML 中解析所有 tag 链接
        tag_ids = []
        for match in re.findall(r'href="/browse/(\d+)"', text):
            if match != "0" and match not in tag_ids:
                tag_ids.append(match)
        return tag_ids if tag_ids else ["0"]  # 如果没有找到 tag，默认只爬 all

    def fetch_record(self, detail_url: str, crawl_date: date) -> DramaRecord | None:
        text = self.curl_http.get(detail_url)
        soup = BeautifulSoup(text, "html.parser")
        next_data = self._extract_next_data(text)
        book_info = next_data.get("props", {}).get("pageProps", {}).get("bookInfo", {})

        site_drama_id = self._extract_first(detail_url, r"/drama/(\d+)/")
        page_title = soup.title.get_text(strip=True).replace(" Drama Watch Online | DramaBox", "") if soup.title else None
        title = (
            book_info.get("bookName")
            or book_info.get("bookNameEn")
            or self._extract_meta(soup, "og:title")
            or page_title
        )
        summary = (
            book_info.get("introduction")
            or self._extract_json(text, "bookIntroduce")
            or self._extract_meta(soup, "description")
        )
        cover_url = self._extract_meta(soup, "og:image") or book_info.get("cover")
        tags = [clean_text(item) for item in book_info.get("typeTwoNames", []) if clean_text(item)]
        publish_date = normalize_datetime(
            book_info.get("firstShelfTime") or self._extract_json(text, "publish_date_std"),
            self.settings.timezone,
        )
        play_count = parse_count(book_info.get("viewCount"))
        collect_count = parse_count(book_info.get("followCount"))

        if not site_drama_id or not title:
            return None

        return DramaRecord(
            site="DramaBox",
            site_drama_id=site_drama_id,
            title=clean_text(title) or title,
            summary=clean_text(summary),
            cover_url=cover_url,
            detail_url=detail_url,
            tag_list=tags,
            category_list=[],
            audience_type=infer_audience_type(tags, [], self.settings.audience_type_map),
            publish_date_std=publish_date,
            play_count=play_count,
            collect_count=collect_count,
            like_count=None,
            episode_count=None,
            episodes_preview=[],
            metric_source="page",
            crawl_date=crawl_date,
            crawled_at=datetime.now().isoformat(timespec="seconds"),
        )

    @staticmethod
    def _extract_meta(soup: BeautifulSoup, name: str) -> str | None:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return tag.get("content") if tag else None

    @staticmethod
    def _extract_json(text: str, key: str) -> str | None:
        match = re.search(rf'"{re.escape(key)}":"((?:\\.|[^"])*)"', text)
        if match:
            return bytes(match.group(1), "utf-8").decode("unicode_escape").replace("\\/", "/")
        number_match = re.search(rf'"{re.escape(key)}":([0-9,]+)', text)
        return number_match.group(1) if number_match else None

    @staticmethod
    def _extract_array(text: str, key: str) -> list[str]:
        match = re.search(rf'"{re.escape(key)}":\[(.*?)\]', text, re.S)
        if not match:
            return []
        return [
            bytes(item, "utf-8").decode("unicode_escape").replace("\\/", "/")
            for item in re.findall(r'"((?:\\.|[^"])*)"', match.group(1))
        ]

    @staticmethod
    def _extract_first(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_next_data(text: str) -> dict:
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text, re.S)
        if not match:
            return {}
        return json.loads(match.group(1))
