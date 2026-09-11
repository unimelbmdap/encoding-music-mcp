"""Unit tests for dynamic single-concept prototype retrieval."""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
from fastmcp import Client

from encoding_music_mcp.tools.score_embeddings import (
    CatalogSimilarityResult,
    ClampModelIdentity,
    ClampRuntimeConfig,
    CountedCatalogSimilarityResult,
    TextEmbeddingBatch,
)
from encoding_music_mcp.server import mcp
from encoding_music_mcp.tools import prototype_retrieval as retrieval


PROMPTS = [
    "Jazz music with improvisatory melodic gestures.",
    "A performance shaped by jazz phrasing and harmony.",
    "Music expressing a recognizably jazz stylistic character.",
]


def _config(tmp_path: Path, dimension: int = 3) -> retrieval.PrototypeSearchConfig:
    return retrieval.PrototypeSearchConfig(
        database_path=tmp_path / "catalog.sqlite3",
        clamp=ClampRuntimeConfig(
            python_executable=Path(sys.executable),
            cache_dir=tmp_path / "cache",
            commit="c" * 40,
            model_revision="revision-a",
            weight_sha256="d" * 64,
            expected_dimension=dimension,
        ),
    )


def _identity(dimension: int = 3) -> ClampModelIdentity:
    return ClampModelIdentity("c" * 40, "revision-a", "d" * 64, dimension)


def _batch(raw: object, texts: tuple[str, ...] = tuple(PROMPTS)) -> TextEmbeddingBatch:
    array = np.asarray(raw)
    return TextEmbeddingBatch(
        texts=texts,
        stems=tuple(f"text_{index:06d}" for index in range(len(array))),
        raw=array,
        normalized=np.zeros_like(array, dtype=float),
        model_identity=_identity(array.shape[1]),
    )


class _FakeRepository:
    def __init__(self, path: Path, captured: dict[str, object]):
        captured["path"] = path
        self.captured = captured

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def counted_catalog_similarity_search(self, query, *, limit, model_identity):
        self.captured["query"] = query.copy()
        self.captured["limit"] = limit
        self.captured["identity"] = model_identity
        return CountedCatalogSimilarityResult(
            matches=(
                CatalogSimilarityResult(
                    embedding_id=7,
                    score_id="score-seven",
                    title="Seventh Song",
                    artist="Composer",
                    work_created_date="1907",
                    distance=0.25,
                ),
            ),
            eligible_count=12,
            excluded_count=3,
        )


def _run(
    tmp_path: Path,
    raw: object,
    *,
    prompts: list[str] | None = None,
    captured: dict[str, object] | None = None,
):
    actual_prompts = prompts or PROMPTS
    values = captured if captured is not None else {}
    return retrieval.run_prototype_search(
        "jazz",
        actual_prompts,
        config=_config(tmp_path, np.asarray(raw).shape[1]),
        embed_texts=lambda *args, **kwargs: _batch(raw, texts=tuple(actual_prompts)),
        repository_factory=lambda path: _FakeRepository(path, values),
    )


@pytest.mark.parametrize(
    ("concept", "prompts", "top_k", "message"),
    [
        (" ", PROMPTS, 10, "concept must be a non-blank"),
        (4, PROMPTS, 10, "concept must be a non-blank"),
        ("jazz", tuple(PROMPTS), 10, "prompts must be a list"),
        ("jazz", PROMPTS[:2], 10, "between 3 and 5"),
        ("jazz", PROMPTS + PROMPTS, 10, "between 3 and 5"),
        ("jazz", [PROMPTS[0], " ", PROMPTS[2]], 10, "non-blank"),
        ("jazz", [PROMPTS[0], 2, PROMPTS[2]], 10, "non-blank"),
        ("jazz", PROMPTS, True, "top_k must be an integer"),
        ("jazz", PROMPTS, 0, "between 1 and 100000"),
        ("jazz", PROMPTS, 100001, "between 1 and 100000"),
    ],
)
def test_invalid_requests_do_not_invoke_clamp(
    tmp_path, concept, prompts, top_k, message
):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid input must not invoke CLaMP")

    with pytest.raises(ValueError, match=message):
        retrieval.run_prototype_search(
            concept,
            prompts,
            config=_config(tmp_path),
            top_k=top_k,
            embed_texts=unexpected,
        )


@pytest.mark.parametrize("count", [3, 4, 5])
def test_valid_prompt_counts_use_one_ordered_batch(tmp_path: Path, count: int):
    prompts = [f"description {index}" for index in range(count)]
    captured: dict[str, object] = {"calls": 0}

    def embed(texts, config, **kwargs):
        captured["calls"] = int(captured["calls"]) + 1
        captured["texts"] = tuple(texts)
        return _batch(np.tile([1.0, 0.0, 0.0], (count, 1)), tuple(texts))

    retrieval.run_prototype_search(
        "concept",
        prompts,
        config=_config(tmp_path),
        embed_texts=embed,
        repository_factory=lambda path: _FakeRepository(path, captured),
    )
    assert captured["calls"] == 1
    assert captured["texts"] == tuple(prompts)


