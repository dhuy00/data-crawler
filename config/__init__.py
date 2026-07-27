"""Package init — config helpers re-export from settings/constants."""

from .constants import DEFAULT_CATEGORIES, DEFAULT_USER_AGENT, PLATFORM_DOMAINS
from .settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
    "DEFAULT_USER_AGENT",
    "PLATFORM_DOMAINS",
    "DEFAULT_CATEGORIES",
]
