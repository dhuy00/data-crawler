"""Runtime settings loaded from environment / .env file.

Lazily instantiates a single Settings object via `get_settings()` so tests
can `monkeypatch.setenv()` and `get_settings.cache_clear()` between cases.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

# Load .env once at import time so env vars are available to everything else.
load_dotenv(override=False)

from models.platform import Platform  # noqa: E402  (after load_dotenv)
from .constants import DEFAULT_USER_AGENT  # noqa: E402


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    user_agent: str = field(default_factory=lambda: _get("USER_AGENT", DEFAULT_USER_AGENT))
    request_timeout: int = field(default_factory=lambda: int(_get("REQUEST_TIMEOUT_SECONDS", "30")))
    headless: bool = field(default_factory=lambda: _get_bool("HEADLESS", True))
    output_dir: str = field(default_factory=lambda: _get("OUTPUT_DIR", "outputs"))
    default_rate_limit: float = field(default_factory=lambda: _get_float(
        "DEFAULT_RATE_LIMIT_PER_SECOND", 1.5))
    run_id: str = field(default_factory=lambda: _get("RUN_ID", ""))

    def rate_limit_for(self, platform: Platform) -> float:
        env_name = f"{platform.value.upper()}_RATE_LIMIT_PER_SECOND"
        return _get_float(env_name, self.default_rate_limit)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings; call `.cache_clear()` to re-read env."""
    return Settings()