def test_independent_normalization_and_mean_cosine_score_are_preserved(tmp_path):
    raw = np.array([[100.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    captured: dict[str, object] = {}
    result = _run(tmp_path, raw, captured=captured)
    centroid = np.array([1.0, 2.0, 0.0]) / 3.0
    norm = np.linalg.norm(centroid)

    assert np.allclose(captured["query"], centroid / norm)
    assert result.results[0].score == pytest.approx(norm * 0.75)
    explicit_mean = np.mean(
        [
            np.dot(np.array([1.0, 0.0, 0.0]), vector / np.linalg.norm(vector))
            for vector in raw
        ]
    )
    expected_distance = 1.0 - explicit_mean / norm
    assert norm * (1.0 - expected_distance) == pytest.approx(explicit_mean)


def test_title_first_vector_free_payload_and_counts(tmp_path):
    result = _run(tmp_path, np.tile([1.0, 0.0, 0.0], (3, 1))).to_dict()

    assert result["concept"] == "jazz"
    assert result["prompts"] == PROMPTS
    assert result["eligible_count"] == 12
    assert result["excluded_count"] == 3
    assert list(result["results"][0]) == [
        "rank",
        "song_title",
        "score_id",
        "embedding_id",
        "artist",
        "work_created_date",
        "score",
    ]
    assert result["results"][0]["song_title"] == "Seventh Song"
    assert "vector" not in str(result).lower()


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (np.array([[0.0, 0.0, 0.0]] * 3), "zero or non-finite prompt"),
        (np.array([[np.inf, 0.0, 0.0]] * 3), "finite real numeric"),
        (
            np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]] * 2),
            "zero or near-zero",
        ),
    ],
)
def test_invalid_or_degenerate_embeddings_are_rejected(tmp_path, raw, message):
    prompts = [f"prompt {index}" for index in range(len(raw))]
    with pytest.raises(retrieval.PrototypeRetrievalError, match=message):
        _run(tmp_path, raw, prompts=prompts)


def test_unexpected_order_shape_and_identity_are_rejected(tmp_path):
    wrong_order = _batch(np.ones((3, 3)), tuple(reversed(PROMPTS)))
    with pytest.raises(retrieval.PrototypeRetrievalError, match="unexpected order"):
        retrieval.run_prototype_search(
            "jazz",
            PROMPTS,
            config=_config(tmp_path),
            embed_texts=lambda *args, **kwargs: wrong_order,
        )

    wrong_identity = TextEmbeddingBatch(
        texts=tuple(PROMPTS),
        stems=("a", "b", "c"),
        raw=np.ones((3, 3)),
        normalized=np.ones((3, 3)),
        model_identity=ClampModelIdentity("wrong", "revision-a", "d" * 64, 3),
    )
    with pytest.raises(retrieval.PrototypeRetrievalError, match="model identity"):
        retrieval.run_prototype_search(
            "jazz",
            PROMPTS,
            config=_config(tmp_path),
            embed_texts=lambda *args, **kwargs: wrong_identity,
        )


def test_pool_reuses_and_closes_repository(tmp_path, monkeypatch):
    created = []

    class Repository:
        def __init__(self, path, *, check_same_thread):
            self.open_calls = 0
            self.closed = False
            created.append(self)

        def open(self):
            self.open_calls += 1

        def counted_catalog_similarity_search(self, *args, **kwargs):
            return CountedCatalogSimilarityResult((), 0, 0)

        def close(self):
            self.closed = True

    monkeypatch.setattr(retrieval, "EmbeddingRepository", Repository)
    pool = retrieval._RepositoryPool()
    for _ in range(2):
        pool.catalog_search(
            tmp_path / "catalog.sqlite3",
            np.array([1.0, 0.0, 0.0]),
            limit=2,
            model_identity=_identity(),
        )
    pool.close()
    assert len(created) == 1
    assert created[0].open_calls == 1
    assert created[0].closed


def test_registered_tool_contract_is_exact():
    assert list(inspect.signature(retrieval.search_songs_by_prototype).parameters) == [
        "concept",
        "prompts",
        "top_k",
        "return_z_score",
    ]

    async def get_tool():
        async with Client(mcp) as client:
            return {tool.name: tool for tool in await client.list_tools()}[
                "search_songs_by_prototype"
            ]

    tool = asyncio.run(get_tool())
    assert tool.inputSchema["required"] == ["concept", "prompts"]
    assert tool.inputSchema["properties"]["top_k"]["default"] == 10


def test_prototype_search_emits_stage_timings(tmp_path, caplog):
    with caplog.at_level("INFO", logger=retrieval.LOGGER.name):
        _run(tmp_path, np.tile([1.0, 0.0, 0.0], (3, 1)))
    records = [
        record
        for record in caplog.records
        if getattr(record, "timing_category", None) == "prototype_search"
    ]
    assert len(records) == 1
    assert set(records[0].timings) == {
        "text_encoding_seconds",
        "prototype_construction_seconds",
        "sqlite_vec_retrieval_seconds",
        "result_projection_seconds",
    }
