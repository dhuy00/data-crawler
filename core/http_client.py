"""HTTP client + per-domain rate limiter.

`HttpClient` wraps `requests.Session`, applies timeouts, a default User-Agent,
and a per-host `RateLimiter` so multiple workers don't hammer a single domain.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

import requests

from .logger import logger


class RateLimiter:
    """Simple per-host token bucket.

    Each host gets its own bucket; tokens regenerate at the configured rate.
    A request blocks until a token is available for its host.
    """

    def __init__(self, requests_per_second: float = 1.5):
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0")
        self._interval = 1.0 / requests_per_second
        self._last_ts: dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc or "default"
        with self._lock:
            now = time.monotonic()
            last = self._last_ts[host]
            wait_for = self._interval - (now - last)
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_ts[host] = time.monotonic()


class HttpClient:
    """Thin wrapper around requests.Session.

    - Applies a default User-Agent if none provided.
    - Enforces a per-host rate limit.
    - Returns the raw `requests.Response` so callers decide how to parse.
    """

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (compatible; data-crawler/0.1)",
        timeout: int = 30,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 3,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        if not extra:
            return {}
        merged = {"User-Agent": self.user_agent}
        merged.update(extra)
        return merged

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        return self._request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        return self._request(
            "POST", url, data=data, json=json, headers=headers, timeout=timeout
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        self.rate_limiter.wait(url)
        timeout = timeout or self.timeout
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=self._headers(headers),
                    timeout=timeout,
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                wait = 1.0 * (2 ** (attempt - 1))
                logger.warning(
                    f"HTTP {method} {url} attempt {attempt}/{self.max_retries} "
                    f"failed: {exc!r}. Retry in {wait:.1f}s"
                )
                time.sleep(wait)
        assert last_exc is not None
        logger.error(f"HTTP {method} {url} failed after {self.max_retries} attempts")
        raise last_exc

    def close(self) -> None:
        self.session.close()
