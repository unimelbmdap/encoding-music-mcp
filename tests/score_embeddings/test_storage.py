"""Tests for transactional sqlite-vec embedding persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from encoding_music_mcp.score_embeddings.clamp_extractor import ClampModelIdentity
from encoding_music_mcp.score_embeddings.storage import (
    EmbeddingDimensionError,
    EmbeddingRecord,
    EmbeddingRepository,
    EmbeddingValueError,
    SCHEMA_VERSION,
    SchemaVersionError,
    StorageError,
)


def _unit_vector(index: int) -> np.ndarray:
    vector = np.zeros(768, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _record(score_id: str = "score-a", index: int = 0) -> EmbeddingRecord:
    vector = _unit_vector(index)
    return EmbeddingRecord(
        score_id=score_id,
        source_path=f"/scores/{score_id}.mei",
        source_sha256=f"source-{score_id}",
        processing_fingerprint="processing-v1",
        validation={"status": "PASS", "pitch": 1.0, "timing": 1.0},
        model_commit="commit-a",
        model_revision="revision-a",
        model_weight_sha256="weight-a",
        raw_embedding=vector.copy(),
        normalized_embedding=vector.copy(),
    )


def _create_version_one_database(database: Path) -> None:
    """Create the previous production schema with one relational/vector pair."""
    import sqlite_vec

    connection = sqlite3.connect(database)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)
    connection.executescript(
        """
        CREATE TABLE score_embeddings (
            id INTEGER PRIMARY KEY,
            logical_key TEXT NOT NULL UNIQUE,
            score_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            processing_fingerprint TEXT NOT NULL,
            validation_json TEXT NOT NULL,
            model_commit TEXT NOT NULL,
            model_revision TEXT NOT NULL,
            model_weight_sha256 TEXT NOT NULL,
            dimension INTEGER NOT NULL CHECK (dimension = 768),
            raw_embedding BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX score_embeddings_score_id_idx
        ON score_embeddings(score_id);
        CREATE VIRTUAL TABLE embedding_vectors USING vec0(
            embedding_id INTEGER PRIMARY KEY,
            normalized_embedding float[768] distance_metric=cosine
        );
        PRAGMA user_version = 1;
        """
    )
    record = _record("legacy")
    connection.execute(
        """
        INSERT INTO score_embeddings (
            logical_key, score_id, source_path, source_sha256,
            processing_fingerprint, validation_json, model_commit,
            model_revision, model_weight_sha256, dimension, raw_embedding
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-logical-key",
            record.score_id,
            record.source_path,
            record.source_sha256,
            record.processing_fingerprint,
            '{"status":"PASS"}',
            record.model_commit,
            record.model_revision,
            record.model_weight_sha256,
            768,
            record.raw_embedding.tobytes(),
        ),
    )
    connection.execute(
        """
        INSERT INTO embedding_vectors (embedding_id, normalized_embedding)
        VALUES (?, ?)
        """,
        (1, sqlite_vec.serialize_float32(record.normalized_embedding.tolist())),
    )
    connection.commit()
    connection.close()


def _upgrade_fixture_to_version_two(database: Path) -> None:
    """Advance a version-one fixture to the previous metadata schema."""
    connection = sqlite3.connect(database)
    connection.execute("ALTER TABLE score_embeddings ADD COLUMN title TEXT")
    connection.execute("ALTER TABLE score_embeddings ADD COLUMN artist TEXT")
    connection.execute(
        "ALTER TABLE score_embeddings ADD COLUMN work_created_date TEXT"
    )
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    connection.close()


def test_repository_creates_versioned_relational_and_vector_schema(tmp_path: Path):
    database = tmp_path / "embeddings.sqlite3"

    with EmbeddingRepository(database) as repository:
        version = repository.connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in repository.connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        view_columns = [
            row[1]
            for row in repository.connection.execute("PRAGMA table_info(song_catalog)")
        ]
        columns = {
            row[1]
            for row in repository.connection.execute(
                "PRAGMA table_info(score_embeddings)"
            )
        }

    assert version == SCHEMA_VERSION
    assert "score_embeddings" in tables
    assert "embedding_vectors" in tables
    assert {"title", "artist", "work_created_date"} <= columns
    assert view_columns == [
        "song_title",
        "artist",
        "date_created",
        "vector_embedding",
    ]


