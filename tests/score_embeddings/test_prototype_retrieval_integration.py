"""Offline prototype-retrieval boundary tests with real sqlite-vec and real score-embeddings database."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from encoding_music_mcp.score_embeddings import (
    ClampModelIdentity,
    ClampRuntimeConfig,
    EmbeddingRecord,
    EmbeddingRepository,
    TextEmbeddingBatch,
    embed_clamp3_texts,
)
from encoding_music_mcp.score_embeddings.clamp_extractor import (
    CLAMP_C2_WEIGHT_SHA256,
    CLAMP_COMMIT,
    CLAMP_EXPECTED_DIMENSION,
    CLAMP_MODEL_REVISION,
)
from encoding_music_mcp.tools import prototype_retrieval
from encoding_music_mcp.tools.prototype_retrieval import (
    PrototypeRetrievalError,
    PrototypeSearchConfig,
    close_prototype_retrieval_resources,
    run_prototype_search,
    search_songs_by_prototype,
)

REAL_DB_PATH = Path("src/encoding_music_mcp/resources/score-embeddings.sqlite3").resolve()
MODEL_IDENTITY = ClampModelIdentity(
    CLAMP_COMMIT,
    CLAMP_MODEL_REVISION,
    CLAMP_C2_WEIGHT_SHA256,
    CLAMP_EXPECTED_DIMENSION,
)
PROMPTS = [
    "Jazz music with improvisatory melodic gestures.",
    "A performance shaped by jazz phrasing and harmony.",
    "Music expressing a recognizably jazz stylistic character.",
]


def _unit(index: int, dimension: int = CLAMP_EXPECTED_DIMENSION) -> np.ndarray:
    vector = np.zeros(dimension, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _record(score_id: str, vector: np.ndarray, **changes) -> EmbeddingRecord:
    record = EmbeddingRecord(
        score_id=score_id,
        source_path=f"/scores/{score_id}.mei",
        source_sha256=f"source-{score_id}",
        processing_fingerprint="processing-v1",
        validation={"status": "PASS"},
        model_commit=MODEL_IDENTITY.model_commit,
        model_revision=MODEL_IDENTITY.model_revision,
        model_weight_sha256=MODEL_IDENTITY.model_weight_sha256,
        raw_embedding=vector.copy(),
        normalized_embedding=vector.copy(),
        title=None,
        artist="Artist",
    )
    return replace(record, **changes)


def _config(database: Path, tmp_path: Path) -> PrototypeSearchConfig:
    return PrototypeSearchConfig(
        database_path=database,
        clamp=ClampRuntimeConfig(
            python_executable=Path(sys.executable),
            cache_dir=tmp_path / "cache",
            commit=MODEL_IDENTITY.model_commit,
            model_revision=MODEL_IDENTITY.model_revision,
            weight_sha256=MODEL_IDENTITY.model_weight_sha256,
            expected_dimension=CLAMP_EXPECTED_DIMENSION,
        ),
    )


def test_dynamic_prototype_retrieval_crosses_real_sqlite_and_clamp_boundary(
    tmp_path: Path,
):
    """Exercise prompt normalization, SQLite KNN, tie breaking, model filtering, and runner."""
    cache = tmp_path / "cache"
    code = cache / "source" / "code"
    code.mkdir(parents=True)
    (code / "extract_clamp3.py").write_text("# fake extractor\n", encoding="utf-8")

    database = tmp_path / "catalog.sqlite3"
    diagonal = (_unit(0) + _unit(1)) / np.sqrt(2.0)
    with EmbeddingRepository(database) as repository:
        first = repository.upsert(
            _record("first", diagonal, title="Shared Title", work_created_date="1901")
        )
        second = repository.upsert(_record("second", diagonal, title="Shared Title"))
        repository.upsert(_record("third", _unit(2), title=None))
        repository.upsert(
            _record(
                "ineligible",
                _unit(0),
                model_commit="different-commit",
                title="Closer but excluded",
            )
        )

    # Prompt vectors with varying magnitudes to verify independent normalization
    prompt_vectors = [
        _unit(0) * 10.0,
        _unit(1) * 2.0,
        diagonal * 0.5,
    ]
    calls: list[list[str]] = []

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        calls.append(command)
        input_dir = Path(command[2])
        output_dir = Path(command[3])
        for index, prompt in enumerate(PROMPTS):
            assert (input_dir / f"text_{index:06d}.txt").read_text(encoding="utf-8") == prompt
            np.save(output_dir / f"text_{index:06d}.npy", prompt_vectors[index])
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def embed_without_setup(texts, runtime, *, runner=None):
        return embed_clamp3_texts(texts, runtime, runner=runner, verify_setup=False)

    result = run_prototype_search(
        "jazz",
        PROMPTS,
        config=_config(database, tmp_path),
        top_k=10,
        runner=runner,
        embed_texts=embed_without_setup,
        repository_factory=EmbeddingRepository,
    )

    # Assertions on runner and ordering
    assert len(calls) == 1
    assert result.concept == "jazz"
    assert result.prompts == tuple(PROMPTS)

    # Exact-model eligibility & exclusion
    assert result.eligible_count == 3
    assert result.excluded_count == 1

    # Stable tie-breaking by ascending embedding_id
    assert [match.embedding_id for match in result.results[:2]] == [first.id, second.id]

    # Title-first catalog metadata (shared title and null title)
    assert [match.song_title for match in result.results[:2]] == [
        "Shared Title",
        "Shared Title",
    ]
    assert result.results[-1].song_title is None
    assert result.results[0].score_id == "first"
    assert result.results[0].artist == "Artist"
    assert result.results[0].work_created_date == "1901"

    # Explicit mean-cosine equivalence
    normalized_prompts = [v / np.linalg.norm(v) for v in prompt_vectors]
    expected_score = float(
        np.mean([np.dot(diagonal, p) for p in normalized_prompts])
    )
    assert result.results[0].score == pytest.approx(expected_score, abs=1e-6)

    # Vector-free output
    assert all(not hasattr(match, "vector") for match in result.results)
    payload = result.to_dict()
    assert "vector" not in str(payload).lower()


def test_dynamic_prototype_retrieval_rejects_zero_and_near_zero_centroids(
    tmp_path: Path,
):
    """Reject opposing prompts whose centroid is zero or below float32 epsilon."""
    opposing_prompts = ["prompt one", "prompt two", "prompt three", "prompt four"]
    raw_opposing = np.vstack([_unit(0), -_unit(0), _unit(1), -_unit(1)])

    def embed_degenerate(texts, config, **kwargs):
        return TextEmbeddingBatch(
            texts=tuple(texts),
            stems=tuple(f"text_{i}" for i in range(len(texts))),
            raw=raw_opposing,
            normalized=np.zeros_like(raw_opposing),
            model_identity=MODEL_IDENTITY,
        )

    with pytest.raises(
        PrototypeRetrievalError, match="centroid is zero or near-zero"
    ):
        run_prototype_search(
            "conflict",
            opposing_prompts,
            config=_config(tmp_path / "unused.sqlite3", tmp_path),
            embed_texts=embed_degenerate,
        )


@pytest.mark.skipif(
    not REAL_DB_PATH.is_file(),
    reason="real score-embeddings.sqlite3 database is not present in resources",
)
def test_dynamic_prototype_retrieval_against_real_score_embeddings_database(
    tmp_path: Path,
):
    """Exercise dynamic prototype search and z-score ranking on real score-embeddings database."""
    close_prototype_retrieval_resources()

    # Query the real database with a synthetic directional ensemble aligned to CLaMP
    prompt_direction = _unit(0)
    raw_prompts = np.vstack([
        prompt_direction * 10.0,
        prompt_direction * 1.0,
        prompt_direction * 0.1,
    ])

    def mock_embed(texts, config, **kwargs):
        return TextEmbeddingBatch(
            texts=tuple(texts),
            stems=tuple(f"text_{i:06d}" for i in range(len(texts))),
            raw=raw_prompts,
            normalized=np.zeros_like(raw_prompts),
            model_identity=MODEL_IDENTITY,
        )

    config = _config(REAL_DB_PATH, tmp_path)
    result = run_prototype_search(
        "real-corpus-prototype",
        PROMPTS,
        config=config,
        top_k=10,
        embed_texts=mock_embed,
    )

    # Real database has 290 complete score embeddings
    assert result.eligible_count == 290
    assert result.excluded_count == 0
    assert len(result.results) == 10
    assert all(match.song_title is not None for match in result.results)

    # Scores must be strictly descending with stable tie breaking
    scores = [match.score for match in result.results]
    assert scores == sorted(scores, reverse=True)
    assert all(not hasattr(match, "vector") for match in result.results)

    # Verify opt-in ADR-0007 dataset-normalized z-score retrieval on the real DB
    original_run_proto = prototype_retrieval.run_prototype_search

    def mock_run_proto(*args, **kwargs):
        kwargs["embed_texts"] = mock_embed
        return original_run_proto(*args, **kwargs)

    env = {
        "ENCODING_MUSIC_EMBEDDINGS_DATABASE": str(REAL_DB_PATH),
        "ENCODING_MUSIC_CLAMP_PYTHON": sys.executable,
    }

    try:
        with (
            patch.dict(os.environ, env),
            patch(
                "encoding_music_mcp.tools.prototype_retrieval.run_prototype_search",
                side_effect=mock_run_proto,
            ),
        ):
            z_result = search_songs_by_prototype(
                "real-corpus-prototype",
                PROMPTS,
                top_k=5,
                return_z_score=True,
            )
            assert isinstance(z_result, dict)
            assert len(z_result) == 5
            # Values are float z-scores
            for title, z_score in z_result.items():
                assert isinstance(title, str)
                assert isinstance(z_score, float)
    finally:
        close_prototype_retrieval_resources()
