"""Contrastive emotion retrieval over CLaMP score embeddings.

This module is deliberately query-only: importing it does not inspect the
environment, open SQLite, or invoke the external CLaMP runtime.
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import numpy as np

from ..score_embeddings import (
    CatalogSimilarityResult,
    ClampModelIdentity,
    ClampRuntimeConfig,
    EmbeddingRepository,
    TextEmbeddingBatch,
    embed_clamp3_texts,
)
from ..score_embeddings.clamp_extractor import CommandRunner

DATABASE_ENV = "ENCODING_MUSIC_EMBEDDINGS_DATABASE"
CLAMP_PYTHON_ENV = "ENCODING_MUSIC_CLAMP_PYTHON"
CLAMP_CACHE_ENV = "ENCODING_MUSIC_CLAMP_CACHE_DIR"
CLAMP_TIMEOUT_ENV = "ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 3600.0
MAX_SEARCH_LIMIT = 100


class EmotionRetrievalError(RuntimeError):
    """Raised when an emotion query cannot be safely executed."""


class EmotionMatchPayload(TypedDict):
    """JSON shape for one vector-free catalog match."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    distance: float


class EmotionModelPayload(TypedDict):
    """JSON shape for exact model provenance."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


class EmotionSearchPayload(TypedDict):
    """Claude-facing JSON result shape."""

    positive_emotion: str
    negative_emotion: str
    operation: str
    model: EmotionModelPayload
    matches: list[EmotionMatchPayload]


@dataclass(frozen=True, slots=True)
class EmotionSearchConfig:
    """Explicit runtime and database configuration for an emotion query."""

    database_path: Path
    clamp: ClampRuntimeConfig


@dataclass(frozen=True, slots=True)
class EmotionMatch:
    """Vector-free catalog projection returned to an MCP client."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    distance: float


