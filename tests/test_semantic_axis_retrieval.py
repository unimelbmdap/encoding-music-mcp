"""Unit tests for Claude-facing matched-prompt semantic-axis retrieval."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

from encoding_music_mcp.score_embeddings import (
    CatalogSimilarityResult,
    ClampModelIdentity,
    ClampRuntimeConfig,
    TextEmbeddingBatch,
)
from encoding_music_mcp.server import mcp
from encoding_music_mcp.tools import semantic_axis_retrieval as retrieval


def _prompts(prefix: str, count: int = 3) -> list[str]:
    return [f"{prefix} musical description {index}." for index in range(count)]


def _config(tmp_path: Path, dimension: int = 3) -> retrieval.SemanticAxisSearchConfig:
    return retrieval.SemanticAxisSearchConfig(
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


def _batch(
    raw: object,
    *,
    texts: tuple[str, ...] | None = None,
    identity: ClampModelIdentity | None = None,
) -> TextEmbeddingBatch:
    model = identity or ClampModelIdentity("c" * 40, "revision-a", "d" * 64, 3)
    array = np.asarray(raw)
    count = len(array) if array.ndim else 0
    ordered = texts or tuple(_prompts("positive") + _prompts("negative"))
    return TextEmbeddingBatch(
        texts=ordered,
        stems=tuple(f"text_{index:06d}" for index in range(count)),
        raw=array,
        normalized=np.zeros_like(array, dtype=float),
        model_identity=model,
    )


class _FakeRepository:
    def __init__(self, path: Path, captured: dict[str, object]):
        captured["path"] = path
        self.captured = captured

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def catalog_similarity_search(self, query, *, limit, model_identity):
        self.captured["query"] = query.copy()
        self.captured["limit"] = limit
        self.captured["identity"] = model_identity
        return [
            CatalogSimilarityResult(
                embedding_id=7,
                score_id="score-seven",
                title="Seventh Song",
                artist="Composer",
                work_created_date="1907",
                distance=0.125,
            )
        ]


def _run_with_batch(
    tmp_path: Path,
    batch: TextEmbeddingBatch,
    *,
    positive: list[str] | None = None,
    negative: list[str] | None = None,
    captured: dict[str, object] | None = None,
):
    values = captured if captured is not None else {}
    return retrieval.run_semantic_axis_search(
        positive or _prompts("positive"),
        negative or _prompts("negative"),
        config=_config(tmp_path, batch.model_identity.dimension),
        embed_texts=lambda *args, **kwargs: batch,
        repository_factory=lambda path: _FakeRepository(path, values),
    )


@pytest.mark.parametrize(
    ("positive", "negative", "limit", "message"),
    [
        (("p1", "p2", "p3"), _prompts("negative"), 10, "must be a list"),
        (_prompts("positive"), "not-a-list", 10, "must be a list"),
        (_prompts("positive", 2), _prompts("negative", 2), 10, "between 3 and 5"),
        (_prompts("positive", 6), _prompts("negative", 6), 10, "between 3 and 5"),
        (_prompts("positive", 3), _prompts("negative", 4), 10, "same number"),
        (["positive one", " ", "positive three"], _prompts("negative"), 10, "non-blank"),
        (_prompts("positive"), ["negative one", 2, "negative three"], 10, "non-blank"),
        (_prompts("positive"), _prompts("negative"), 0, "between 1 and 100000"),
        (_prompts("positive"), _prompts("negative"), 100001, "between 1 and 100000"),
        (_prompts("positive"), _prompts("negative"), True, "must be an integer"),
        (_prompts("positive"), _prompts("negative"), 1.5, "must be an integer"),
    ],
)
def test_request_validation_happens_before_embedding(
    tmp_path: Path,
    positive: object,
    negative: object,
    limit: object,
    message: str,
):
    def unexpected_embed(*args, **kwargs):
        pytest.fail("invalid input must not invoke CLaMP")

    with pytest.raises(ValueError, match=message):
        retrieval.run_semantic_axis_search(
            positive,  # type: ignore[arg-type]
            negative,  # type: ignore[arg-type]
            config=_config(tmp_path),
            limit=limit,  # type: ignore[arg-type]
            embed_texts=unexpected_embed,
        )


@pytest.mark.parametrize("count", [3, 4, 5])
def test_valid_ensemble_cardinalities_use_one_ordered_batch(tmp_path: Path, count: int):
    positive = _prompts("positive", count)
    negative = _prompts("negative", count)
    ordered = tuple(positive + negative)
    captured: dict[str, object] = {}
    raw = np.vstack(
        [np.tile([1.0, 0.0, 0.0], (count, 1)), np.tile([0.0, 1.0, 0.0], (count, 1))]
    )

    def embed(texts, config, **kwargs):
        captured["calls"] = int(captured.get("calls", 0)) + 1
        captured["texts"] = tuple(texts)
        return _batch(raw, texts=ordered)

    retrieval.run_semantic_axis_search(
        positive,
        negative,
        config=_config(tmp_path),
        embed_texts=embed,
        repository_factory=lambda path: _FakeRepository(path, captured),
    )

    assert captured["calls"] == 1
    assert captured["texts"] == ordered


def test_repeated_searches_repeat_encoding_and_retrieval_without_query_cache(
    tmp_path: Path,
):
    positive = _prompts("positive")
    negative = _prompts("negative")
    ordered = tuple(positive + negative)
    raw = np.array([[1.0, 0.0, 0.0]] * 3 + [[0.0, 1.0, 0.0]] * 3)
    captured: dict[str, object] = {"embedding_calls": 0, "retrieval_calls": 0}

    def embed(texts, config, **kwargs):
        captured["embedding_calls"] = int(captured["embedding_calls"]) + 1
        return _batch(raw, texts=tuple(texts))

    class CountingRepository(_FakeRepository):
        def catalog_similarity_search(self, query, *, limit, model_identity):
            captured["retrieval_calls"] = int(captured["retrieval_calls"]) + 1
            return super().catalog_similarity_search(
                query,
                limit=limit,
                model_identity=model_identity,
            )

    for _ in range(2):
        retrieval.run_semantic_axis_search(
            positive,
            negative,
            config=_config(tmp_path),
            embed_texts=embed,
            repository_factory=lambda path: CountingRepository(path, captured),
        )

    assert captured["embedding_calls"] == 2
    assert captured["retrieval_calls"] == 2
    assert ordered == tuple(positive + negative)


def test_repository_pool_reuses_connection_and_closes_it(tmp_path: Path, monkeypatch):
    created = []

    class Repository:
        def __init__(self, path, *, check_same_thread):
            self.path = path
            self.check_same_thread = check_same_thread
            self.open_calls = 0
            self.search_calls = 0
            self.closed = False
            created.append(self)

        def open(self):
            self.open_calls += 1

        def catalog_similarity_search(self, query, *, limit, model_identity):
            self.search_calls += 1
            return []

        def close(self):
            self.closed = True

    monkeypatch.setattr(retrieval, "EmbeddingRepository", Repository)
    pool = retrieval._RepositoryPool()
    identity = ClampModelIdentity("c" * 40, "revision-a", "d" * 64, 3)
    direction = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    for _ in range(2):
        pool.catalog_search(
            tmp_path / "catalog.sqlite3",
            direction,
            limit=5,
            model_identity=identity,
        )
    pool.close()

    assert len(created) == 1
    assert created[0].check_same_thread is False
    assert created[0].open_calls == 1
    assert created[0].search_calls == 2
    assert created[0].closed is True


def test_each_prompt_is_normalized_before_averaging(tmp_path: Path):
    positive = _prompts("positive")
    negative = _prompts("negative")
    raw = np.array(
        [
            [100.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
        ]
    )
    captured: dict[str, object] = {}

    _run_with_batch(
        tmp_path,
        _batch(raw, texts=tuple(positive + negative)),
        positive=positive,
        negative=negative,
        captured=captured,
    )

    positive_centroid = np.array([1.0, 2.0, 0.0]) / np.sqrt(5.0)
    expected = positive_centroid - np.array([-1.0, 0.0, 0.0])
    expected /= np.linalg.norm(expected)
    assert np.allclose(captured["query"], expected)


def test_each_pole_centroid_is_normalized_before_subtraction(tmp_path: Path):
    positive = _prompts("positive", 4)
    negative = _prompts("negative", 4)
    raw = np.array(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
        ]
    )
    captured: dict[str, object] = {}

    _run_with_batch(
        tmp_path,
        _batch(raw, texts=tuple(positive + negative)),
        positive=positive,
        negative=negative,
        captured=captured,
    )

    expected = np.array([1.0, -1.0, 0.0]) / np.sqrt(2.0)
    assert np.allclose(captured["query"], expected)


def test_final_centroid_difference_is_normalized_and_identity_filtered(tmp_path: Path):
    captured: dict[str, object] = {}
    positive = _prompts("positive")
    negative = _prompts("negative")
    raw = np.array([[1.0, 0.0, 0.0]] * 3 + [[0.0, 1.0, 0.0]] * 3)
    batch = _batch(raw, texts=tuple(positive + negative))

    def embed(texts, config, **kwargs):
        captured["texts"] = tuple(texts)
        captured["runner"] = kwargs.get("runner")
        return batch

    def sentinel_runner(*args):
        return None

    result = retrieval.run_semantic_axis_search(
        positive,
        negative,
        config=_config(tmp_path),
        limit=4,
        runner=sentinel_runner,
        embed_texts=embed,
        repository_factory=lambda path: _FakeRepository(path, captured),
    )

    assert np.linalg.norm(captured["query"]) == pytest.approx(1.0)
    assert captured["identity"] is batch.model_identity
    assert captured["limit"] == 4
    assert captured["runner"] is sentinel_runner
    assert result.aggregation.axis_operation == "positive_centroid - negative_centroid"


@pytest.mark.parametrize(
    ("batch", "positive", "negative", "message"),
    [
        (_batch(np.ones((6, 2))), None, None, r"expected \(6, 3\)"),
        (_batch(np.array([[1.0, np.inf, 0.0]] * 6)), None, None, "finite real numeric"),
        (_batch(np.array([["one", "two", "three"]] * 6)), None, None, "finite real numeric"),
        (
            _batch(np.array([[0.0, 0.0, 0.0]] + [[1.0, 0.0, 0.0]] * 5)),
            None,
            None,
            "prompt embedding at index 0",
        ),
        (
            _batch(
                np.array(
                    [
                        [1.0, 0.0, 0.0],
                        [-1.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                        [0.0, -1.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                    ]
                ),
                texts=tuple(_prompts("positive", 4) + _prompts("negative", 4)),
            ),
            _prompts("positive", 4),
            _prompts("negative", 4),
            "positive prompt centroid",
        ),
        (_batch(np.array([[1.0, 0.0, 0.0]] * 6)), None, None, "semantic-axis direction"),
        (
            _batch(
                np.array([[1.0, 0.0, 0.0]] * 3 + [[0.0, 1.0, 0.0]] * 3),
                texts=tuple(_prompts("negative") + _prompts("positive")),
            ),
            None,
            None,
            "unexpected order",
        ),
    ],
)
def test_malformed_or_degenerate_text_embeddings_are_rejected(
    tmp_path: Path,
    batch: TextEmbeddingBatch,
    positive: list[str] | None,
    negative: list[str] | None,
    message: str,
):
    with pytest.raises(retrieval.SemanticAxisRetrievalError, match=message):
        _run_with_batch(tmp_path, batch, positive=positive, negative=negative)


def test_environment_configuration_is_call_time_and_actionable(tmp_path: Path):
    database = tmp_path / "songs.sqlite3"
    database.touch()
    environment = {
        retrieval.DATABASE_ENV: str(database),
        retrieval.CLAMP_PYTHON_ENV: sys.executable,
        retrieval.CLAMP_CACHE_ENV: str(tmp_path / "model-cache"),
        retrieval.CLAMP_TIMEOUT_ENV: "12.5",
    }

    config = retrieval.config_from_environment(environment)

    assert config.database_path == database.absolute()
    assert config.clamp.python_executable == Path(sys.executable).absolute()
    assert config.clamp.cache_dir == (tmp_path / "model-cache").resolve()
    assert config.clamp.timeout_seconds == 12.5

    with pytest.raises(
        retrieval.SemanticAxisRetrievalError, match=retrieval.DATABASE_ENV
    ):
        retrieval.config_from_environment({})
    with pytest.raises(retrieval.SemanticAxisRetrievalError, match="does not exist"):
        retrieval.config_from_environment(
            {
                retrieval.DATABASE_ENV: str(tmp_path / "missing.sqlite3"),
                retrieval.CLAMP_PYTHON_ENV: sys.executable,
            }
        )
    with pytest.raises(retrieval.SemanticAxisRetrievalError, match="positive finite"):
        retrieval.config_from_environment(
            {**environment, retrieval.CLAMP_TIMEOUT_ENV: "nan"}
        )


def test_result_is_deterministic_vector_free_and_retains_provenance(tmp_path: Path):
    captured: dict[str, object] = {}
    positive = [" positive one ", "positive two", "positive three"]
    negative = [" negative one ", "negative two", "negative three"]
    encoded = tuple(prompt.strip() for prompt in positive + negative)
    result = retrieval.run_semantic_axis_search(
        positive,
        negative,
        config=_config(tmp_path),
        embed_texts=lambda *args, **kwargs: _batch(
            np.array([[1.0, 0.0, 0.0]] * 3 + [[0.0, 1.0, 0.0]] * 3),
            texts=encoded,
        ),
        repository_factory=lambda path: _FakeRepository(path, captured),
    ).to_dict()

    assert result["positive_prompts"] == [
        "positive one",
        "positive two",
        "positive three",
    ]
    assert result["negative_prompts"] == [
        "negative one",
        "negative two",
        "negative three",
    ]
    assert result["aggregation"] == {
        "prompt_normalization": "l2",
        "centroid_aggregation": "arithmetic_mean",
        "centroid_normalization": "l2",
        "axis_operation": "positive_centroid - negative_centroid",
        "axis_normalization": "l2",
    }
    assert result["model"] == {
        "model_commit": "c" * 40,
        "model_revision": "revision-a",
        "model_weight_sha256": "d" * 64,
        "dimension": 3,
    }
    assert result["matches"] == [
        {
            "embedding_id": 7,
            "score_id": "score-seven",
            "title": "Seventh Song",
            "artist": "Composer",
            "work_created_date": "1907",
            "distance": 0.125,
        }
    ]
    assert "vector" not in repr(result).lower()


def test_import_has_no_runtime_side_effects_and_only_semantic_axis_tool_is_registered(
    monkeypatch,
):
    monkeypatch.setattr(
        retrieval.EmbeddingRepository,
        "open",
        lambda self: pytest.fail("import must not open a database"),
    )
    monkeypatch.setattr(
        retrieval,
        "embed_clamp3_texts",
        lambda *args, **kwargs: pytest.fail("import must not invoke CLaMP"),
    )
    importlib.reload(retrieval)

    tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
    assert "search_songs_by_emotion" not in tools
    tool = tools["search_songs_by_semantic_axis"]
    assert tool.parameters["required"] == ["positive_prompts", "negative_prompts"]
    assert tool.parameters["properties"]["positive_prompts"]["type"] == "array"
    assert tool.parameters["properties"]["negative_prompts"]["type"] == "array"
    assert tool.description == inspect.getdoc(retrieval.search_songs_by_semantic_axis)
    assert "3–5 short, caption-like music descriptions" in tool.description
    assert "Do not invent an arbitrary opposite" in tool.description


def test_retired_emotion_module_and_symbols_are_absent():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("encoding_music_mcp.tools.emotion_retrieval")
    assert not hasattr(retrieval, "run_emotion_search")
    assert not hasattr(retrieval, "EmotionSearchPayload")
