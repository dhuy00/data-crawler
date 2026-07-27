"""Tests for core/http_client.py — covers RateLimiter only (HTTP requests are network)."""

from __future__ import annotations

import time

from core.http_client import RateLimiter


def test_rate_limiter_rejects_zero():
    import pytest
    with pytest.raises(ValueError):
        RateLimiter(requests_per_second=0)


def test_rate_limiter_waits_between_requests():
    rl = RateLimiter(requests_per_second=10)  # interval = 0.1s
    rl.wait("https://a.test/x")
    t0 = time.monotonic()
    rl.wait("https://a.test/y")
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.05  # allow slack — just verify it actually waited some


def test_rate_limiter_per_host_independent():
    rl = RateLimiter(requests_per_second=10)
    rl.wait("https://host-a.test/x")
    t0 = time.monotonic()
    rl.wait("https://host-b.test/x")  # different host, no wait
    elapsed = time.monotonic() - t0
    assert elapsed < 0.05
