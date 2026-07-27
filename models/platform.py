"""Platform enum — the four Vietnamese e-commerce sites supported by this project."""

from __future__ import annotations

from enum import Enum


class Platform(str, Enum):
    """Identifier for each supported e-commerce platform.

    Inheriting from `str` lets instances be used directly as string values
    in CSV/JSONL output and in DB lookups.
    """

    TIKI = "tiki"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    SENDO = "sendo"

    @property
    def label(self) -> str:
        """Human-readable label used in logs and CSV headers."""
        return {
            Platform.TIKI: "Tiki",
            Platform.SHOPEE: "Shopee",
            Platform.LAZADA: "Lazada",
            Platform.SENDO: "Sendo",
        }[self]

    @property
    def comment_supported(self) -> bool:
        """Whether this platform exposes comments via a public endpoint.

        Note: if a later investigation proves Lazada or Sendo DO expose
        comments publicly, flip the bool here — no other code change needed.
        """
        return self in {Platform.TIKI, Platform.SHOPEE, Platform.SENDO}

    @classmethod
    def parse(cls, value: str | "Platform") -> "Platform":
        """Parse a string (case-insensitive) into a Platform, raising on unknown."""
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"Unknown platform: {value!r}. Expected one of: {[m.value for m in cls]}"
        )
