"""Registry mapping `Platform` enum to its concrete crawler class.

Pipelines look up a crawler via `registry.get(platform)` without knowing
which module implemented it. New platforms are added with `register(...)`.
"""

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING, Callable

from models.platform import Platform

if TYPE_CHECKING:
    from crawlers.base import BaseCrawler

# Importing the crawlers package triggers each per-platform module's
# `@register(...)` decorator, populating the registry singleton. This is a
# no-op if no crawler module is present (e.g. during unit tests that
# register fakes explicitly).
try:
    import crawlers  # noqa: F401
except ImportError:
    pass


class PlatformRegistry:
    """Thread-safe registry mapping `Platform` -> `BaseCrawler` subclass."""

    def __init__(self) -> None:
        self._creators: dict[Platform, Callable[[], "BaseCrawler"]] = {}
        self._lock = RLock()

    def register(
        self,
        platform: Platform,
        factory: Callable[[], "BaseCrawler"],
    ) -> None:
        with self._lock:
            self._creators[platform] = factory

    def get(self, platform: Platform) -> "BaseCrawler":
        try:
            creator = self._creators[platform]
        except KeyError as exc:
            raise LookupError(
                f"No crawler registered for platform {platform.value!r}. "
                f"Known: {[p.value for p in self._creators]}"
            ) from exc
        return creator()

    def available(self) -> list[Platform]:
        with self._lock:
            return list(self._creators.keys())

    def __contains__(self, platform: object) -> bool:
        return isinstance(platform, Platform) and platform in self._creators


_registry = PlatformRegistry()


def get_registry() -> PlatformRegistry:
    """Return the process-wide registry singleton."""
    return _registry


def register(platform: Platform):
    """Decorator: `@register(Platform.X)` on a `BaseCrawler` subclass."""

    def _wrap(cls: type["BaseCrawler"]) -> type["BaseCrawler"]:
        _registry.register(platform, cls)
        return cls

    return _wrap