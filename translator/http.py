from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = "translator/0.1"

Fetcher = Callable[[str], str]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FetchError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def fetch_text(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        raise FetchError(f"Failed to fetch {url}") from exc
