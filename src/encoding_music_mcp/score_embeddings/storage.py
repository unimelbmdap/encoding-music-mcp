"""Transactional SQLite and sqlite-vec embedding repository."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, Self

import numpy as np

EXPECTED_EMBEDDING_DIMENSION = 768
SCHEMA_VERSION = 3
SQLITE_VEC_VERSION = "0.1.9"
QUERY_NORM_ABSOLUTE_TOLERANCE = 1e-4


class StorageError(RuntimeError):
    """Base exception for embedding persistence failures."""


class StorageDependencyError(StorageError):
    """Raised when the pinned SQLite vector extension is unavailable."""


class SchemaVersionError(StorageError):
    """Raised when a database schema is newer than this application."""


class EmbeddingDimensionError(StorageError):
    """Raised when an embedding does not match the repository dimension."""


class EmbeddingValueError(StorageError):
    """Raised when an embedding contains non-finite values."""


class EmbeddingModelIdentity(Protocol):
    """Structural identity accepted when restricting similarity searches."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    """A complete embedding and its reproducibility evidence."""

    score_id: str
    source_path: str
    source_sha256: str
    processing_fingerprint: str
    validation: Mapping[str, Any]
    model_commit: str
    model_revision: str
    model_weight_sha256: str
    raw_embedding: np.ndarray
    normalized_embedding: np.ndarray
    title: str | None = None
    artist: str | None = None
    work_created_date: str | None = None


@dataclass(frozen=True, slots=True)
class StoredEmbedding:
    """Relational embedding record returned by the repository."""

    id: int
    logical_key: str
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    source_path: str
    source_sha256: str
    processing_fingerprint: str
    validation: dict[str, Any]
    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int
    raw_embedding: np.ndarray
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    """A nearest-neighbor record and its cosine distance."""

    embedding: StoredEmbedding
    distance: float

    @property
    def embedding_id(self) -> int:
        """Return the catalog embedding identifier without exposing its vector."""
        return self.embedding.id

    @property
    def score_id(self) -> str:
        """Return the catalog score identifier."""
        return self.embedding.score_id

    @property
    def title(self) -> str | None:
        """Return the catalog title."""
        return self.embedding.title

    @property
    def artist(self) -> str | None:
        """Return the catalog artist or composer."""
        return self.embedding.artist

    @property
    def work_created_date(self) -> str | None:
        """Return the catalog work-creation date."""
        return self.embedding.work_created_date


@dataclass(frozen=True, slots=True)
class CatalogEmbedding:
    """Simple catalog record for callers that explicitly request vector data."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    vector: np.ndarray


