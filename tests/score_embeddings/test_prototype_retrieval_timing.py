"""FastMCP Client cold/warm timing tests for prototype retrieval."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any

import pytest
from fastmcp import Client

from encoding_music_mcp.tools.score_embeddings import clamp_extractor
from encoding_music_mcp.server import mcp
from encoding_music_mcp.tools import prototype_retrieval


CONCEPT = "jazz"
PROMPTS = [
    "Jazz music with improvisatory melodic gestures.",
    "A performance shaped by jazz phrasing and harmony.",
    "Music expressing a recognizably jazz stylistic character.",
]
RETRIEVAL_DEADLINE_SECONDS = 90.0


@pytest.fixture(autouse=True)
def run_fastmcp_sync_tools_inline(monkeypatch: pytest.MonkeyPatch):
    """Keep the in-process FastMCP boundary deterministic in sandboxed tests."""
    from fastmcp.tools import function_tool

    async def call_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(function_tool, "call_sync_fn_in_threadpool", call_inline)


class _TimingCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.events: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        category = getattr(record, "timing_category", None)
        timings = getattr(record, "timings", None)
        if isinstance(category, str) and isinstance(timings, dict):
            self.events.append(
                {
                    "category": category,
                    "timings": {
                        str(name): float(value) for name, value in timings.items()
                    },
                }
            )


@contextmanager
def _collect_timings():
    collector = _TimingCollector()
    loggers = (clamp_extractor.LOGGER, prototype_retrieval.LOGGER)
    previous = [logger.level for logger in loggers]
    for logger in loggers:
        logger.addHandler(collector)
        logger.setLevel(logging.INFO)
    try:
        yield collector
    finally:
        for logger, level in zip(loggers, previous, strict=True):
            logger.removeHandler(collector)
            logger.setLevel(level)


def _flatten(events: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "end_to_end_retrieval_seconds": duration,
        "events": [event["category"] for event in events],
    }
    for event in events:
        result.update(event["timings"])
    return result


async def _measure_client_runs(warm_runs: int) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    with _collect_timings() as collector:
        async with Client(mcp) as client:
            for _ in range(warm_runs + 1):
                event_start = len(collector.events)
                started = time.perf_counter()
                await client.call_tool(
                    "search_songs_by_prototype",
                    {"concept": CONCEPT, "prompts": PROMPTS, "top_k": 3},
                )
                duration = time.perf_counter() - started
                assert duration < RETRIEVAL_DEADLINE_SECONDS, (
                    "prototype retrieval exceeded the strict 90-second deadline: "
                    f"{duration:.6f}s"
                )
                runs.append(_flatten(collector.events[event_start:], duration))
    return {
        "deadline_seconds": RETRIEVAL_DEADLINE_SECONDS,
        "cold": runs[0],
        "warm_runs": runs[1:],
    }


def _close_resources() -> None:
    prototype_retrieval.close_prototype_retrieval_resources()
    clamp_extractor.close_persistent_clamp_text_encoder()


def test_fastmcp_timing_separates_fake_cold_and_warm_runs(monkeypatch):
    calls = 0

    def fake_run(concept, prompts, *, config, top_k):
        nonlocal calls
        calls += 1
        if calls == 1:
            clamp_extractor.LOGGER.info(
                "startup",
                extra={
                    "timing_category": "clamp_worker_startup",
                    "timings": {
                        "interpreter_startup_seconds": 1.0,
                        "model_and_tokenizer_load_seconds": 2.0,
                        "checkpoint_load_seconds": 3.0,
                        "warmup_seconds": 4.0,
                    },
                },
            )
        clamp_extractor.LOGGER.info(
            "encoding",
            extra={
                "timing_category": "clamp_text_encoding",
                "timings": {
                    "tokenisation_seconds": 0.1,
                    "model_inference_seconds": 0.2,
                },
            },
        )
        prototype_retrieval.LOGGER.info(
            "search",
            extra={
                "timing_category": "prototype_search",
                "timings": {
                    "text_encoding_seconds": 0.3,
                    "prototype_construction_seconds": 0.01,
                    "sqlite_vec_retrieval_seconds": 0.02,
                    "result_projection_seconds": 0.001,
                },
            },
        )
        return prototype_retrieval.PrototypeSearchResult(
            concept=concept,
            prompts=tuple(prompts),
            model=prototype_retrieval.PrototypeModelProvenance(
                "c" * 40, "revision", "d" * 64, 768
            ),
            eligible_count=0,
            excluded_count=0,
            results=(),
        )

    monkeypatch.setattr(
        prototype_retrieval, "config_from_environment", lambda: object()
    )
    monkeypatch.setattr(prototype_retrieval, "run_prototype_search", fake_run)
    _close_resources()
    try:
        report = asyncio.run(_measure_client_runs(warm_runs=2))
    finally:
        _close_resources()

    print(json.dumps(report, indent=2, sort_keys=True))
    assert calls == 3
    assert report["cold"]["interpreter_startup_seconds"] == 1.0
    assert "interpreter_startup_seconds" not in report["warm_runs"][0]
    assert all(
        run["end_to_end_retrieval_seconds"] < RETRIEVAL_DEADLINE_SECONDS
        for run in [report["cold"], *report["warm_runs"]]
    )


@pytest.mark.skipif(
    os.environ.get("ENCODING_MUSIC_RUN_REAL_TIMING") != "1",
    reason="set ENCODING_MUSIC_RUN_REAL_TIMING=1 with offline runtime variables",
)
def test_real_fastmcp_prototype_cold_and_warm_timings():
    _close_resources()
    try:
        report = asyncio.run(_measure_client_runs(warm_runs=2))
    finally:
        _close_resources()

    print(json.dumps(report, indent=2, sort_keys=True))
    assert report["cold"]["interpreter_startup_seconds"] > 0
    assert report["cold"]["checkpoint_load_seconds"] > 0
    assert len(report["warm_runs"]) == 2
    assert all("model_inference_seconds" in run for run in report["warm_runs"])
    assert all(
        run["end_to_end_retrieval_seconds"] < RETRIEVAL_DEADLINE_SECONDS
        for run in [report["cold"], *report["warm_runs"]]
    )
