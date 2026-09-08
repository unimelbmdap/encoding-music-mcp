"""Matched-prompt semantic-axis retrieval over CLaMP score embeddings.

This module is deliberately query-only: importing it does not inspect the
environment, open SQLite, or invoke the external CLaMP runtime.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
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
from ..score_embeddings.runtime_config import (
    CLAMP_PYTHON_ENV as CLAMP_PYTHON_ENV,
    CLAMP_CACHE_ENV as CLAMP_CACHE_ENV,
    CLAMP_TIMEOUT_ENV as CLAMP_TIMEOUT_ENV,
    RuntimeConfigurationError,
    resolve_clamp_runtime,
)

DATABASE_ENV = "ENCODING_MUSIC_EMBEDDINGS_DATABASE"
STATIC_DATABASE_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "score-embeddings.sqlite"
)
MIN_PROMPTS_PER_POLE = 3
MAX_PROMPTS_PER_POLE = 5
MAX_SEARCH_LIMIT = 100

LOGGER = logging.getLogger(__name__)


class SemanticAxisRetrievalError(RuntimeError):
    """Raised when a semantic-axis query cannot be safely executed."""


class SemanticAxisMatchPayload(TypedDict):
    """JSON shape for one vector-free catalog match."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    distance: float


class SemanticAxisModelPayload(TypedDict):
    """JSON shape for exact model provenance."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


class SemanticAxisAggregationPayload(TypedDict):
    """JSON shape describing deterministic semantic-axis construction."""

    prompt_normalization: str
    centroid_aggregation: str
    centroid_normalization: str
    axis_operation: str
    axis_normalization: str


class SemanticAxisSearchPayload(TypedDict):
    """Claude-facing JSON result shape."""

    positive_prompts: list[str]
    negative_prompts: list[str]
    aggregation: SemanticAxisAggregationPayload
    model: SemanticAxisModelPayload
    matches: list[SemanticAxisMatchPayload]


@dataclass(frozen=True, slots=True)
class SemanticAxisSearchConfig:
    """Explicit runtime and database configuration for a semantic-axis query."""

    database_path: Path
    clamp: ClampRuntimeConfig


@dataclass(frozen=True, slots=True)
class SemanticAxisMatch:
    """Vector-free catalog projection returned to an MCP client."""

    embedding_id: int
    score_id: str
    title: str | None
    artist: str | None
    work_created_date: str | None
    distance: float


@dataclass(frozen=True, slots=True)
class SemanticAxisModelProvenance:
    """Exact CLaMP identity shared by the text and score embeddings."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


@dataclass(frozen=True, slots=True)
class SemanticAxisAggregationProvenance:
    """Stable description of the ADR-0005 aggregation pipeline."""

    prompt_normalization: str = "l2"
    centroid_aggregation: str = "arithmetic_mean"
    centroid_normalization: str = "l2"
    axis_operation: str = "positive_centroid - negative_centroid"
    axis_normalization: str = "l2"


