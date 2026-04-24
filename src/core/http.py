from __future__ import annotations

from collections.abc import Mapping
import logging
import time

import httpx

from src.core.settings import Settings


class HttpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(self.__class__.__name__)
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=settings.http_timeout,
            headers={
                "user-agent": settings.user_agent,
                "accept-language": "en-US,en;q=0.9",
            },
        )

    def close(self) -> None:
        self._client.close()

    def get(
        self,
        url: str,
        *,
        allow_statuses: set[int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        allow_statuses = allow_statuses or {200}
        last_error: Exception | None = None
        for attempt in range(1, self._settings.http_max_retries + 2):
            try:
                response = self._client.get(url, headers=headers)
                if response.status_code not in allow_statuses:
                    raise httpx.HTTPStatusError(
                        f"unexpected status code {response.status_code} for {url}",
                        request=response.request,
                        response=response,
                    )
                if self._settings.http_delay_seconds:
                    time.sleep(self._settings.http_delay_seconds)
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                self._logger.warning(
                    "request failed (%s/%s): %s",
                    attempt,
                    self._settings.http_max_retries + 1,
                    url,
                )
                if attempt > self._settings.http_max_retries:
                    break
                time.sleep(min(0.5 * attempt, 2.0))
        assert last_error is not None
        raise last_error
