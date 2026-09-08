import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel

from .prototype_retrieval import search_songs_by_prototype
from .semantic_axis_retrieval import search_songs_by_semantic_axis

LOGGER = logging.getLogger(__name__)


class PrototypeQuery(BaseModel):
    concept: str
    prompts: list[str]
    weight: float


class SemanticAxisQuery(BaseModel):
    positive_prompts: list[str]
    negative_prompts: list[str]
    weight: float


def search_songs_by_combined_criteria(
    prototypes: Optional[List[PrototypeQuery]] = None,
    semantic_axes: Optional[List[SemanticAxisQuery]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Compositional weighted retrieval of songs using multiple prototypes and semantic axes.

    LLM Logic Rules:
    - Explicit Modifiers (Adverbs/Quantifiers): Words like "very", "slightly", "mostly", or "a hint of" should directly translate to higher or lower mathematical weights.
    - Implicit Emphasis (Word Count / Focus): If a user spends two sentences describing the emotional atmosphere and only tacks on "by a rock band" at the end, assign a higher weight to the mood axis because it's the core focus of the prompt.
    - Zero-Weighting (Omission): If the user omits a trait, they did not mention it. Set its weight to 0.0. Do not assign default weights to unmentioned traits to avoid noise in Z-scores.
    - Conflict Resolution: If a user asks for a contradiction (e.g. "A fast-paced, energetic lullaby"), weight the explicit genre higher, or split them 50/50 and let the vector space figure out if a hybrid exists.
    - For all z index documentation, state that this is so a single score makes sense without context.
    """
    if prototypes is None:
        prototypes = []
    if semantic_axes is None:
        semantic_axes = []

    all_scores = {}
    weights = {}

    # Collect prototype results
    for i, proto in enumerate(prototypes):
        if isinstance(proto, dict):
            concept = proto.get("concept", "")
            prompts = proto.get("prompts", [])
            weight = float(proto.get("weight", 1.0))
        else:
            concept = proto.concept
            prompts = proto.prompts
            weight = float(proto.weight)

        col_name = f"proto_{i}_{concept}"
        scores = search_songs_by_prototype(
            concept=concept,
            prompts=prompts,
            top_k=100000,
            return_z_score=True,
        )
        all_scores[col_name] = scores
        weights[col_name] = weight

    # Collect semantic axis results
    for i, axis in enumerate(semantic_axes):
        if isinstance(axis, dict):
            pos = axis.get("positive_prompts", [])
            neg = axis.get("negative_prompts", [])
            weight = float(axis.get("weight", 1.0))
        else:
            pos = axis.positive_prompts
            neg = axis.negative_prompts
            weight = float(axis.weight)

        col_name = f"axis_{i}"
        scores = search_songs_by_semantic_axis(
            positive_prompts=pos,
            negative_prompts=neg,
            limit=100000,
            return_z_score=True,
        )
        all_scores[col_name] = scores
        weights[col_name] = weight

    if not all_scores:
        return []

    # Combine into DataFrame
    df = pd.DataFrame(all_scores).fillna(0.0)
    LOGGER.debug("Combined retrieval scores: %s", all_scores)
    LOGGER.debug("Combined retrieval dataframe: %s", df)

    # Weight series
    weight_series = pd.Series(weights)

    # Calculate combined score
    combined_scores = df.dot(weight_series)

    # Sort descending
    combined_scores = combined_scores.sort_values(ascending=False)

    # Take top limit
    top_results = combined_scores.head(limit)

    results = []
    for title, score in top_results.items():
        results.append({
            "title": str(title),
            "score": float(score),
        })

    return results
