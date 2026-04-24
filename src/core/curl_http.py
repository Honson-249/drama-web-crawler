from __future__ import annotations

import logging
import subprocess

from src.core.settings import Settings


class CurlHttpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(self.__class__.__name__)

    def get(self, url: str) -> str:
        command = [
            "curl.exe",
            "-L",
            "--connect-timeout",
            str(int(self._settings.http_timeout)),
            "--max-time",
            str(int(self._settings.http_timeout) * 2),
            "-A",
            self._settings.user_agent,
            "-H",
            "Accept-Language: en-US,en;q=0.9",
            url,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            self._logger.warning("curl request failed for %s: %s", url, result.stderr.strip())
            raise RuntimeError(f"curl failed for {url}: {result.stderr.strip()}")
        return result.stdout
