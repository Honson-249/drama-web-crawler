from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Iterable
from zoneinfo import ZoneInfo

from src.core.models import EpisodePreview


_COUNT_PATTERN = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([KMB])?\s*$", re.IGNORECASE)
_DATE_FROM_URL_PATTERN = re.compile(r"/(20\d{2})/(0[1-9]|1[0-2])/([0-3]\d)/")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(value.strip().split())
    return collapsed or None


def decode_escaped_string(value: str | None) -> str | None:
    if value is None:
        return None
    # Use JSON decoding to properly handle unicode escapes like \u6bd4
    # This correctly decodes Chinese and other non-ASCII characters in URLs
    try:
        # Wrap in quotes to make it a valid JSON string, then unwrap the result
        return json.loads(f'"{value}"').replace("\\/", "/")
    except (ValueError, UnicodeDecodeError):
        # Fallback to original method if JSON decoding fails
        return bytes(value, "utf-8").decode("unicode_escape").replace("\\/", "/")


def parse_count(value: object, *, zero_is_null: bool = False) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return None if zero_is_null and value == 0 else value
    if isinstance(value, float):
        integer = int(value)
        return None if zero_is_null and integer == 0 else integer

    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "na"}:
        return None
    match = _COUNT_PATTERN.match(text.replace(",", ""))
    if not match:
        return None

    number = float(match.group(1))
    suffix = (match.group(2) or "").upper()
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[suffix]
    result = int(number * multiplier)
    return None if zero_is_null and result == 0 else result


def normalize_datetime(value: object, timezone_name: str) -> str | None:
    if value is None:
        return None
    tz = ZoneInfo(timezone_name)

    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000
        dt = datetime.fromtimestamp(raw, tz=timezone.utc).astimezone(tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    text = clean_text(str(value))
    if not text:
        return None
    if text.isdigit():
        return normalize_datetime(int(text), timezone_name)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt.endswith("Z"):
            parsed = parsed.replace(tzinfo=timezone.utc).astimezone(tz)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        if fmt == "%Y/%m/%d":
            return parsed.strftime("%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(tz)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return parsed.strftime("%Y-%m-%d %H:%M:%S" if ":" in text else "%Y-%m-%d")


def extract_date_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = _DATE_FROM_URL_PATTERN.search(url)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def infer_audience_type(
    tags: Iterable[str],
    categories: Iterable[str],
    mapping: dict[str, list[str]],
) -> str:
    tokens = {
        clean_text(token).lower()
        for token in [*tags, *categories]
        if clean_text(token)
    }
    matched = {
        group
        for group, keywords in mapping.items()
        for keyword in keywords
        if any(keyword.lower() in token for token in tokens)
    }
    if not matched:
        return "unknown"
    if len(matched) > 1:
        return "mixed"
    return next(iter(matched))


def limit_episode_previews(episodes: Iterable[EpisodePreview], limit: int = 10) -> list[EpisodePreview]:
    ordered = sorted(episodes, key=lambda item: (item.episode_no is None, item.episode_no or 0))
    return list(ordered[:limit])
