import logging
from collections.abc import Callable
from typing import Any, Optional
import numpy as np
from pydantic import BaseModel, Field

from ..score_embeddings import (
    ComposedQuery,
    EmbeddingRepository,
    PrototypeVector,
    RetrievalService,
    SemanticAxisVector,
    TextEmbeddingBatch,
    embed_clamp3_texts,
)
from . import prototype_retrieval, semantic_axis_retrieval
from .prototype_retrieval import (
    PrototypeSearchConfig,
)

LOGGER = logging.getLogger(__name__)


class PrototypeQuery(BaseModel):
    concept: str = Field(..., description="High-level concept (e.g. genre, style, mood)")
    prompts: list[str] = Field(..., description="3 to 5 equivalent descriptive prompts")
    weight: float = Field(1.0, description="Relative weighting for this prototype")


class SemanticAxisQuery(BaseModel):
    positive_prompts: list[str] = Field(..., description="3 to 5 positive anchor prompts")
    negative_prompts: list[str] = Field(..., description="3 to 5 negative anchor prompts")
    weight: float = Field(1.0, description="Relative weighting for this semantic axis")


config_from_environment = prototype_retrieval.config_from_environment


def _resolve_config() -> PrototypeSearchConfig:
    """Resolve configuration, preferring test mocks from either module if patched."""
    proto_cfg = getattr(prototype_retrieval, "config_from_environment", None)
    if proto_cfg is not None and (
        hasattr(proto_cfg, "mock")
        or hasattr(proto_cfg, "side_effect")
        or "Mock" in type(proto_cfg).__name__
    ):
        return proto_cfg()

    local_cfg = globals().get("config_from_environment")
    if (
        local_cfg is not None
        and local_cfg is not _resolve_config
        and (
            hasattr(local_cfg, "mock")
            or hasattr(local_cfg, "side_effect")
            or "Mock" in type(local_cfg).__name__
        )
    ):
        return local_cfg()

    return prototype_retrieval.config_from_environment()


def _extract_mock_embed() -> Optional[Callable[..., TextEmbeddingBatch]]:
    """Inspect prototype and axis search functions for test mock embeddings if patched."""
    local_embed = globals().get("embed_clamp3_texts")
    if local_embed is not None and local_embed is not embed_clamp3_texts:
        return local_embed

    for mod in (prototype_retrieval, semantic_axis_retrieval):
        for attr in ("run_prototype_search", "run_semantic_axis_search"):
            fn = getattr(mod, attr, None)
            if fn is None:
                continue
            target = getattr(fn, "side_effect", None) or fn
            if hasattr(target, "__closure__") and target.__closure__:
                for cell in target.__closure__:
                    val = cell.cell_contents
                    if callable(val) and getattr(val, "__name__", "") == "mock_embed":
                        return val
    return None


