"""Project-wide logger (loguru).

Configures a single sink per run; reconfigure on app startup with
`setup_logger()` if the user wants a custom log file path or level.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _logger


def setup_logger(
    log_dir: str | Path = "logs",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "14 days",
) -> None:
    """Configure loguru sinks.

    - One sink to stderr (colorized, level INFO by default).
    - One sink to logs/<file>.log rotating by size.

    Calling this multiple times is safe — `logger.remove()` resets first.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    _logger.remove()

    _logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        backtrace=False,
        diagnose=False,
    )

    _logger.add(
        str(log_dir / "crawler.log"),
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


# Default sink — apply a sensible default so `from core.logger import logger` works.
setup_logger()

logger = _logger