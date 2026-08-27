"""Unit tests for Claude-facing contrastive emotion retrieval."""

from __future__ import annotations

import asyncio
import importlib
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
from encoding_music_mcp.tools import emotion_retrieval as retrieval


def _config(tmp_path: Path, dimension: int = 3) -> retrieval.EmotionSearchConfig:
    return retrieval.EmotionSearchConfig(
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
    raw: np.ndarray,
    *,
    texts: tuple[str, str] = ("happy", "sad"),
    identity: ClampModelIdentity | None = None,
) -> TextEmbeddingBatch:
    model = identity or ClampModelIdentity("c" * 40, "revision-a", "d" * 64, 3)
    return TextEmbeddingBatch(
        texts=texts,
        stems=("text_000000", "text_000001"),
        raw=raw,
        normalized=np.zeros_like(raw, dtype=float),
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


@pytest.mark.parametrize(
    ("positive", "negative", "limit", "message"),
    [
        ("", "sad", 10, "positive_emotion"),
        ("happy", "  ", 10, "negative_emotion"),
        ("Happy", " happy ", 10, "must be distinct"),
        ("happy", "sad", 0, "between 1 and 100"),
        ("happy", "sad", 101, "between 1 and 100"),
        ("happy", "sad", True, "must be an integer"),
    ],
)
def test_request_validation_happens_before_embedding(
    tmp_path: Path, positive: str, negative: str, limit: int, message: str
):
    def unexpected_embed(*args, **kwargs):
        pytest.fail("invalid input must not invoke CLaMP")

    with pytest.raises(ValueError, match=message):
        retrieval.run_emotion_search(
            positive,
            negative,
            config=_config(tmp_path),
            limit=limit,
            embed_texts=unexpected_embed,
        )


def test_raw_positive_minus_negative_is_normalized_once_and_identity_filtered(
    tmp_path: Path,
):
    captured: dict[str, object] = {}
    raw = np.array([[4.0, 3.0, 0.0], [1.0, -1.0, 0.0]])
    batch = _batch(raw)

    def embed(texts, config, **kwargs):
        captured["texts"] = tuple(texts)
        captured["runner"] = kwargs.get("runner")
        return batch

    def sentinel_runner(*args):
        return None
    result = retrieval.run_emotion_search(
        " happy ",
        " sad ",
        config=_config(tmp_path),
        limit=4,
        runner=sentinel_runner,
        embed_texts=embed,
        repository_factory=lambda path: _FakeRepository(path, captured),
    )

    expected_raw_contrast = raw[0] - raw[1]
    expected = expected_raw_contrast / np.linalg.norm(expected_raw_contrast)
    assert captured["texts"] == ("happy", "sad")
    assert captured["runner"] is sentinel_runner
    assert np.allclose(captured["query"], expected)
    assert np.linalg.norm(captured["query"]) == pytest.approx(1.0)
    assert captured["identity"] is batch.model_identity
    assert captured["limit"] == 4
    assert result.operation == "positive - negative"


@pytest.mark.parametrize(
    ("batch", "message"),
    [
        (_batch(np.ones((2, 2))), r"expected \(2, 3\)"),
        (_batch(np.array([[1.0, np.inf, 0.0], [0.0, 0.0, 0.0]])), "finite"),
        (_batch(np.ones((2, 3))), "zero contrast"),
        (_batch(np.ones((2, 3)), texts=("sad", "happy")), "unexpected order"),
    ],
)
def test_malformed_or_degenerate_text_embeddings_are_rejected(
    tmp_path: Path, batch: TextEmbeddingBatch, message: str
):
    with pytest.raises(retrieval.EmotionRetrievalError, match=message):
        retrieval.run_emotion_search(
            "happy",
            "sad",
            config=_config(tmp_path),
            embed_texts=lambda *args, **kwargs: batch,
        )


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

    with pytest.raises(retrieval.EmotionRetrievalError, match=retrieval.DATABASE_ENV):
        retrieval.config_from_environment({})
    with pytest.raises(retrieval.EmotionRetrievalError, match="does not exist"):
        retrieval.config_from_environment(
            {
                retrieval.DATABASE_ENV: str(tmp_path / "missing.sqlite3"),
                retrieval.CLAMP_PYTHON_ENV: sys.executable,
            }
        )
    with pytest.raises(retrieval.EmotionRetrievalError, match="positive finite"):
        retrieval.config_from_environment(
            {**environment, retrieval.CLAMP_TIMEOUT_ENV: "nan"}
        )


def test_result_is_deterministic_vector_free_and_retains_provenance(tmp_path: Path):
    captured: dict[str, object] = {}
    result = retrieval.run_emotion_search(
        "happy",
        "sad",
        config=_config(tmp_path),
        embed_texts=lambda *args, **kwargs: _batch(
            np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        ),
        repository_factory=lambda path: _FakeRepository(path, captured),
    ).to_dict()

    assert result["positive_emotion"] == "happy"
    assert result["negative_emotion"] == "sad"
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


def test_import_has_no_runtime_side_effects_and_tool_is_registered(monkeypatch):
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
    tool = tools["search_songs_by_emotion"]
    assert tool.parameters["required"] == ["positive_emotion", "negative_emotion"]
    assert "happy" in tool.description and "sad" in tool.description
