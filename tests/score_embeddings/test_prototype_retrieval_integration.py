"""Offline prototype-retrieval boundary tests with real sqlite-vec."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from encoding_music_mcp.score_embeddings import (
    ClampModelIdentity,
    ClampRuntimeConfig,
    EmbeddingRecord,
    EmbeddingRepository,
    TextEmbeddingBatch,
)
from encoding_music_mcp.tools.prototype_retrieval import (
    PrototypeSearchConfig,
    run_prototype_search,
)


IDENTITY = ClampModelIdentity("c" * 40, "revision-a", "d" * 64, 768)
PROMPTS = ["jazz description one", "jazz description two", "jazz description three"]


def _unit(index: int) -> np.ndarray:
    vector = np.zeros(768, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _record(score_id: str, vector: np.ndarray, **changes) -> EmbeddingRecord:
    record = EmbeddingRecord(
        score_id=score_id,
        source_path=f"/scores/{score_id}.mei",
        source_sha256=f"source-{score_id}",
        processing_fingerprint="processing-v1",
        validation={"status": "PASS"},
        model_commit=IDENTITY.model_commit,
        model_revision=IDENTITY.model_revision,
        model_weight_sha256=IDENTITY.model_weight_sha256,
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
            commit=IDENTITY.model_commit,
            model_revision=IDENTITY.model_revision,
            weight_sha256=IDENTITY.model_weight_sha256,
            expected_dimension=768,
        ),
    )


def test_dynamic_prototype_retrieval_crosses_real_sqlite_boundary(tmp_path: Path):
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

    raw_prompts = np.vstack([_unit(0) * 10.0, _unit(1), diagonal])

    def embed(texts, config, **kwargs):
        return TextEmbeddingBatch(
            texts=tuple(texts),
            stems=("one", "two", "three"),
            raw=raw_prompts,
            normalized=np.zeros_like(raw_prompts),
            model_identity=IDENTITY,
        )

    result = run_prototype_search(
        "jazz",
        PROMPTS,
        config=_config(database, tmp_path),
        top_k=10,
        embed_texts=embed,
        repository_factory=EmbeddingRepository,
    )

    assert result.eligible_count == 3
    assert result.excluded_count == 1
    assert [match.embedding_id for match in result.results[:2]] == [first.id, second.id]
    assert [match.song_title for match in result.results[:2]] == [
        "Shared Title",
        "Shared Title",
    ]
    expected = np.mean(
        [
            float(np.dot(diagonal, vector / np.linalg.norm(vector)))
            for vector in raw_prompts
        ]
    )
    assert result.results[0].score == pytest.approx(expected, abs=1e-6)
    assert result.results[-1].song_title is None
    assert all(not hasattr(match, "vector") for match in result.results)