@dataclass(frozen=True, slots=True)
class EmotionModelProvenance:
    """Exact CLaMP identity shared by the text and score embeddings."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


@dataclass(frozen=True, slots=True)
class EmotionSearchResult:
    """Typed, vector-free result of an ordered contrastive query."""

    positive_emotion: str
    negative_emotion: str
    operation: str
    model: EmotionModelProvenance
    matches: tuple[EmotionMatch, ...]

    def to_dict(self) -> EmotionSearchPayload:
        """Return the JSON-compatible MCP representation."""
        return {
            "positive_emotion": self.positive_emotion,
            "negative_emotion": self.negative_emotion,
            "operation": self.operation,
            "model": {
                "model_commit": self.model.model_commit,
                "model_revision": self.model.model_revision,
                "model_weight_sha256": self.model.model_weight_sha256,
                "dimension": self.model.dimension,
            },
            "matches": [
                {
                    "embedding_id": match.embedding_id,
                    "score_id": match.score_id,
                    "title": match.title,
                    "artist": match.artist,
                    "work_created_date": match.work_created_date,
                    "distance": match.distance,
                }
                for match in self.matches
            ],
        }


EmbeddingFunction = Callable[..., TextEmbeddingBatch]
RepositoryFactory = Callable[[Path], EmbeddingRepository]


def _required_path(environment: Mapping[str, str], name: str) -> Path:
    value = environment.get(name, "").strip()
    if not value:
        raise EmotionRetrievalError(
            f"Missing required environment variable {name}; configure it before "
            "calling search_songs_by_emotion"
        )
    return Path(value).expanduser().absolute()


def config_from_environment(
    environment: Mapping[str, str] | None = None,
) -> EmotionSearchConfig:
    """Build query configuration from narrowly scoped environment variables."""
    values = os.environ if environment is None else environment
    database_path = _required_path(values, DATABASE_ENV)
    python_executable = _required_path(values, CLAMP_PYTHON_ENV)

    if not database_path.is_file():
        raise EmotionRetrievalError(
            f"Configured embedding database does not exist: {database_path} "
            f"(from {DATABASE_ENV})"
        )
    if not python_executable.is_file():
        raise EmotionRetrievalError(
            f"Configured CLaMP interpreter does not exist: {python_executable} "
            f"(from {CLAMP_PYTHON_ENV})"
        )

    timeout_text = values.get(CLAMP_TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        timeout_seconds = float(timeout_text)
    except ValueError as exc:
        raise EmotionRetrievalError(
            f"{CLAMP_TIMEOUT_ENV} must be a positive finite number; got "
            f"{timeout_text!r}"
        ) from exc
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise EmotionRetrievalError(
            f"{CLAMP_TIMEOUT_ENV} must be a positive finite number; got "
            f"{timeout_text!r}"
        )

    cache_text = values.get(CLAMP_CACHE_ENV, "").strip()
    clamp_options: dict[str, Any] = {
        "python_executable": python_executable,
        "timeout_seconds": timeout_seconds,
    }
    if cache_text:
        clamp_options["cache_dir"] = Path(cache_text)

    return EmotionSearchConfig(
        database_path=database_path,
        clamp=ClampRuntimeConfig(**clamp_options),
    )


def _validate_request(
    positive_emotion: str,
    negative_emotion: str,
    limit: int,
) -> tuple[str, str]:
    if not isinstance(positive_emotion, str) or not positive_emotion.strip():
        raise ValueError("positive_emotion must be a non-blank string")
    if not isinstance(negative_emotion, str) or not negative_emotion.strip():
        raise ValueError("negative_emotion must be a non-blank string")
    positive = positive_emotion.strip()
    negative = negative_emotion.strip()
    if positive.casefold() == negative.casefold():
        raise ValueError("positive_emotion and negative_emotion must be distinct")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if limit <= 0 or limit > MAX_SEARCH_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_SEARCH_LIMIT}")
    return positive, negative


def _contrast_direction(
    batch: TextEmbeddingBatch,
    ordered_poles: tuple[str, str],
) -> np.ndarray:
    identity = batch.model_identity
    if batch.texts != ordered_poles:
        raise EmotionRetrievalError(
            "CLaMP returned text embeddings in an unexpected order"
        )
    raw = np.asarray(batch.raw)
    expected_shape = (2, identity.dimension)
    if raw.shape != expected_shape:
        raise EmotionRetrievalError(
            f"CLaMP text embeddings have shape {raw.shape}; expected {expected_shape}"
        )
    if not np.issubdtype(raw.dtype, np.number) or not np.isfinite(raw).all():
        raise EmotionRetrievalError(
            "CLaMP text embeddings must contain only finite numeric values"
        )

    # Contrast is intentionally formed from raw projections, then normalized once.
    direction = np.asarray(raw[0] - raw[1], dtype=np.float32)
    if not np.isfinite(direction).all():
        raise EmotionRetrievalError("The emotion contrast contains non-finite values")
    norm = float(np.linalg.norm(direction))
    if not math.isfinite(norm) or norm == 0.0:
        raise EmotionRetrievalError(
            "The emotion poles produced a zero contrast; choose more distinct emotions"
        )
    return np.ascontiguousarray(direction / norm, dtype=np.float32)


def _project_match(match: CatalogSimilarityResult) -> EmotionMatch:
    return EmotionMatch(
        embedding_id=match.embedding_id,
        score_id=match.score_id,
        title=match.title,
        artist=match.artist,
        work_created_date=match.work_created_date,
        distance=match.distance,
    )


def run_emotion_search(
    positive_emotion: str,
    negative_emotion: str,
    *,
    config: EmotionSearchConfig,
    limit: int = 10,
    runner: CommandRunner | None = None,
    embed_texts: EmbeddingFunction = embed_clamp3_texts,
    repository_factory: RepositoryFactory = EmbeddingRepository,
) -> EmotionSearchResult:
    """Encode an ordered emotion contrast and search compatible score vectors."""
    positive, negative = _validate_request(
        positive_emotion, negative_emotion, limit
    )
    poles = (positive, negative)
    embedding_options: dict[str, Any] = {}
    if runner is not None:
        embedding_options["runner"] = runner
    batch = embed_texts(poles, config.clamp, **embedding_options)
    direction = _contrast_direction(batch, poles)

    identity: ClampModelIdentity = batch.model_identity
    try:
        with repository_factory(config.database_path) as repository:
            matches = repository.catalog_similarity_search(
                direction,
                limit=limit,
                model_identity=identity,
            )
    except EmotionRetrievalError:
        raise
    except Exception as exc:
        raise EmotionRetrievalError(
            f"Emotion similarity search failed for {config.database_path}: {exc}"
        ) from exc

    return EmotionSearchResult(
        positive_emotion=positive,
        negative_emotion=negative,
        operation="positive - negative",
        model=EmotionModelProvenance(
            model_commit=identity.model_commit,
            model_revision=identity.model_revision,
            model_weight_sha256=identity.model_weight_sha256,
            dimension=identity.dimension,
        ),
        matches=tuple(_project_match(match) for match in matches),
    )


def search_songs_by_emotion(
    positive_emotion: str,
    negative_emotion: str,
    limit: int = 10,
) -> EmotionSearchPayload:
    """Find songs along an emotion contrast chosen by Claude.

    Claude must translate the user's request into two distinct ordered poles.
    For example, for "happiest songs", call with ``happy`` as the positive
    emotion and ``sad`` as the negative emotion. The application—not Claude—
    computes the aligned CLaMP vector as ``happy - sad`` and performs retrieval.
    """
    return run_emotion_search(
        positive_emotion,
        negative_emotion,
        config=config_from_environment(),
        limit=limit,
    ).to_dict()