def test_version_one_migration_preserves_vector_and_sets_nullable_metadata(
    tmp_path: Path,
):
    database = tmp_path / "legacy.sqlite3"
    _create_version_one_database(database)

    with EmbeddingRepository(database) as repository:
        stored = repository.get(1)
        vector_count = repository.connection.execute(
            "SELECT count(*) FROM embedding_vectors"
        ).fetchone()[0]
        results = repository.similarity_search(_unit_vector(0), limit=1)
        catalog_row = repository.connection.execute(
            "SELECT * FROM song_catalog"
        ).fetchone()
        version = repository.connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION
    assert stored.title is None
    assert stored.artist is None
    assert stored.work_created_date is None
    assert vector_count == 1
    assert results[0].embedding_id == 1
    assert results[0].distance == pytest.approx(0.0)
    assert catalog_row["song_title"] is None
    assert catalog_row["artist"] is None
    assert catalog_row["date_created"] is None
    assert np.array_equal(
        np.frombuffer(catalog_row["vector_embedding"], dtype=np.float32),
        _unit_vector(0),
    )


def test_version_two_migration_adds_usable_song_catalog_view(tmp_path: Path):
    database = tmp_path / "version-two.sqlite3"
    _create_version_one_database(database)
    _upgrade_fixture_to_version_two(database)
    connection = sqlite3.connect(database)
    connection.execute(
        """
        UPDATE score_embeddings
        SET title = ?, artist = ?, work_created_date = ?
        """,
        ("Legacy Song", "Legacy Artist", "1685"),
    )
    connection.commit()
    connection.close()

    with EmbeddingRepository(database) as repository:
        row = repository.connection.execute("SELECT * FROM song_catalog").fetchone()
        version = repository.connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION
    assert tuple(row.keys()) == (
        "song_title",
        "artist",
        "date_created",
        "vector_embedding",
    )
    assert row["song_title"] == "Legacy Song"
    assert row["artist"] == "Legacy Artist"
    assert row["date_created"] == "1685"
    assert np.array_equal(
        np.frombuffer(row["vector_embedding"], dtype=np.float32),
        _unit_vector(0),
    )


def test_repository_disables_extension_loading_after_sqlite_vec_initialization(
    tmp_path: Path,
):
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        with pytest.raises(sqlite3.OperationalError, match="not authorized"):
            repository.connection.execute(
                "SELECT load_extension(?)",
                (str(tmp_path / "untrusted-extension"),),
            ).fetchone()


def test_upsert_is_transactional_and_reuses_stable_identity(tmp_path: Path):
    record = _record()
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        first = repository.upsert(record)
        changed = replace(
            record,
            title="Prelude in C",
            artist="Example Composer",
            work_created_date="1722",
            source_path="/moved/score-a.mei",
            validation={"status": "PASS WITH WARNINGS"},
            raw_embedding=_unit_vector(2),
            normalized_embedding=_unit_vector(2),
        )
        second = repository.upsert(changed)
        relational_count = repository.connection.execute(
            "SELECT count(*) FROM score_embeddings"
        ).fetchone()[0]
        vector_count = repository.connection.execute(
            "SELECT count(*) FROM embedding_vectors"
        ).fetchone()[0]

    assert first.id == second.id
    assert second.source_path == "/moved/score-a.mei"
    assert second.title == "Prelude in C"
    assert second.artist == "Example Composer"
    assert second.work_created_date == "1722"
    assert second.validation["status"] == "PASS WITH WARNINGS"
    assert np.array_equal(second.raw_embedding, _unit_vector(2))
    assert relational_count == vector_count == 1


def test_changed_provenance_creates_distinct_identity(tmp_path: Path):
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        first = repository.upsert(_record())
        second = repository.upsert(
            replace(_record(), processing_fingerprint="processing-v2")
        )

    assert first.id != second.id
    assert first.logical_key != second.logical_key


def test_descriptive_metadata_is_not_part_of_logical_identity(tmp_path: Path):
    original = replace(
        _record(),
        title="Old title",
        artist="Old artist",
        work_created_date=None,
    )
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        first = repository.upsert(original)
        updated = repository.upsert(
            replace(
                original,
                title="New title",
                artist="New artist",
                work_created_date="circa 1600",
            )
        )

    assert first.id == updated.id
    assert first.logical_key == updated.logical_key
    assert updated.title == "New title"
    assert updated.artist == "New artist"
    assert updated.work_created_date == "circa 1600"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("raw_embedding", np.zeros(767), EmbeddingDimensionError),
        ("normalized_embedding", np.zeros(769), EmbeddingDimensionError),
        ("raw_embedding", np.full(768, np.nan), EmbeddingValueError),
    ],
)
def test_upsert_rejects_invalid_vectors_without_partial_rows(
    tmp_path: Path,
    field: str,
    value: np.ndarray,
    error: type[Exception],
):
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        with pytest.raises(error):
            repository.upsert(replace(_record(), **{field: value}))
        count = repository.connection.execute(
            "SELECT count(*) FROM score_embeddings"
        ).fetchone()[0]

    assert count == 0


