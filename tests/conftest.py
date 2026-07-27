"""Pytest fixtures shared across the foundation layer.

Located at tests/conftest.py so pytest picks it up for every test file under
tests/ without needing to be imported.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Empty output dir under pytest's tmp_path."""
    out = tmp_path / "outputs"
    out.mkdir()
    return out


@pytest.fixture(autouse=True)
def _isolate_settings_cache():
    """Clear the lru_cache on get_settings before/after each test.

    Cleared after yield as well so the next test starts from a known state
    even if the test itself patched env vars.
    """
    from config.settings import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def network_tests_enabled():
    """True only when RUN_NETWORK_TESTS=1; smoke tests skip otherwise."""
    return os.environ.get("RUN_NETWORK_TESTS") == "1"
