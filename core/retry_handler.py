"""Tenacity-based retry decorators for sync and async operations.

Both decorators catch broad network/timeout exceptions and exponential-backoff
between retries. Caller can override the stop / wait / retry parameters.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logger import logger

T = TypeVar("T")

# Defaults — broad enough to cover requests + aiohttp + playwright timeouts.
DEFAULT_EXC = (Exception,)


def retry_sync(
    func: Callable[..., T] | None = None,
    *,
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[BaseException], ...] = DEFAULT_EXC,
) -> Callable[..., T]:
    """Decorate a sync callable with tenacity retry.

    Usage:
        @retry_sync
        def fetch(): ...

        @retry_sync(max_attempts=5)
        def fetch(): ...
    """
    def _wrap(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    wait = min(initial_wait * (2 ** (attempt - 1)), max_wait)
                    logger.warning(
                        f"{fn.__name__} attempt {attempt}/{max_attempts} failed: {exc!r}. "
                        f"Retry in {wait:.1f}s"
                    )
                    import time as _t
                    _t.sleep(wait)
            assert last_exc is not None
            raise last_exc
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper

    if func is not None and callable(func):
        return _wrap(func)
    return _wrap  # called with kwargs


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[BaseException], ...] = DEFAULT_EXC,
    **kwargs: Any,
) -> T:
    """Run an async callable with retry-on-exception + exponential backoff."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=initial_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    ):
        with attempt:
            try:
                return await func(*args, **kwargs)
            except exceptions as exc:
                logger.warning(
                    f"{func.__name__} attempt failed: {exc!r}"
                )
                raise
    # tenacity's AsyncRetrying with reraise=True always re-raises on failure,
    # so we never reach this branch — guard is for type-checkers.
    raise RuntimeError("retry_async reached unreachable code")  # pragma: no cover


def make_retry_async_decorator(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[BaseException], ...] = DEFAULT_EXC,
):
    """Build an async retry decorator with bound retry parameters.

    Usage:
        @make_retry_async_decorator(max_attempts=5)
        async def fetch(): ...
    """
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(
                fn,
                *args,
                max_attempts=max_attempts,
                initial_wait=initial_wait,
                max_wait=max_wait,
                exceptions=exceptions,
                **kwargs,
            )
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return decorator


# Convenience alias kept for legacy callers.
retry_async_decorator = make_retry_async_decorator