@dataclass(frozen=True, slots=True)
class CatalogSimilarityResult:
    """Vector-free catalog projection of one similarity match."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    distance: float


@dataclass(frozen=True, slots=True)
class CountedCatalogSimilarityResult:
    """Vector-free catalog matches with exact-model eligibility accounting."""

    matches: tuple[CatalogSimilarityResult, ...]
    eligible_count: int
    excluded_count: int


def embedding_logical_key(record: EmbeddingRecord) -> str:
    """Return the stable identity for one source/configuration/model tuple."""
    identity = {
        "model_commit": record.model_commit,
        "model_revision": record.model_revision,
        "model_weight_sha256": record.model_weight_sha256,
        "processing_fingerprint": record.processing_fingerprint,
        "source_sha256": record.source_sha256,
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validated_vector(
    value: np.ndarray | Sequence[float],
    *,
    dimension: int,
) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32)
    if vector.shape != (dimension,):
        raise EmbeddingDimensionError(
            f"Embedding has shape {vector.shape}; expected ({dimension},)"
        )
    if not np.isfinite(vector).all():
        raise EmbeddingValueError("Embedding contains non-finite values")
    return np.ascontiguousarray(vector)


def _validated_query_vector(
    value: np.ndarray | Sequence[float],
    *,
    dimension: int,
) -> np.ndarray:
    """Validate that a query is a finite, non-zero L2-normalized vector."""
    vector = _validated_vector(value, dimension=dimension)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise EmbeddingValueError("Query embedding must be non-zero")
    if not np.isclose(norm, 1.0, rtol=0.0, atol=QUERY_NORM_ABSOLUTE_TOLERANCE):
        raise EmbeddingValueError(
            "Query embedding must be L2-normalized before search; "
            f"received norm {norm:.8g}"
        )
    return vector


@dataclass(frozen=True, slots=True)
class QueryVector:
    """A validated query vector and its provenance."""

    values: np.ndarray
    dimension: int = EXPECTED_EMBEDDING_DIMENSION
    model_identity: EmbeddingModelIdentity | None = None
    query_type: str = "generic"
    raw_norm: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "values",
            _validated_query_vector(self.values, dimension=self.dimension),
        )


class EmbeddingRepository:
    """Own migrations and paired relational/vector embedding operations."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        dimension: int = EXPECTED_EMBEDDING_DIMENSION,
        check_same_thread: bool = True,
    ) -> None:
        if dimension != EXPECTED_EMBEDDING_DIMENSION:
            raise EmbeddingDimensionError(
                "The pinned CLaMP/vector schema requires dimension "
                f"{EXPECTED_EMBEDDING_DIMENSION}, received {dimension}"
            )
        self.database_path = Path(database_path).expanduser().resolve()
        self.dimension = dimension
        self.check_same_thread = check_same_thread
        self._connection: sqlite3.Connection | None = None
        self._serialize_float32: Any = None

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the open database connection."""
        if self._connection is None:
            raise StorageError("Embedding repository is not open")
        return self._connection

    def open(self) -> None:
        """Open the database, load sqlite-vec, and apply migrations."""
        if self._connection is not None:
            return
        try:
            import sqlite_vec
        except ImportError as exc:
            raise StorageDependencyError(
                "sqlite-vec is required; install the score-embeddings extra"
            ) from exc
        if getattr(sqlite_vec, "__version__", None) != SQLITE_VEC_VERSION:
            raise StorageDependencyError(
                f"sqlite-vec {SQLITE_VEC_VERSION} is required; found "
                f"{getattr(sqlite_vec, '__version__', 'unknown')}"
            )

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.database_path,
            check_same_thread=self.check_same_thread,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
        except (AttributeError, sqlite3.Error) as exc:
            connection.close()
            raise StorageDependencyError(
                f"Failed to load the packaged sqlite-vec extension: {exc}"
            ) from exc
        finally:
            try:
                connection.enable_load_extension(False)
            except (AttributeError, sqlite3.Error):
                pass

        self._connection = connection
        self._serialize_float32 = sqlite_vec.serialize_float32
        try:
            self._migrate()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _migrate(self) -> None:
        connection = self.connection
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise SchemaVersionError(
                f"Database schema version {current_version} is newer than supported "
                f"version {SCHEMA_VERSION}"
            )
        if current_version == SCHEMA_VERSION:
            return
        try:
            connection.execute("BEGIN IMMEDIATE")
            if current_version == 0:
                connection.execute(
                    """
                    CREATE TABLE score_embeddings (
                        id INTEGER PRIMARY KEY,
                        logical_key TEXT NOT NULL UNIQUE,
                        score_id TEXT NOT NULL,
                        title TEXT,
                        artist TEXT,
                        work_created_date TEXT,
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
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX score_embeddings_score_id_idx
                    ON score_embeddings(score_id)
                    """
                )
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE embedding_vectors USING vec0(
                        embedding_id INTEGER PRIMARY KEY,
                        normalized_embedding float[768] distance_metric=cosine
                    )
                    """
                )
            elif current_version == 1:
                connection.execute("ALTER TABLE score_embeddings ADD COLUMN title TEXT")
                connection.execute(
                    "ALTER TABLE score_embeddings ADD COLUMN artist TEXT"
                )
                connection.execute(
                    "ALTER TABLE score_embeddings ADD COLUMN work_created_date TEXT"
                )
            connection.execute(
                """
                CREATE VIEW song_catalog AS
                SELECT
                    score_embeddings.title AS song_title,
                    score_embeddings.artist AS artist,
                    score_embeddings.work_created_date AS date_created,
                    embedding_vectors.normalized_embedding AS vector_embedding
                FROM score_embeddings
                JOIN embedding_vectors
                    ON embedding_vectors.embedding_id = score_embeddings.id
                """
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise StorageError(f"Failed to migrate embedding database: {exc}") from exc

    def upsert(self, record: EmbeddingRecord) -> StoredEmbedding:
        """Atomically insert or replace relational and vector representations."""
        raw = _validated_vector(record.raw_embedding, dimension=self.dimension)
        normalized = _validated_vector(
            record.normalized_embedding,
            dimension=self.dimension,
        )
        logical_key = embedding_logical_key(record)
        validation_json = json.dumps(
            record.validation,
            sort_keys=True,
            separators=(",", ":"),
        )
        connection = self.connection
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO score_embeddings (
                    logical_key, score_id, title, artist, work_created_date,
                    source_path, source_sha256,
                    processing_fingerprint, validation_json, model_commit,
                    model_revision, model_weight_sha256, dimension, raw_embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(logical_key) DO UPDATE SET
                    score_id = excluded.score_id,
                    title = excluded.title,
                    artist = excluded.artist,
                    work_created_date = excluded.work_created_date,
                    source_path = excluded.source_path,
                    validation_json = excluded.validation_json,
                    raw_embedding = excluded.raw_embedding,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    logical_key,
                    record.score_id,
                    record.title,
                    record.artist,
                    record.work_created_date,
                    record.source_path,
                    record.source_sha256,
                    record.processing_fingerprint,
                    validation_json,
                    record.model_commit,
                    record.model_revision,
                    record.model_weight_sha256,
                    self.dimension,
                    raw.tobytes(),
                ),
            )
            row = connection.execute(
                "SELECT id FROM score_embeddings WHERE logical_key = ?",
                (logical_key,),
            ).fetchone()
            if row is None:
                raise StorageError("Upsert completed without a relational record")
            embedding_id = int(row["id"])
            connection.execute(
                "DELETE FROM embedding_vectors WHERE embedding_id = ?",
                (embedding_id,),
            )
            connection.execute(
                """
                INSERT INTO embedding_vectors (embedding_id, normalized_embedding)
                VALUES (?, ?)
                """,
                (embedding_id, self._serialize_float32(normalized.tolist())),
            )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Failed to persist embedding: {exc}") from exc
        return self.get(embedding_id)

    def get(self, embedding_id: int) -> StoredEmbedding:
        """Return one stored embedding by integer identifier."""
        row = self.connection.execute(
            "SELECT * FROM score_embeddings WHERE id = ?",
            (embedding_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Embedding record does not exist: {embedding_id}")
        return self._row_to_embedding(row)

    def get_by_score_id(self, score_id: str) -> list[StoredEmbedding]:
        """Return all identities for a score in insertion order."""
        rows = self.connection.execute(
            "SELECT * FROM score_embeddings WHERE score_id = ? ORDER BY id",
            (score_id,),
        ).fetchall()
        return [self._row_to_embedding(row) for row in rows]

    def get_catalog(self, embedding_id: int) -> CatalogEmbedding:
        """Return one concise catalog record, including its requested raw vector."""
        embedding = self.get(embedding_id)
        return CatalogEmbedding(
            embedding_id=embedding.id,
            score_id=embedding.score_id,
            title=embedding.title,
            artist=embedding.artist,
            work_created_date=embedding.work_created_date,
            vector=embedding.raw_embedding,
        )

    def similarity_search(
        self,
        query: QueryVector | np.ndarray | Sequence[float],
        *,
        limit: int = 10,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> list[SimilarityResult]:
        """Run cosine KNN in SQLite, optionally restricted to one exact model.

        An identity filter with no compatible stored records returns an empty list.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        if isinstance(query, QueryVector):
            vector = query.values
            if model_identity is None and query.model_identity is not None:
                model_identity = query.model_identity
        else:
            vector = _validated_query_vector(query, dimension=self.dimension)
        total_records = int(
            self.connection.execute("SELECT count(*) FROM score_embeddings").fetchone()[
                0
            ]
        )
        if total_records == 0:
            return []
        if model_identity is None:
            identity_values: tuple[str | int | None, ...] = (None, None, None, None)
            candidate_count = min(limit, total_records)
        else:
            identity_values = (
                model_identity.model_commit,
                model_identity.model_revision,
                model_identity.model_weight_sha256,
                model_identity.dimension,
            )
            candidate_count = total_records
        rows = self.connection.execute(
            """
            SELECT score_embeddings.*, neighbors.distance
            FROM (
                SELECT embedding_id, distance
                FROM embedding_vectors
                WHERE normalized_embedding MATCH ? AND k = ?
            ) AS neighbors
            JOIN score_embeddings ON score_embeddings.id = neighbors.embedding_id
            WHERE ? IS NULL OR (
                score_embeddings.model_commit = ?
                AND score_embeddings.model_revision = ?
                AND score_embeddings.model_weight_sha256 = ?
                AND score_embeddings.dimension = ?
            )
            ORDER BY neighbors.distance, score_embeddings.id
            LIMIT ?
            """,
            (
                self._serialize_float32(vector.tolist()),
                candidate_count,
                identity_values[0],
                *identity_values,
                limit,
            ),
        ).fetchall()
        return [
            SimilarityResult(
                embedding=self._row_to_embedding(row),
                distance=float(row["distance"]),
            )
            for row in rows
        ]

    def catalog_similarity_search(
        self,
        query: QueryVector | np.ndarray | Sequence[float],
        *,
        limit: int = 10,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> list[CatalogSimilarityResult]:
        """Return a vector-free, optionally model-restricted catalog KNN result."""
        return [
            CatalogSimilarityResult(
                embedding_id=result.embedding_id,
                score_id=result.score_id,
                title=result.title,
                artist=result.artist,
                work_created_date=result.work_created_date,
                distance=result.distance,
            )
            for result in self.similarity_search(
                query,
                limit=limit,
                model_identity=model_identity,
            )
        ]

    def counted_catalog_similarity_search(
        self,
        query: QueryVector | np.ndarray | Sequence[float],
        *,
        limit: int = 10,
        model_identity: EmbeddingModelIdentity,
    ) -> CountedCatalogSimilarityResult:
        """Return exact-model catalog KNN matches and compatibility counts.

        ``excluded_count`` covers stored rows with different model provenance.
        Invalid vectors never reach storage and therefore are not counted here.
        """
        counts = self.connection.execute(
            """
            SELECT
                count(*) AS total_count,
                count(*) FILTER (WHERE
                    model_commit = ?
                    AND model_revision = ?
                    AND model_weight_sha256 = ?
                    AND dimension = ?
                ) AS eligible_count
            FROM score_embeddings
            """,
            (
                model_identity.model_commit,
                model_identity.model_revision,
                model_identity.model_weight_sha256,
                model_identity.dimension,
            ),
        ).fetchone()
        assert counts is not None
        total_count = int(counts["total_count"])
        eligible_count = int(counts["eligible_count"])
        matches = tuple(
            self.catalog_similarity_search(
                query,
                limit=limit,
                model_identity=model_identity,
            )
        )
        return CountedCatalogSimilarityResult(
            matches=matches,
            eligible_count=eligible_count,
            excluded_count=max(0, total_count - eligible_count),
        )

    def get_corpus_matrix(
        self,
        *,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> tuple[tuple[StoredEmbedding, ...], np.ndarray]:
        """Return all matching stored embeddings and an (N, dimension) L2-normalized float32 matrix."""
        if model_identity is None:
            rows = self.connection.execute(
                "SELECT * FROM score_embeddings ORDER BY id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT * FROM score_embeddings
                WHERE model_commit = ?
                  AND model_revision = ?
                  AND model_weight_sha256 = ?
                  AND dimension = ?
                ORDER BY id
                """,
                (
                    model_identity.model_commit,
                    model_identity.model_revision,
                    model_identity.model_weight_sha256,
                    model_identity.dimension,
                ),
            ).fetchall()
        if not rows:
            return (), np.empty((0, self.dimension), dtype=np.float32)

        embeddings = tuple(self._row_to_embedding(row) for row in rows)
        raw_list = [emb.raw_embedding for emb in embeddings]
        matrix = np.stack(raw_list).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized_matrix = matrix / norms
        return embeddings, normalized_matrix

    def compute_baseline_statistics(
        self,
        queries: Sequence[QueryVector | np.ndarray | Sequence[float]],
        *,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> list[tuple[float, float]]:
        """Compute (mean, std) of cosine similarities across the corpus for each query vector.

        Uses a fast matrix multiplication against stored corpus embeddings.
        """
        if not queries:
            return []

        vectors = []
        for q in queries:
            if isinstance(q, QueryVector):
                vectors.append(q.values)
                if model_identity is None and q.model_identity is not None:
                    model_identity = q.model_identity
            else:
                vectors.append(_validated_query_vector(q, dimension=self.dimension))

        query_matrix = np.stack(vectors).astype(np.float32)
        _, corpus_matrix = self.get_corpus_matrix(model_identity=model_identity)
        if corpus_matrix.shape[0] == 0:
            return [(0.0, 1.0) for _ in queries]

        similarities = corpus_matrix @ query_matrix.T
        for col_idx, q in enumerate(queries):
            raw_norm = q.raw_norm if isinstance(q, QueryVector) else 1.0
            if raw_norm != 1.0:
                similarities[:, col_idx] *= raw_norm

        means = similarities.mean(axis=0)
        stds = similarities.std(axis=0, ddof=0)

        results = []
        for mean_val, std_val in zip(means, stds, strict=True):
            std_float = float(std_val)
            if std_float <= 1e-7:
                std_float = 1.0
            results.append((float(mean_val), std_float))
        return results

    def similarity_search_by_id(
        self,
        embedding_id: int,
        *,
        limit: int = 10,
        include_self: bool = False,
    ) -> list[SimilarityResult]:
        """Find neighbors of an existing embedding record."""
        row = self.connection.execute(
            """
            SELECT normalized_embedding
            FROM embedding_vectors
            WHERE embedding_id = ?
            """,
            (embedding_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Embedding vector does not exist: {embedding_id}")
        query = np.frombuffer(row["normalized_embedding"], dtype=np.float32).copy()
        requested = limit if include_self else limit + 1
        results = self.similarity_search(query, limit=requested)
        if not include_self:
            results = [
                result for result in results if result.embedding.id != embedding_id
            ]
        return results[:limit]

    @staticmethod
    def _row_to_embedding(row: sqlite3.Row) -> StoredEmbedding:
        raw = np.frombuffer(row["raw_embedding"], dtype=np.float32).copy()
        return StoredEmbedding(
            id=int(row["id"]),
            logical_key=str(row["logical_key"]),
            score_id=str(row["score_id"]),
            title=str(row["title"]) if row["title"] is not None else None,
            artist=str(row["artist"]) if row["artist"] is not None else None,
            work_created_date=(
                str(row["work_created_date"])
                if row["work_created_date"] is not None
                else None
            ),
            source_path=str(row["source_path"]),
            source_sha256=str(row["source_sha256"]),
            processing_fingerprint=str(row["processing_fingerprint"]),
            validation=json.loads(row["validation_json"]),
            model_commit=str(row["model_commit"]),
            model_revision=str(row["model_revision"]),
            model_weight_sha256=str(row["model_weight_sha256"]),
            dimension=int(row["dimension"]),
            raw_embedding=raw,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
