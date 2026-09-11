"""Dynamic single-concept prototype retrieval over CLaMP score embeddings.

Importing this query-only module does not inspect the environment, open SQLite,
or invoke the external CLaMP runtime.
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

from .score_embeddings import (
    ClampModelIdentity,
    ClampRuntimeConfig,
    CountedCatalogSimilarityResult,
    EmbeddingRepository,
    TextEmbeddingBatch,
    embed_clamp3_texts,
)
from .score_embeddings.clamp_extractor import CommandRunner
from .score_embeddings.runtime_config import (
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
MIN_PROMPTS = 3
MAX_PROMPTS = 5
MAX_TOP_K = 100
CENTROID_NORM_EPSILON = float(np.finfo(np.float32).eps)
SCORE_DEFINITION = (
    "Mean cosine similarity across separately embedded and L2-normalized "
    "prototype prompts."
)
CLASSIFICATION_WARNING = (
    "Scores indicate semantic alignment, not definitive classification. "
    "Individual results might be incorrect, but usually the returned results are correct on average."
)

LOGGER = logging.getLogger(__name__)


class PrototypeRetrievalError(RuntimeError):
    """Raised when a prototype query cannot be safely executed."""


class PrototypeMatchPayload(TypedDict):
    rank: int
    song_title: str | None
    score_id: str
    embedding_id: int
    artist: str | None
    work_created_date: str | None
    score: float


class PrototypeModelPayload(TypedDict):
    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


class PrototypeSearchPayload(TypedDict):
    concept: str
    prompts: list[str]
    score_definition: str
    warning: str
    model: PrototypeModelPayload
    eligible_count: int
    excluded_count: int
    results: list[PrototypeMatchPayload]


@dataclass(frozen=True, slots=True)
class PrototypeSearchConfig:
    database_path: Path
    clamp: ClampRuntimeConfig


@dataclass(frozen=True, slots=True)
class PrototypeMatch:
    rank: int
    song_title: str | None
    score_id: str
    embedding_id: int
    artist: str | None
    work_created_date: str | None
    score: float


@dataclass(frozen=True, slots=True)
class PrototypeModelProvenance:
    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


@dataclass(frozen=True, slots=True)
class PrototypeSearchResult:
    concept: str
    prompts: tuple[str, ...]
    model: PrototypeModelProvenance
    eligible_count: int
    excluded_count: int
    results: tuple[PrototypeMatch, ...]
    score_definition: str = SCORE_DEFINITION
    warning: str = CLASSIFICATION_WARNING

    def to_dict(self) -> PrototypeSearchPayload:
        return {
            "concept": self.concept,
            "prompts": list(self.prompts),
            "score_definition": self.score_definition,
            "warning": self.warning,
            "model": {
                "model_commit": self.model.model_commit,
                "model_revision": self.model.model_revision,
                "model_weight_sha256": self.model.model_weight_sha256,
                "dimension": self.model.dimension,
            },
            "eligible_count": self.eligible_count,
            "excluded_count": self.excluded_count,
            "results": [
                {
                    "rank": match.rank,
                    "song_title": match.song_title,
                    "score_id": match.score_id,
                    "embedding_id": match.embedding_id,
                    "artist": match.artist,
                    "work_created_date": match.work_created_date,
                    "score": match.score,
                }
                for match in self.results
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
    ) -> CountedCatalogSimilarityResult:
        path = database_path.resolve()
        with self._lock:
            repository = self._repositories.get(path)
            if repository is None:
                repository = EmbeddingRepository(path, check_same_thread=False)
                repository.open()
                self._repositories[path] = repository
            return repository.counted_catalog_similarity_search(
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


def close_prototype_retrieval_resources() -> None:
    """Close lazily opened prototype-retrieval database connections."""
    _REPOSITORY_POOL.close()


def _resolve_database_path(environment: Mapping[str, str]) -> Path:
    raw_path = environment.get(DATABASE_ENV, "").strip()
    if raw_path:
        path = Path(raw_path).expanduser().absolute()
        if not path.is_file():
            raise PrototypeRetrievalError(
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
        raise PrototypeRetrievalError(
            f"Embedding database does not exist: {STATIC_DATABASE_PATH}"
        )
    return STATIC_DATABASE_PATH


def config_from_environment(
    environment: Mapping[str, str] | None = None,
) -> PrototypeSearchConfig:
    """Build query configuration from narrowly scoped environment variables."""
    values = os.environ if environment is None else environment
    database_path = _resolve_database_path(values)
    try:
        clamp = resolve_clamp_runtime(values)
    except RuntimeConfigurationError as exc:
        raise PrototypeRetrievalError(str(exc)) from exc
    return PrototypeSearchConfig(database_path=database_path, clamp=clamp)


def _validate_request(
    concept: object,
    prompts: object,
    top_k: object,
) -> tuple[str, tuple[str, ...]]:
    if not isinstance(concept, str) or not concept.strip():
        raise ValueError("concept must be a non-blank string")
    if not isinstance(prompts, list):
        raise ValueError("prompts must be a list")
    if not MIN_PROMPTS <= len(prompts) <= MAX_PROMPTS:
        raise ValueError(
            f"prompts must contain between {MIN_PROMPTS} and {MAX_PROMPTS} prompts"
        )
    normalized_prompts: list[str] = []
    for index, prompt in enumerate(prompts):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"prompts[{index}] must be a non-blank string")
        normalized_prompts.append(prompt.strip())
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")
    if not 1 <= top_k <= 100000:
        raise ValueError("top_k must be between 1 and 100000")
    return concept.strip(), tuple(normalized_prompts)


def _verify_model_identity(
    identity: ClampModelIdentity,
    config: ClampRuntimeConfig,
) -> None:
    expected = (
        config.commit,
        config.model_revision,
        config.weight_sha256,
        config.expected_dimension,
    )
    actual = (
        identity.model_commit,
        identity.model_revision,
        identity.model_weight_sha256,
        identity.dimension,
    )
    if actual != expected:
        raise PrototypeRetrievalError(
            "CLaMP text output model identity does not match the configured "
            "commit, revision, weight hash, and dimension"
        )


def _prototype_direction(
    batch: TextEmbeddingBatch,
    ordered_prompts: tuple[str, ...],
) -> tuple[np.ndarray, float]:
    if batch.texts != ordered_prompts:
        raise PrototypeRetrievalError(
            "CLaMP returned text embeddings in an unexpected order"
        )
    raw = np.asarray(batch.raw)
    expected_shape = (len(ordered_prompts), batch.model_identity.dimension)
    if raw.shape != expected_shape:
        raise PrototypeRetrievalError(
            f"CLaMP text embeddings have shape {raw.shape}; expected {expected_shape}"
        )
    is_real_numeric = np.issubdtype(raw.dtype, np.integer) or np.issubdtype(
        raw.dtype, np.floating
    )
    if not is_real_numeric or not np.isfinite(raw).all():
        raise PrototypeRetrievalError(
            "CLaMP text embeddings must contain only finite real numeric values"
        )
    vectors = np.asarray(raw, dtype=np.float64)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(norms).all() or np.any(norms == 0.0):
        raise PrototypeRetrievalError(
            "CLaMP returned a zero or non-finite prompt embedding"
        )
    unit_prompts = vectors / norms[:, np.newaxis]
    centroid = np.mean(unit_prompts, axis=0)
    centroid_norm = float(np.linalg.norm(centroid))
    if (
        not np.isfinite(centroid).all()
        or not math.isfinite(centroid_norm)
        or centroid_norm <= CENTROID_NORM_EPSILON
    ):
        raise PrototypeRetrievalError(
            "The prototype centroid is zero or near-zero; choose more coherent prompts"
        )
    direction = centroid / centroid_norm
    if not np.isfinite(direction).all():
        raise PrototypeRetrievalError(
            "The normalized prototype direction contains non-finite values"
        )
    return np.ascontiguousarray(direction, dtype=np.float32), centroid_norm


def run_prototype_search(
    concept: str,
    prompts: list[str],
    *,
    config: PrototypeSearchConfig,
    top_k: int = 10,
    runner: CommandRunner | None = None,
    embed_texts: EmbeddingFunction = embed_clamp3_texts,
    repository_factory: RepositoryFactory | None = None,
) -> PrototypeSearchResult:
    """Encode one dynamic prompt ensemble and search compatible score vectors."""
    clean_concept, ordered_prompts = _validate_request(concept, prompts, top_k)
    embedding_options: dict[str, Any] = {}
    if runner is not None:
        embedding_options["runner"] = runner
    encoding_started = time.perf_counter()
    batch = embed_texts(ordered_prompts, config.clamp, **embedding_options)
    encoding_finished = time.perf_counter()
    _verify_model_identity(batch.model_identity, config.clamp)
    direction, centroid_norm = _prototype_direction(batch, ordered_prompts)
    prototype_finished = time.perf_counter()
    identity = batch.model_identity
    try:
        if repository_factory is None:
            search_result = _REPOSITORY_POOL.catalog_search(
                config.database_path,
                direction,
                limit=top_k,
                model_identity=identity,
            )
        else:
            with repository_factory(config.database_path) as repository:
                search_result = repository.counted_catalog_similarity_search(
                    direction,
                    limit=top_k,
                    model_identity=identity,
                )
    except PrototypeRetrievalError:
        raise
    except Exception as exc:
        raise PrototypeRetrievalError(
            f"Prototype similarity search failed for {config.database_path}: {exc}"
        ) from exc
    retrieval_finished = time.perf_counter()
    projected: list[PrototypeMatch] = []
    for rank, match in enumerate(search_result.matches, start=1):
        score = centroid_norm * (1.0 - match.distance)
        if not math.isfinite(score):
            raise PrototypeRetrievalError(
                "SQLite returned a non-finite cosine distance"
            )
        projected.append(
            PrototypeMatch(
                rank=rank,
                song_title=match.title,
                score_id=match.score_id,
                embedding_id=match.embedding_id,
                artist=match.artist,
                work_created_date=match.work_created_date,
                score=score,
            )
        )
    result = PrototypeSearchResult(
        concept=clean_concept,
        prompts=ordered_prompts,
        model=PrototypeModelProvenance(
            model_commit=identity.model_commit,
            model_revision=identity.model_revision,
            model_weight_sha256=identity.model_weight_sha256,
            dimension=identity.dimension,
        ),
        eligible_count=search_result.eligible_count,
        excluded_count=search_result.excluded_count,
        results=tuple(projected),
    )
    projection_finished = time.perf_counter()
    timings = {
        "text_encoding_seconds": encoding_finished - encoding_started,
        "prototype_construction_seconds": prototype_finished - encoding_finished,
        "sqlite_vec_retrieval_seconds": retrieval_finished - prototype_finished,
        "result_projection_seconds": projection_finished - retrieval_finished,
    }
    LOGGER.info(
        "Prototype stages: text_encoding=%.6fs prototype_construction=%.6fs "
        "sqlite_vec_retrieval=%.6fs result_projection=%.6fs",
        timings["text_encoding_seconds"],
        timings["prototype_construction_seconds"],
        timings["sqlite_vec_retrieval_seconds"],
        timings["result_projection_seconds"],
        extra={"timing_category": "prototype_search", "timings": timings},
    )
    return result


def search_songs_by_prototype(
    concept: str,
    prompts: list[str],
    top_k: int = 10,
    return_z_score: bool = True,
) -> PrototypeSearchPayload | dict[str, float]:
    """Rank songs for one independent high-level concept using prompt consensus.

    Use this for a single category such as a genre or style, instrument, ensemble,
    mood category, atmosphere, setting, production or vocal character, rhythmic
    character, texture, broad harmony, or cultural/historical character. Supply
    3–5 short caption-like descriptions of the same concept at similar specificity.

    Do not combine independent concepts in one call. Use semantic-axis retrieval
    for a genuine bipolar continuum and symbolic tools for exact key, BPM, notes,
    chords, intervals, progressions, or bar locations.

    Scores return by default as standardized z-indices measuring concept outlierness in
    standard deviations from the dataset mean, so a single score makes sense without context.

    LLM Presentation Guidance:
    - When presenting results to the user, stipulate that individual results might be incorrect, but usually the returned results are correct on average.
    """
    if return_z_score:
        # Fetch a large number of results to compute true z-scores across the dataset
        result = run_prototype_search(
            concept,
            prompts,
            config=config_from_environment(),
            top_k=100000,
        )

        from .helpers import calculate_z_scores

        raw_scores = [match.score for match in result.results]
        z_scores = calculate_z_scores(raw_scores)

        # Combine matches with their z-scores
        scored_matches = list(zip(result.results, z_scores))

        # Sort by z-score descending, tie-breaking on embedding_id
        scored_matches.sort(key=lambda x: (x[1], -x[0].embedding_id), reverse=True)

        top_matches = scored_matches[:top_k]
        return {
            match.song_title
            if match.song_title is not None
            else match.score_id: z_score
            for match, z_score in top_matches
        }

    return run_prototype_search(
        concept,
        prompts,
        config=config_from_environment(),
        top_k=top_k,
    ).to_dict()