def test_cosine_similarity_runs_in_vec0_and_orders_neighbors(tmp_path: Path):
    angled = np.zeros(768, dtype=np.float32)
    angled[:2] = [0.8, 0.6]
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        first = repository.upsert(_record("near", 0))
        repository.upsert(
            replace(
                _record("angled", 0),
                raw_embedding=angled,
                normalized_embedding=angled,
            )
        )
        repository.upsert(_record("far", 1))

        results = repository.similarity_search_by_id(first.id, limit=2)

    assert [result.embedding.score_id for result in results] == ["angled", "far"]
    assert results[0].distance == pytest.approx(0.2, abs=1e-5)
    assert results[1].distance == pytest.approx(1.0, abs=1e-5)


def test_catalog_projection_is_concise_and_knn_ties_are_ordered_by_id(
    tmp_path: Path,
):
    first_record = replace(
        _record("first"),
        title="First Song",
        artist="First Artist",
        work_created_date="1901-02-03",
    )
    second_record = replace(
        _record("second"),
        title="Second Song",
        artist="Second Artist",
    )
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        first = repository.upsert(first_record)
        second = repository.upsert(second_record)
        catalog = repository.get_catalog(first.id)
        matches = repository.catalog_similarity_search(_unit_vector(0), limit=2)

    assert np.array_equal(catalog.vector, _unit_vector(0))
    assert catalog.title == "First Song"
    assert [match.embedding_id for match in matches] == [first.id, second.id]
    assert matches[0].score_id == "first"
    assert matches[0].title == "First Song"
    assert matches[0].artist == "First Artist"
    assert matches[0].work_created_date == "1901-02-03"
    assert not hasattr(matches[0], "vector")


def test_model_filtered_knn_returns_all_requested_compatible_rows(
    tmp_path: Path,
):
    compatible_identity = ClampModelIdentity(
        model_commit="compatible-commit",
        model_revision="compatible-revision",
        model_weight_sha256="compatible-weight",
        dimension=768,
    )
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        for index in range(3):
            repository.upsert(_record(f"closer-incompatible-{index}", 0))
        compatible_first = repository.upsert(
            replace(
                _record("compatible-first", 1),
                model_commit=compatible_identity.model_commit,
                model_revision=compatible_identity.model_revision,
                model_weight_sha256=compatible_identity.model_weight_sha256,
            )
        )
        compatible_second = repository.upsert(
            replace(
                _record("compatible-second", 2),
                model_commit=compatible_identity.model_commit,
                model_revision=compatible_identity.model_revision,
                model_weight_sha256=compatible_identity.model_weight_sha256,
            )
        )

        matches = repository.catalog_similarity_search(
            _unit_vector(0),
            limit=2,
            model_identity=compatible_identity,
        )
        absent_matches = repository.similarity_search(
            _unit_vector(0),
            model_identity=ClampModelIdentity(
                model_commit="absent",
                model_revision="absent",
                model_weight_sha256="absent",
                dimension=768,
            ),
        )

    assert [match.embedding_id for match in matches] == [
        compatible_first.id,
        compatible_second.id,
    ]
    assert [match.score_id for match in matches] == [
        "compatible-first",
        "compatible-second",
    ]
    assert absent_matches == []


@pytest.mark.parametrize(
    ("query", "error", "message"),
    [
        (np.zeros(767), EmbeddingDimensionError, "expected"),
        (np.full(768, np.inf), EmbeddingValueError, "non-finite"),
        (np.zeros(768), EmbeddingValueError, "non-zero"),
        (_unit_vector(0) * 2.0, EmbeddingValueError, "L2-normalized"),
    ],
)
def test_arbitrary_query_rejects_invalid_or_non_normalized_vectors(
    tmp_path: Path,
    query: np.ndarray,
    error: type[Exception],
    message: str,
):
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        repository.upsert(_record())
        with pytest.raises(error, match=message):
            repository.similarity_search(query)


def test_vector_insert_failure_rolls_back_relational_write(tmp_path: Path):
    with EmbeddingRepository(tmp_path / "embeddings.sqlite3") as repository:
        repository._serialize_float32 = lambda _: b"invalid-dimension"  # type: ignore[method-assign]

        with pytest.raises(StorageError, match="persist embedding"):
            repository.upsert(_record())

        count = repository.connection.execute(
            "SELECT count(*) FROM score_embeddings"
        ).fetchone()[0]

    assert count == 0


def test_newer_schema_is_rejected(tmp_path: Path):
    database = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    connection.close()

    with pytest.raises(SchemaVersionError, match="newer"):
        with EmbeddingRepository(database):
            pass