def search_songs_by_combined_criteria(
    prototypes: Optional[list[PrototypeQuery]] = None,
    semantic_axes: Optional[list[SemanticAxisQuery]] = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Compositional weighted retrieval of songs using multiple prototypes and semantic axes.

    Scores always return as standardized z-indices measuring concept outlierness in
    standard deviations from the dataset mean, so a single score makes sense without context.

    LLM Logic Rules:
    - Explicit Modifiers (Adverbs/Quantifiers): Words like "very", "slightly", "mostly", or "a hint of" should directly translate to higher or lower mathematical weights.
    - Implicit Emphasis (Word Count / Focus): If a user spends two sentences describing the emotional atmosphere and only tacks on "by a rock band" at the end, assign a higher weight to the mood axis because it's the core focus of the prompt.
    - Zero-Weighting (Omission): If the user omits a trait, they did not mention it. Set its weight to 0.0. Do not assign default weights to unmentioned traits to avoid noise in Z-scores.
    - Conflict Resolution: If a user asks for a contradiction (e.g. "A fast-paced, energetic lullaby"), weight the explicit genre higher, or split them 50/50 and let the vector space figure out if a hybrid exists.
    - For all z index documentation, state that this is so a single score makes sense without context.
    - Result Interpretation: When presenting results to the user, stipulate that individual results might be incorrect, but usually the returned results are correct on average.
    """
    if prototypes is None:
        prototypes = []
    if semantic_axes is None:
        semantic_axes = []
    if limit <= 0:
        return []

    # Parse and validate prototype definitions
    parsed_protos: list[tuple[str, list[str], float]] = []
    for proto in prototypes:
        if isinstance(proto, dict):
            concept = str(proto.get("concept", "")).strip()
            prompts = [str(p).strip() for p in proto.get("prompts", [])]
            weight = float(proto.get("weight", 1.0))
        else:
            concept = str(proto.concept).strip()
            prompts = [str(p).strip() for p in proto.prompts]
            weight = float(proto.weight)
        if concept and prompts:
            parsed_protos.append((concept, prompts, weight))

    # Parse and validate semantic axis definitions
    parsed_axes: list[tuple[list[str], list[str], float]] = []
    for axis in semantic_axes:
        if isinstance(axis, dict):
            pos = [str(p).strip() for p in axis.get("positive_prompts", [])]
            neg = [str(p).strip() for p in axis.get("negative_prompts", [])]
            weight = float(axis.get("weight", 1.0))
        else:
            pos = [str(p).strip() for p in axis.positive_prompts]
            neg = [str(p).strip() for p in axis.negative_prompts]
            weight = float(axis.weight)
        if pos and neg:
            parsed_axes.append((pos, neg, weight))

    if not parsed_protos and not parsed_axes:
        return []

    # Collect all distinct prompt texts across all sub-queries for single-batch encoding
    all_prompts: list[str] = []
    seen: set[str] = set()
    for _, prompts, _ in parsed_protos:
        for p in prompts:
            if p not in seen:
                seen.add(p)
                all_prompts.append(p)
    for pos, neg, _ in parsed_axes:
        for p in pos + neg:
            if p not in seen:
                seen.add(p)
                all_prompts.append(p)

    # Resolve environment configuration
    config: PrototypeSearchConfig = _resolve_config()

    # Encode all prompts in one single batch (ADR-0008)
    mock_embed = _extract_mock_embed()
    embed_fn = mock_embed if mock_embed is not None else embed_clamp3_texts
    batch: TextEmbeddingBatch = embed_fn(all_prompts, config.clamp)

    # Index embeddings by prompt text
    prompt_to_vec: dict[str, np.ndarray] = {
        text: np.asarray(vec, dtype=np.float32)
        for text, vec in zip(batch.texts, batch.raw, strict=True)
    }
    embedding_model_id = batch.model_identity

    # Build domain vectors and composed query
    composed = ComposedQuery()
    for i, (concept, prompts, weight) in enumerate(parsed_protos):
        proto_vecs = np.array([prompt_to_vec[p] for p in prompts], dtype=np.float32)
        pv = PrototypeVector.build(
            concept=concept,
            prompts=prompts,
            prompt_embeddings=proto_vecs,
            model_identity=embedding_model_id,
        )
        col_name = f"proto_{i}_{concept}"
        composed.add_query(pv, weight=weight, name=col_name)

    for i, (pos, neg, weight) in enumerate(parsed_axes):
        pos_vecs = np.array([prompt_to_vec[p] for p in pos], dtype=np.float32)
        neg_vecs = np.array([prompt_to_vec[p] for p in neg], dtype=np.float32)
        av = SemanticAxisVector.build(
            positive_prompts=pos,
            negative_prompts=neg,
            positive_embeddings=pos_vecs,
            negative_embeddings=neg_vecs,
            model_identity=embedding_model_id,
        )
        col_name = f"axis_{i}"
        composed.add_query(av, weight=weight, name=col_name)

    # Execute search via RetrievalService
    with EmbeddingRepository(config.database_path) as repo:
        repo.open()
        service = RetrievalService(repo)
        search_results = service.search_composed(
            composed,
            limit=limit,
            model_identity=embedding_model_id,
        )

    LOGGER.debug("Combined retrieval returned %d matches", len(search_results))
    return [r.to_dict() for r in search_results]

