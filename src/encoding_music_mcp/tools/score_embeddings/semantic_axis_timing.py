"""Opt-in cold/warm timing pipeline for real semantic-axis retrieval."""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from typing import Any

from .. import semantic_axis_retrieval
from . import clamp_extractor


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
    loggers = (clamp_extractor.LOGGER, semantic_axis_retrieval.LOGGER)
    previous_levels = [logger.level for logger in loggers]
    for logger in loggers:
        logger.addHandler(collector)
        logger.setLevel(logging.INFO)
    try:
        yield collector
    finally:
        for logger, level in zip(loggers, previous_levels, strict=True):
            logger.removeHandler(collector)
            logger.setLevel(level)


def _flatten(events: list[dict[str, Any]], total_seconds: float) -> dict[str, float]:
    flattened = {"total_search_seconds": total_seconds}
    for event in events:
        for name, value in event["timings"].items():
            flattened[name] = value
    return flattened


def measure_semantic_axis_retrieval(
    positive_prompts: list[str],
    negative_prompts: list[str],
    *,
    limit: int = 10,
    warm_runs: int = 3,
    search: Callable[..., object] = semantic_axis_retrieval.search_songs_by_semantic_axis,
) -> dict[str, Any]:
    """Measure one cold and multiple warm searches using call-time environment.

    The configured runtime must already be prepared offline. This function does
    not run setup and cannot download model assets.
    """
    if warm_runs <= 0:
        raise ValueError("warm_runs must be positive")
    clamp_extractor.close_persistent_clamp_text_encoder()
    semantic_axis_retrieval.close_semantic_axis_retrieval_resources()
    runs: list[dict[str, float]] = []
    try:
        with _collect_timings() as collector:
            for _ in range(warm_runs + 1):
                event_start = len(collector.events)
                started = time.perf_counter()
                search(positive_prompts, negative_prompts, limit=limit)
                total_seconds = time.perf_counter() - started
                runs.append(
                    _flatten(collector.events[event_start:], total_seconds)
                )
    finally:
        semantic_axis_retrieval.close_semantic_axis_retrieval_resources()
        clamp_extractor.close_persistent_clamp_text_encoder()

    warm = runs[1:]
    warm_keys = sorted(set.intersection(*(set(run) for run in warm)))
    warm_average = {
        key: statistics.fmean(run[key] for run in warm) for key in warm_keys
    }
    return {
        "cold": runs[0],
        "warm_runs": warm,
        "warm_average": warm_average,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure a real offline semantic-axis cold search and warm searches."
    )
    parser.add_argument("--positive", action="append", required=True)
    parser.add_argument("--negative", action="append", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--warm-runs", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = measure_semantic_axis_retrieval(
        args.positive,
        args.negative,
        limit=args.limit,
        warm_runs=args.warm_runs,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
