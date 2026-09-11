"""Tests for the opt-in real semantic-axis timing pipeline."""

from __future__ import annotations

import json
import os

import pytest

from encoding_music_mcp.tools.score_embeddings import clamp_extractor
from encoding_music_mcp.tools.score_embeddings.semantic_axis_timing import (
    measure_semantic_axis_retrieval,
)
from encoding_music_mcp.tools import semantic_axis_retrieval


POSITIVE = [
    "Music expressing a joyful and optimistic mood.",
    "Happy energetic music with a cheerful character.",
    "Happy calm music with a warm contented character.",
]
NEGATIVE = [
    "Music expressing a sorrowful and pessimistic mood.",
    "Sad energetic music with a distressed character.",
    "Sad calm music with a melancholic subdued character.",
]


def test_timing_pipeline_separates_cold_startup_from_warm_searches(monkeypatch):
    calls = 0
    closed = []
    monkeypatch.setattr(
        clamp_extractor,
        "close_persistent_clamp_text_encoder",
        lambda: closed.append("worker"),
    )
    monkeypatch.setattr(
        semantic_axis_retrieval,
        "close_semantic_axis_retrieval_resources",
        lambda: closed.append("repository"),
    )

    def search(positive, negative, *, limit):
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
        semantic_axis_retrieval.LOGGER.info(
            "search",
            extra={
                "timing_category": "semantic_axis_search",
                "timings": {
                    "text_encoding_seconds": 0.3,
                    "axis_construction_seconds": 0.01,
                    "sqlite_vec_retrieval_seconds": 0.02,
                    "result_projection_seconds": 0.001,
                },
            },
        )

    result = measure_semantic_axis_retrieval(
        POSITIVE,
        NEGATIVE,
        warm_runs=2,
        search=search,
    )

    assert calls == 3
    assert result["cold"]["interpreter_startup_seconds"] == 1.0
    assert "interpreter_startup_seconds" not in result["warm_runs"][0]
    assert result["warm_average"]["model_inference_seconds"] == 0.2
    assert result["warm_average"]["sqlite_vec_retrieval_seconds"] == 0.02
    assert closed == ["worker", "repository", "repository", "worker"]


@pytest.mark.skipif(
    os.environ.get("ENCODING_MUSIC_RUN_REAL_TIMING") != "1",
    reason="set ENCODING_MUSIC_RUN_REAL_TIMING=1 with offline runtime variables",
)
def test_real_semantic_axis_cold_and_warm_timings():
    result = measure_semantic_axis_retrieval(POSITIVE, NEGATIVE, warm_runs=2)

    print(json.dumps(result, indent=2, sort_keys=True))
    assert result["cold"]["interpreter_startup_seconds"] > 0
    assert result["cold"]["checkpoint_load_seconds"] > 0
    assert len(result["warm_runs"]) == 2
    assert all("model_inference_seconds" in run for run in result["warm_runs"])
