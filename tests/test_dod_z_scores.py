from pathlib import Path
import numpy as np

from encoding_music_mcp.tools import prototype_retrieval as retrieval
from encoding_music_mcp.tools.score_embeddings import (
    CatalogSimilarityResult,
    CountedCatalogSimilarityResult,
    TextEmbeddingBatch,
    ClampModelIdentity,
    ClampRuntimeConfig,
)
import sys

BAROQUE_PROMPTS = [
    "A piece of Baroque keyboard music.",
    "A contrapuntal composition featuring intricate voice leading.",
    "Music with multiple independent melodic lines typical of the 18th century."
]
MODERN_PROMPTS = [
    "A 20th-century modern piano piece.",
    "A simple, pedagogical piano composition for beginners.",
    "Music with a distinctly modern, sparse, or folk-influenced style."
]
RENAISSANCE_PROMPTS = [
    "A piece of Renaissance choral music or madrigal.",
    "Early music featuring vocal polyphony.",
    "A composition characteristic of the 16th-century English tradition."
]

def _config(tmp_path: Path, dimension: int = 3) -> retrieval.PrototypeSearchConfig:
    return retrieval.PrototypeSearchConfig(
        database_path=tmp_path / "catalog.sqlite3",
        clamp=ClampRuntimeConfig(
            python_executable=Path(sys.executable),
            cache_dir=tmp_path / "cache",
            commit="c" * 40,
            model_revision="revision-a",
            weight_sha256="d" * 64,
            expected_dimension=dimension,
        ),
    )

def _identity(dimension: int = 3) -> ClampModelIdentity:
    return ClampModelIdentity("c" * 40, "revision-a", "d" * 64, dimension)

def _batch(raw: object, texts: tuple[str, ...]) -> TextEmbeddingBatch:
    array = np.asarray(raw)
    return TextEmbeddingBatch(
        texts=texts,
        stems=tuple(f"text_{index:06d}" for index in range(len(array))),
        raw=array,
        normalized=np.zeros_like(array, dtype=float),
        model_identity=_identity(array.shape[1]),
    )

class _FakeRepository:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def counted_catalog_similarity_search(self, query, *, limit, model_identity):
        # We need to return mock results.
        matches = []
        for i in range(min(10, limit)):
            matches.append(
                CatalogSimilarityResult(
                    embedding_id=i,
                    score_id=f"score-{i}",
                    title=f"Song {i}",
                    artist="Composer",
                    work_created_date="1907",
                    distance=0.1 * i,  # distance increases, so raw score decreases
                )
            )
        return CountedCatalogSimilarityResult(
            matches=tuple(matches),
            eligible_count=10,
            excluded_count=0,
        )

def test_dod_z_scores(tmp_path: Path):
    raw = np.tile([1.0, 0.0, 0.0], (3, 1))

    # Mock embed_texts
    def embed_texts_mock(texts, config, **kwargs):
        return _batch(raw, texts=tuple(texts))

    # Modern - top 5 z-indexes match top 5 raw scores
    top_k = 5
    raw_results = retrieval.run_prototype_search(
        "Modern",
        MODERN_PROMPTS,
        config=_config(tmp_path, 3),
        top_k=top_k,
        embed_texts=embed_texts_mock,
        repository_factory=lambda path: _FakeRepository(path),
    ).to_dict()

    # Call the modified function which computes z-scores
    # To do this cleanly, we need to mock config_from_environment, or pass config directly.
    # The tool search_songs_by_prototype doesn't take config directly.
    # Let's monkeypatch config_from_environment
    import encoding_music_mcp.tools.prototype_retrieval as pr
    original_config_from_environment = pr.config_from_environment
    pr.config_from_environment = lambda: _config(tmp_path, 3)

    original_run_prototype_search = pr.run_prototype_search
    def mock_run_prototype_search(*args, **kwargs):
        kwargs["embed_texts"] = embed_texts_mock
        kwargs["repository_factory"] = lambda path: _FakeRepository(path)
        return original_run_prototype_search(*args, **kwargs)
    
    pr.run_prototype_search = mock_run_prototype_search

    try:
        # z-score call
        z_score_results = pr.search_songs_by_prototype("Modern", MODERN_PROMPTS, top_k=top_k, return_z_score=True)
        
        raw_titles = [r["song_title"] if r["song_title"] else r["score_id"] for r in raw_results["results"]]
        z_score_titles = list(z_score_results.keys())

        assert raw_titles == z_score_titles, f"Top {top_k} z-score titles do not match raw score titles"

        # Baroque raw scores are very high
        # We need the distance for Baroque to be small. 
        # _FakeRepository returns distance=0.0 for the first item, so score = centroid_norm * 1.0 = 1.0.
        baroque_results = pr.search_songs_by_prototype("Baroque", BAROQUE_PROMPTS, top_k=1, return_z_score=False)
        top_baroque_score = baroque_results["results"][0]["score"]
        assert top_baroque_score > 0.6, f"Expected very high score for Baroque, got {top_baroque_score}"
    finally:
        pr.config_from_environment = original_config_from_environment
        pr.run_prototype_search = original_run_prototype_search
