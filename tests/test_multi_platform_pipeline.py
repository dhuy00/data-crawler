"""Tests for the multi-platform pipeline.

Phase 5 keeps the implementation simple — sequential per-platform
dispatch. We monkey-patch `run_full_pipeline` and `run_keyword_pipeline`
to keep these tests pure (no network).
"""

from __future__ import annotations

import asyncio

import pytest

from pipelines.multi_platform_pipeline import run_multi_platform_pipeline


async def _fake_full(*args, **kwargs):  # noqa: ARG001
    platform_value = kwargs.get("platform_value") or args[0] if args else "tiki"
    return {
        "platform": platform_value,
        "product_count": 5,
        "comment_count": 12,
        "categories": 3,
        "run_id": "test",
    }


async def _fake_keyword(*args, **kwargs):
    platform_value = kwargs.get("platform_value") or (args[1] if len(args) > 1 else "tiki")
    return {
        "platform": platform_value,
        "product_count": 8,
        "comment_count": 0,
        "keywords": kwargs.get("keywords") or args[0],
        "run_id": "test",
    }


async def _failing_full(*args, **kwargs):
    raise RuntimeError("simulated network failure")


def test_multi_platform_full_runs_each_platform(tmp_path) -> None:
    from pipelines import multi_platform_pipeline as mod

    mod.run_full_pipeline = _fake_full

    async def main():
        return await run_multi_platform_pipeline(
            platforms=["tiki", "shopee", "lazada", "sendo"],
            mode="full",
            output_dir=tmp_path,
            fetch_comments=True,
            limit_products=10,
        )
    result = asyncio.run(main())

    assert result["mode"] == "full"
    assert result["platforms"] == ["tiki", "shopee", "lazada", "sendo"]
    assert result["product_count"] == 20  # 5 per platform × 4
    assert result["comment_count"] == 48  # 12 × 4
    assert set(result["per_platform"].keys()) == {"tiki", "shopee", "lazada", "sendo"}
    for plat in ("tiki", "shopee", "lazada", "sendo"):
        assert result["per_platform"][plat]["product_count"] == 5


def test_multi_platform_keyword_runs_each_platform(tmp_path) -> None:
    from pipelines import multi_platform_pipeline as mod

    mod.run_keyword_pipeline = _fake_keyword

    async def main():
        return await run_multi_platform_pipeline(
            platforms=["tiki", "shopee"],
            mode="keyword",
            output_dir=tmp_path,
            fetch_comments=False,
            keywords=["iphone", "airpods"],
            max_products_per_keyword=10,
        )
    result = asyncio.run(main())
    assert result["mode"] == "keyword"
    assert result["platforms"] == ["tiki", "shopee"]
    assert result["product_count"] == 16  # 8 × 2
    assert result["comment_count"] == 0


def test_multi_platform_records_per_platform_error(tmp_path) -> None:
    from pipelines import multi_platform_pipeline as mod

    # First call fails, second succeeds → aggregated continues.
    calls = {"n": 0}

    async def _mixed(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated failure")
        return await _fake_full(*args, **kwargs)

    mod.run_full_pipeline = _mixed

    async def main():
        return await run_multi_platform_pipeline(
            platforms=["tiki", "shopee"],
            mode="full",
            output_dir=tmp_path,
        )
    result = asyncio.run(main())
    assert "error" in result["per_platform"]["tiki"]
    assert result["per_platform"]["shopee"]["product_count"] == 5
    # Only shopee contributes
    assert result["product_count"] == 5


def test_multi_platform_rejects_empty_platform_list(tmp_path) -> None:
    async def main():
        return await run_multi_platform_pipeline(
            platforms=[], mode="full", output_dir=tmp_path
        )
    with pytest.raises(ValueError):
        asyncio.run(main())


def test_multi_platform_rejects_unsupported_mode(tmp_path) -> None:
    async def main():
        return await run_multi_platform_pipeline(
            platforms=["tiki"], mode="menu", output_dir=tmp_path
        )
    with pytest.raises(ValueError):
        asyncio.run(main())


def test_multi_platform_summary_shape(tmp_path) -> None:
    from pipelines import multi_platform_pipeline as mod

    mod.run_full_pipeline = _fake_full

    async def main():
        return await run_multi_platform_pipeline(
            platforms=["tiki"], mode="full", output_dir=tmp_path
        )
    result = asyncio.run(main())
    for key in ("run_id", "mode", "platforms", "started_at",
                "finished_at", "product_count", "comment_count", "per_platform"):
        assert key in result
    assert result["mode"] == "full"
    assert isinstance(result["platforms"], list)
