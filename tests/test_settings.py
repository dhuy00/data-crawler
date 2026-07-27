"""Tests for config/."""

from __future__ import annotations

from config import DEFAULT_CATEGORIES, DEFAULT_USER_AGENT, PLATFORM_DOMAINS, get_settings
from config.settings import Settings
from models import Platform


def test_constants_exposed():
    assert DEFAULT_USER_AGENT.startswith("Mozilla")
    assert Platform.TIKI in PLATFORM_DOMAINS
    assert "dien-thoai" in DEFAULT_CATEGORIES


def test_settings_default(monkeypatch):
    monkeypatch.delenv("USER_AGENT", raising=False)
    monkeypatch.delenv("REQUEST_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HEADLESS", raising=False)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    get_settings.cache_clear()

    s = get_settings()
    assert isinstance(s, Settings)
    assert s.user_agent == DEFAULT_USER_AGENT
    assert s.request_timeout == 30
    assert s.output_dir == "outputs"


def test_settings_overrides(monkeypatch):
    monkeypatch.setenv("USER_AGENT", "TestAgent/1.0")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("OUTPUT_DIR", "data_out")
    get_settings.cache_clear()

    s = get_settings()
    assert s.user_agent == "TestAgent/1.0"
    assert s.request_timeout == 5
    assert s.output_dir == "data_out"


def test_rate_limit_per_platform(monkeypatch):
    monkeypatch.setenv("DEFAULT_RATE_LIMIT_PER_SECOND", "2.0")
    monkeypatch.setenv("SHOPEE_RATE_LIMIT_PER_SECOND", "3.5")
    get_settings.cache_clear()

    s = get_settings()
    assert s.rate_limit_for(Platform.SHOPEE) == 3.5
    assert s.rate_limit_for(Platform.TIKI) == 2.0
