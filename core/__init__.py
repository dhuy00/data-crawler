"""Core utilities — logger, retry, http, browser, storage.

All crawlers and pipelines build on these. Keep this layer dependency-free
of `crawlers/`, `pipelines/`, `services/` so it can be tested in isolation.
"""

from .browser import BrowserManager
from .http_client import HttpClient, RateLimiter
from .logger import logger, setup_logger
from .retry_handler import retry_async, retry_sync
from .storage import Storage

__all__ = [
    "logger",
    "setup_logger",
    "retry_sync",
    "retry_async",
    "HttpClient",
    "RateLimiter",
    "BrowserManager",
    "Storage",
]