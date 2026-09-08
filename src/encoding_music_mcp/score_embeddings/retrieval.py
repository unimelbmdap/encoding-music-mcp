"""Unified vector retrieval domain model and composed query service under ADR-0008."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .clamp_extractor import (
    TextEncoder,
)
from .storage import (
    EmbeddingModelIdentity,
    EmbeddingRepository,
    QueryVector,
)

LOGGER = logging.getLogger(__name__)
CENTROID_NORM_EPSILON = float(np.finfo(np.float32).eps)
SCORE_DEFINITION = (
    "Dataset-normalized z-index measuring outlierness in standard deviations from the dataset mean. "
    "Individual results might be incorrect, but returned results are usually correct on average."
)


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0 or not np.isfinite(norm):
        return np.zeros_like(vector)
    return vector / norm


@dataclass(frozen=True, slots=True)
class PrototypeVector(QueryVector):
    """Specialized QueryVector constructed from prototype concept descriptions."""

    concept: str = ""
    prompts: tuple[str, ...] = ()
    centroid_norm: float = 1.0

    @classmethod
    def build(
        cls,
        concept: str,
        prompts: Sequence[str],
        prompt_embeddings: np.ndarray,
        *,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> PrototypeVector:
        """Build a PrototypeVector following ADR-0006 independently normalized centroid rules."""
        if not concept.strip():
            raise ValueError("concept must not be blank")
        if not (3 <= len(prompts) <= 5):
            raise ValueError(f"prompts must contain between 3 and 5 items; received {len(prompts)}")
        if prompt_embeddings.shape[0] != len(prompts):
            raise ValueError(
                f"prompt_embeddings count {prompt_embeddings.shape[0]} does not match prompts count {len(prompts)}"
            )

        # L2-normalize each prompt independently
        norms = np.linalg.norm(prompt_embeddings, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized_prompts = prompt_embeddings / norms

        # Arithmetic mean centroid c
        centroid = normalized_prompts.mean(axis=0).astype(np.float32)
        centroid_norm = float(np.linalg.norm(centroid))
        if not np.isfinite(centroid_norm) or centroid_norm <= CENTROID_NORM_EPSILON:
            raise ValueError("Prototype prompts produced a degenerate zero or non-finite centroid")

        direction = (centroid / centroid_norm).astype(np.float32)
        return cls(
            values=direction,
            dimension=len(direction),
            model_identity=model_identity,
            query_type="prototype",
            raw_norm=centroid_norm,
            concept=concept,
            prompts=tuple(prompts),
            centroid_norm=centroid_norm,
        )


@dataclass(frozen=True, slots=True)
class SemanticAxisVector(QueryVector):
    """Specialized QueryVector constructed from contrasting positive and negative prompt ensembles."""

    positive_prompts: tuple[str, ...] = ()
    negative_prompts: tuple[str, ...] = ()

    @classmethod
    def build(
        cls,
        positive_prompts: Sequence[str],
        negative_prompts: Sequence[str],
        positive_embeddings: np.ndarray,
        negative_embeddings: np.ndarray,
        *,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> SemanticAxisVector:
        """Build a SemanticAxisVector following ADR-0005 contrast arithmetic."""
        if not (3 <= len(positive_prompts) <= 5):
            raise ValueError("positive_prompts must contain between 3 and 5 items")
        if len(positive_prompts) != len(negative_prompts):
            raise ValueError("positive_prompts and negative_prompts must have equal cardinality")

        # Normalize prompts
        pos_norms = np.linalg.norm(positive_embeddings, axis=1, keepdims=True)
        pos_norms[pos_norms == 0.0] = 1.0
        norm_pos = positive_embeddings / pos_norms

        neg_norms = np.linalg.norm(negative_embeddings, axis=1, keepdims=True)
        neg_norms[neg_norms == 0.0] = 1.0
        norm_neg = negative_embeddings / neg_norms

        # Pole centroids
        pos_centroid = _l2_normalize(norm_pos.mean(axis=0))
        neg_centroid = _l2_normalize(norm_neg.mean(axis=0))

        # Contrast direction
        contrast = pos_centroid - neg_centroid
        contrast_norm = float(np.linalg.norm(contrast))
        if not np.isfinite(contrast_norm) or contrast_norm <= CENTROID_NORM_EPSILON:
            raise ValueError("Semantic axis produced a degenerate zero or non-finite contrast vector")

        direction = (contrast / contrast_norm).astype(np.float32)
        return cls(
            values=direction,
            dimension=len(direction),
            model_identity=model_identity,
            query_type="semantic_axis",
            raw_norm=1.0,
            positive_prompts=tuple(positive_prompts),
            negative_prompts=tuple(negative_prompts),
        )


@dataclass(slots=True)
class WeightedQuery:
    """Associates a QueryVector with a weight and baseline dataset statistics."""

    query: QueryVector
    weight: float = 1.0
    mean_similarity: float = 0.0
    std_similarity: float = 1.0
    name: str = ""

    def adjusted_vector(self) -> np.ndarray:
        """Compute the z-score standardized vector contribution w * raw_norm / sigma * v."""
        std = self.std_similarity if self.std_similarity > 1e-7 else 1.0
        scale = (self.weight * self.query.raw_norm) / std
        return (scale * self.query.values).astype(np.float32)

    def offset(self) -> float:
        """Compute the z-score standardized scalar offset w * mu / sigma."""
        std = self.std_similarity if self.std_similarity > 1e-7 else 1.0
        return float((self.weight * self.mean_similarity) / std)


@dataclass(slots=True)
class ComposedQuery:
    """Composite container holding weighted prototype and semantic axis queries."""

    queries: list[WeightedQuery] = field(default_factory=list)

    def add_query(
        self,
        query: QueryVector,
        weight: float = 1.0,
        name: str = "",
    ) -> WeightedQuery:
        """Add a weighted query vector to the composition."""
        wq = WeightedQuery(query=query, weight=weight, name=name)
        self.queries.append(wq)
        return wq

    def all_prompts(self) -> list[str]:
        """Return all distinct prompt texts across all sub-queries in deterministic order."""
        prompts = []
        seen = set()
        for wq in self.queries:
            q = wq.query
            if isinstance(q, PrototypeVector):
                for p in q.prompts:
                    if p not in seen:
                        seen.add(p)
                        prompts.append(p)
            elif isinstance(q, SemanticAxisVector):
                for p in list(q.positive_prompts) + list(q.negative_prompts):
                    if p not in seen:
                        seen.add(p)
                        prompts.append(p)
        return prompts

    def compose(self) -> tuple[np.ndarray, float, float]:
        """Synthesize the composite search vector V, its norm, and total offset C.

        Returns (q, ||V||, C) where q is the L2-normalized direction for SQLite search.
        """
        if not self.queries:
            raise ValueError("ComposedQuery contains no queries")

        dim = self.queries[0].query.dimension
        total_vector = np.zeros(dim, dtype=np.float32)
        total_offset = 0.0

        for wq in self.queries:
            total_vector += wq.adjusted_vector()
            total_offset += wq.offset()

        norm_v = float(np.linalg.norm(total_vector))
        if not np.isfinite(norm_v) or norm_v <= CENTROID_NORM_EPSILON:
            raise ValueError("Composed query produced a degenerate zero vector")

        direction = (total_vector / norm_v).astype(np.float32)
        return direction, norm_v, total_offset


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Rich search result containing song identities, metadata, and z-index scores."""

    rank: int
    title: str | None
    song_title: str | None
    artist: str | None
    work_created_date: str | None
    score_id: str
    embedding_id: int
    score: float  # z-index
    component_scores: dict[str, float] = field(default_factory=dict)
    score_definition: str = SCORE_DEFINITION

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dictionary with complete context."""
        return {
            "rank": self.rank,
            "title": self.title,
            "song_title": self.song_title,
            "artist": self.artist,
            "work_created_date": self.work_created_date,
            "score_id": self.score_id,
            "embedding_id": self.embedding_id,
            "score": self.score,
            "component_scores": self.component_scores,
            "score_definition": self.score_definition,
        }


class RetrievalService:
    """Coordinates prompt encoding, vector composition, database search, and z-index ranking."""

    def __init__(
        self,
        repository: EmbeddingRepository,
        encoder: TextEncoder | None = None,
    ) -> None:
        self.repository = repository
        self.encoder = encoder or TextEncoder()

    def search_composed(
        self,
        composed_query: ComposedQuery,
        limit: int = 10,
        *,
        model_identity: EmbeddingModelIdentity | None = None,
    ) -> list[SearchResult]:
        """Execute a composed query via a single SQLite KNN search with exact z-index recovery."""
        if not composed_query.queries:
            return []

        # 1. Evaluate baseline dataset statistics for each component
        vectors = [wq.query for wq in composed_query.queries]
        if model_identity is None and vectors and vectors[0].model_identity is not None:
            model_identity = vectors[0].model_identity

        stats = self.repository.compute_baseline_statistics(vectors, model_identity=model_identity)
        for wq, (mu, sigma) in zip(composed_query.queries, stats, strict=True):
            wq.mean_similarity = mu
            wq.std_similarity = sigma

        # 2. Synthesize composite search vector and offset under ADR-0008
        direction, norm_v, total_offset = composed_query.compose()

        # 3. Single SQLite KNN search for the top limit items
        knn_results = self.repository.similarity_search(
            direction,
            limit=limit,
            model_identity=model_identity,
        )

        # 4. Recover exact z-index scores and individual component z-scores
        results: list[SearchResult] = []
        for rank, match in enumerate(knn_results, start=1):
            # Combined z-score formula: ||V|| * (1 - distance) - C
            combined_z = (norm_v * (1.0 - match.distance)) - total_offset

            # Component score breakdown
            raw_emb = match.embedding.raw_embedding
            norm_song = _l2_normalize(raw_emb)
            component_scores: dict[str, float] = {}

            for idx, wq in enumerate(composed_query.queries):
                col_name = wq.name or f"query_{idx}"
                raw_dot = float(np.dot(norm_song, wq.query.values))
                # For prototypes, raw score accounts for centroid norm
                raw_score = raw_dot * wq.query.raw_norm
                std = wq.std_similarity if wq.std_similarity > 1e-7 else 1.0
                comp_z = (raw_score - wq.mean_similarity) / std
                component_scores[col_name] = round(float(comp_z), 4)

            display_title = match.title or match.score_id
            results.append(
                SearchResult(
                    rank=rank,
                    title=display_title,
                    song_title=match.title,
                    artist=match.artist,
                    work_created_date=match.work_created_date,
                    score_id=match.score_id,
                    embedding_id=match.embedding_id,
                    score=round(float(combined_z), 4),
                    component_scores=component_scores,
                )
            )

        return results