@dataclass(frozen=True, slots=True)
class SemanticAxisSearchResult:
    """Typed, vector-free result of a matched-prompt semantic-axis query."""

    positive_prompts: tuple[str, ...]
    negative_prompts: tuple[str, ...]
    aggregation: SemanticAxisAggregationProvenance
    model: SemanticAxisModelProvenance
    matches: tuple[SemanticAxisMatch, ...]

    def to_dict(self) -> SemanticAxisSearchPayload:
        """Return the JSON-compatible MCP representation."""
        return {
            "positive_prompts": list(self.positive_prompts),
            "negative_prompts": list(self.negative_prompts),
            "aggregation": {
                "prompt_normalization": self.aggregation.prompt_normalization,
                "centroid_aggregation": self.aggregation.centroid_aggregation,
                "centroid_normalization": self.aggregation.centroid_normalization,
                "axis_operation": self.aggregation.axis_operation,
                "axis_normalization": self.aggregation.axis_normalization,
            },
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


class _RepositoryPool:
    """Serialize and reuse sqlite-vec connections by resolved database path."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._repositories: dict[Path, EmbeddingRepository] = {}

    def catalog_search(
        self,
        database_path: Path,
        direction: np.ndarray,
        *,
        limit: int,
        model_identity: ClampModelIdentity,
    ) -> list[CatalogSimilarityResult]:
        path = database_path.resolve()
        with self._lock:
            repository = self._repositories.get(path)
            if repository is None:
                repository = EmbeddingRepository(path, check_same_thread=False)
                repository.open()
                self._repositories[path] = repository
            return repository.catalog_similarity_search(
                direction,
                limit=limit,
                model_identity=model_identity,
            )

    def close(self) -> None:
        with self._lock:
            for repository in self._repositories.values():
                repository.close()
            self._repositories.clear()


_REPOSITORY_POOL = _RepositoryPool()


def close_semantic_axis_retrieval_resources() -> None:
    """Close lazily opened semantic-axis database connections."""
    _REPOSITORY_POOL.close()


def _resolve_database_path(environment: Mapping[str, str]) -> Path:
    raw_path = environment.get(DATABASE_ENV, "").strip()
    if raw_path:
        path = Path(raw_path).expanduser().absolute()
        if not path.is_file():
            raise SemanticAxisRetrievalError(
                f"Configured embedding database does not exist: {path} "
                f"(from {DATABASE_ENV})"
            )
        return path
    if (
        not STATIC_DATABASE_PATH.is_file()
        and STATIC_DATABASE_PATH.with_suffix(".sqlite3").is_file()
    ):
        return STATIC_DATABASE_PATH.with_suffix(".sqlite3")
    if not STATIC_DATABASE_PATH.is_file():
        raise SemanticAxisRetrievalError(
            f"Embedding database does not exist: {STATIC_DATABASE_PATH}"
        )
    return STATIC_DATABASE_PATH


def config_from_environment(
    environment: Mapping[str, str] | None = None,
) -> SemanticAxisSearchConfig:
    """Build query configuration from narrowly scoped environment variables."""
    values = os.environ if environment is None else environment
    database_path = _resolve_database_path(values)
    try:
        clamp = resolve_clamp_runtime(values)
    except RuntimeConfigurationError as exc:
        raise SemanticAxisRetrievalError(str(exc)) from exc
    return SemanticAxisSearchConfig(database_path=database_path, clamp=clamp)


def _validate_prompt_ensemble(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    if not MIN_PROMPTS_PER_POLE <= len(value) <= MAX_PROMPTS_PER_POLE:
        raise ValueError(
            f"{name} must contain between {MIN_PROMPTS_PER_POLE} and "
            f"{MAX_PROMPTS_PER_POLE} prompts"
        )

    prompts: list[str] = []
    for index, prompt in enumerate(value):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{name}[{index}] must be a non-blank string")
        prompts.append(prompt.strip())
    return tuple(prompts)


def _validate_request(
    positive_prompts: object,
    negative_prompts: object,
    limit: object,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    positive = _validate_prompt_ensemble(positive_prompts, "positive_prompts")
    negative = _validate_prompt_ensemble(negative_prompts, "negative_prompts")
    if len(positive) != len(negative):
        raise ValueError(
            "positive_prompts and negative_prompts must contain the same number "
            "of prompts"
        )
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if limit <= 0 or limit > 100000:
        raise ValueError("limit must be between 1 and 100000")
    return positive, negative


def _unit_vector(vector: np.ndarray, *, description: str) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise SemanticAxisRetrievalError(
            f"The {description} is zero or non-finite; choose more distinct prompts"
        )
    normalized = vector / norm
    if not np.isfinite(normalized).all():
        raise SemanticAxisRetrievalError(
            f"The normalized {description} contains non-finite values"
        )
    return normalized


def _semantic_axis_direction(
    batch: TextEmbeddingBatch,
    ordered_prompts: tuple[str, ...],
    pole_size: int,
) -> np.ndarray:
    identity = batch.model_identity
    if batch.texts != ordered_prompts:
        raise SemanticAxisRetrievalError(
            "CLaMP returned text embeddings in an unexpected order"
        )

    raw = np.asarray(batch.raw)
    expected_shape = (len(ordered_prompts), identity.dimension)
    if raw.shape != expected_shape:
        raise SemanticAxisRetrievalError(
            f"CLaMP text embeddings have shape {raw.shape}; expected {expected_shape}"
        )
    is_real_numeric = np.issubdtype(raw.dtype, np.integer) or np.issubdtype(
        raw.dtype, np.floating
    )
    if not is_real_numeric or not np.isfinite(raw).all():
        raise SemanticAxisRetrievalError(
            "CLaMP text embeddings must contain only finite real numeric values"
        )

    vectors = np.asarray(raw, dtype=np.float64)
    unit_prompts = np.empty_like(vectors)
    for index, vector in enumerate(vectors):
        unit_prompts[index] = _unit_vector(
            vector, description=f"prompt embedding at index {index}"
        )

    positive_mean = np.mean(unit_prompts[:pole_size], axis=0)
    negative_mean = np.mean(unit_prompts[pole_size:], axis=0)
    positive_centroid = _unit_vector(
        positive_mean, description="positive prompt centroid"
    )
    negative_centroid = _unit_vector(
        negative_mean, description="negative prompt centroid"
    )
    direction = _unit_vector(
        positive_centroid - negative_centroid,
        description="semantic-axis direction",
    )
    return np.ascontiguousarray(direction, dtype=np.float32)


def _project_match(match: CatalogSimilarityResult) -> SemanticAxisMatch:
    return SemanticAxisMatch(
        embedding_id=match.embedding_id,
        score_id=match.score_id,
        title=match.title,
        artist=match.artist,
        work_created_date=match.work_created_date,
        distance=match.distance,
    )


def run_semantic_axis_search(
    positive_prompts: list[str],
    negative_prompts: list[str],
    *,
    config: SemanticAxisSearchConfig,
    limit: int = 10,
    runner: CommandRunner | None = None,
    embed_texts: EmbeddingFunction = embed_clamp3_texts,
    repository_factory: RepositoryFactory | None = None,
) -> SemanticAxisSearchResult:
    """Encode matched prompt ensembles and search compatible score vectors."""
    positive, negative = _validate_request(positive_prompts, negative_prompts, limit)
    ordered_prompts = positive + negative
    embedding_options: dict[str, Any] = {}
    if runner is not None:
        embedding_options["runner"] = runner
    encoding_started = time.perf_counter()
    batch = embed_texts(ordered_prompts, config.clamp, **embedding_options)
    encoding_finished = time.perf_counter()
    direction = _semantic_axis_direction(batch, ordered_prompts, len(positive))
    axis_finished = time.perf_counter()

    identity: ClampModelIdentity = batch.model_identity
    try:
        if repository_factory is None:
            matches = _REPOSITORY_POOL.catalog_search(
                config.database_path,
                direction,
                limit=limit,
                model_identity=identity,
            )
        else:
            with repository_factory(config.database_path) as repository:
                matches = repository.catalog_similarity_search(
                    direction,
                    limit=limit,
                    model_identity=identity,
                )
    except SemanticAxisRetrievalError:
        raise
    except Exception as exc:
        raise SemanticAxisRetrievalError(
            f"Semantic-axis similarity search failed for {config.database_path}: {exc}"
        ) from exc

    retrieval_finished = time.perf_counter()
    result = SemanticAxisSearchResult(
        positive_prompts=positive,
        negative_prompts=negative,
        aggregation=SemanticAxisAggregationProvenance(),
        model=SemanticAxisModelProvenance(
            model_commit=identity.model_commit,
            model_revision=identity.model_revision,
            model_weight_sha256=identity.model_weight_sha256,
            dimension=identity.dimension,
        ),
        matches=tuple(_project_match(match) for match in matches),
    )
    projection_finished = time.perf_counter()
    stage_timings = {
        "text_encoding_seconds": encoding_finished - encoding_started,
        "axis_construction_seconds": axis_finished - encoding_finished,
        "sqlite_vec_retrieval_seconds": retrieval_finished - axis_finished,
        "result_projection_seconds": projection_finished - retrieval_finished,
    }
    LOGGER.info(
        "Semantic-axis stages: text_encoding=%.6fs axis_construction=%.6fs "
        "sqlite_vec_retrieval=%.6fs result_projection=%.6fs",
        stage_timings["text_encoding_seconds"],
        stage_timings["axis_construction_seconds"],
        stage_timings["sqlite_vec_retrieval_seconds"],
        stage_timings["result_projection_seconds"],
        extra={
            "timing_category": "semantic_axis_search",
            "timings": stage_timings,
        },
    )
    return result


def search_songs_by_semantic_axis(
    positive_prompts: list[str],
    negative_prompts: list[str],
    limit: int = 10,
    return_z_score: bool = False,
) -> SemanticAxisSearchPayload | dict[str, float]:
    """Rank songs along a high-level semantic contrast using matched prompt ensembles.

    Best suited to broad musical characteristics represented in CLaMP embeddings,
    including mood or emotion, energy or arousal, genre/style character, atmosphere,
    and texture. It is not intended for exact properties such as key, BPM, individual
    chords, notes, or bar-level events.

    Claude must translate the user's request into two ordered, genuinely contrasting
    poles: the requested direction and its semantic opposite. For each pole, generate
    3–5 short, caption-like music descriptions rather than isolated words or one long
    description.

    Prompts at the same position in each ensemble should have matching musical context
    and differ primarily in the requested attribute. Avoid introducing differences in
    genre, instrumentation, tempo, harmony, or production unless the user specified
    them. Both ensembles must be equally detailed.

    Example for "find the happiest songs":

    positive_prompts:
      - "Music expressing a joyful and optimistic mood."
      - "Happy, energetic music with a cheerful emotional character."
      - "Happy, calm music with a warm and contented character."

    negative_prompts:
      - "Music expressing a sorrowful and pessimistic mood."
      - "Sad, energetic music with a distressed emotional character."
      - "Sad, calm music with a melancholic and subdued character."

    Suitable contrasts include joyful–sorrowful, energetic–subdued, tense–peaceful,
    bright–dark, dense–sparse, playful–serious, acoustic–electronic, or an explicitly
    requested genre/style comparison such as jazz-like–classical-like.

    Do not invent an arbitrary opposite for a single category. For example, jazz and
    classical are only valid poles when the user explicitly requests that comparison.
    """
    if return_z_score:
        result = run_semantic_axis_search(
            positive_prompts,
            negative_prompts,
            config=config_from_environment(),
            limit=100000,
        )

        from .helpers import calculate_z_scores

        # Raw scores in semantic axis retrieval are 1.0 - match.distance ?
        # Wait, the match object has a `distance` attribute. The score is typically inverse of distance or similar.
        # But wait, in semantic axis, we want to score based on the projected distance along the axis.
        # Wait, the `match.distance` in `CatalogSimilarityResult` is the cosine distance. So smaller distance = higher match.
        # Or wait, for semantic axis, it might project onto the axis. Let's see what distance is.
        # The prompt says "raw scores". Should I use 1.0 - distance? Or just distance?
        # Actually, let's use `1.0 - distance` or just raw distance.
        # In PrototypeRetrieval, we did `centroid_norm * (1.0 - match.distance)`.
        # For semantic axis, it returns `matches` which have a `distance` attribute.
        # The z-score of `x` where x = 1 - distance, is the same as z-score of `x` (with opposite sign if we used distance directly).
        # We should use `1.0 - match.distance` as raw score for semantic axis? Or wait, let's just use `1.0 - match.distance` to be safe, since higher raw score should mean better match, so `1.0 - distance` makes sense. Wait, the prompt just says "calculate the raw scores for all of them". But `SemanticAxisMatch` only has `distance`.
        # So I will define raw_score = -match.distance or 1.0 - match.distance.
        # Let's use `-match.distance` or just `1.0 - match.distance`.
        raw_scores = [1.0 - match.distance for match in result.matches]
        z_scores = calculate_z_scores(raw_scores)

        scored_matches = list(zip(result.matches, z_scores))
        scored_matches.sort(key=lambda x: (x[1], -x[0].embedding_id), reverse=True)

        top_matches = scored_matches[:limit]
        return {
            match.title if match.title is not None else match.score_id: z_score
            for match, z_score in top_matches
        }

    return run_semantic_axis_search(
        positive_prompts,
        negative_prompts,
        config=config_from_environment(),
        limit=limit,
    ).to_dict()
