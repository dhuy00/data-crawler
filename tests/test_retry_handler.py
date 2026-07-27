"""Tests for core/retry_handler.py."""

from __future__ import annotations

import asyncio

import pytest

from core.retry_handler import retry_async, retry_async_decorator, retry_sync


class TestRetrySync:
    def test_succeeds_first_try(self):
        calls = {"n": 0}

        @retry_sync(max_attempts=3)
        def fn():
            calls["n"] += 1
            return "ok"

        assert fn() == "ok"
        assert calls["n"] == 1

    def test_eventually_succeeds(self):
        calls = {"n": 0}

        @retry_sync(max_attempts=3, initial_wait=0.0, max_wait=0.0)
        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("transient")
            return "ok"

        assert fn() == "ok"
        assert calls["n"] == 3

    def test_gives_up_after_max(self):
        calls = {"n": 0}

        @retry_sync(max_attempts=2, initial_wait=0.0, max_wait=0.0,
                    exceptions=(ValueError,))
        def fn():
            calls["n"] += 1
            raise ValueError("nope")

        with pytest.raises(ValueError):
            fn()
        assert calls["n"] == 2


class TestRetryAsync:
    def test_succeeds_first_try(self):
        async def main():
            calls = {"n": 0}

            async def fn():
                calls["n"] += 1
                return "ok"

            return await retry_async(fn, max_attempts=3), calls["n"]

        result, n = asyncio.run(main())
        assert result == "ok"
        assert n == 1

    def test_eventually_succeeds(self):
        async def main():
            calls = {"n": 0}

            async def fn():
                calls["n"] += 1
                if calls["n"] < 2:
                    raise RuntimeError("transient")
                return "ok"

            return await retry_async(
                fn, max_attempts=3, initial_wait=0.0, max_wait=0.0
            ), calls["n"]

        result, n = asyncio.run(main())
        assert result == "ok"
        assert n == 2

    def test_decorator_form(self):
        @retry_async_decorator(max_attempts=2, initial_wait=0.0, max_wait=0.0)
        async def boom():
            raise RuntimeError("nope")

        async def main():
            return await boom()

        with pytest.raises(RuntimeError):
            asyncio.run(main())
