"""Unit and mathematical verification for unified vector domain and ADR-0008 retrieval."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from encoding_music_mcp.tools.score_embeddings import (
    ClampModelIdentity,
    ComposedQuery,
    EmbeddingRecord,
    EmbeddingRepository,
    PrototypeVector,
    QueryVector,
    RetrievalService,
    SemanticAxisVector,
    TextEmbeddingBatch,
    WeightedQuery,
)
from encoding_music_mcp.tools.combined_retrieval import (
    PrototypeQuery,
    SemanticAxisQuery,
    search_songs_by_combined_criteria,
)


def _unit_vector(dim: int = 768, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def test_query_vector_validation() -> None:
    """QueryVector validates dimension, non-emptiness, and finite values."""
    v = _unit_vector(768)
    qv = QueryVector(values=v, dimension=768)
    assert qv.dimension == 768
    assert qv.raw_norm == 1.0

    # Mismatched dimension
    with pytest.raises((ValueError, Exception), match="expected .512"):
        QueryVector(values=v, dimension=512)

    # Non-finite values
    bad_v = v.copy()
    bad_v[0] = np.nan
    with pytest.raises((ValueError, Exception)):
        QueryVector(values=bad_v, dimension=768)


def test_prototype_vector_builder() -> None:
    """PrototypeVector builds normalized direction and retains centroid norm."""
    dim = 768
    prompts = ["prompt 1", "prompt 2", "prompt 3"]
    raw_prompts = np.array([_unit_vector(dim, i) for i in range(3)], dtype=np.float32)

    pv = PrototypeVector.build("Chamber Music", prompts, raw_prompts)
    assert pv.concept == "Chamber Music"
    assert len(pv.prompts) == 3
    assert pv.query_type == "prototype"
    assert 0.0 < pv.raw_norm <= 1.0
    assert np.isclose(np.linalg.norm(pv.values), 1.0, atol=1e-5)

    # Invalid prompt counts
    with pytest.raises(ValueError, match="between 3 and 5"):
        PrototypeVector.build("Test", ["1", "2"], raw_prompts[:2])


def test_semantic_axis_vector_builder() -> None:
    """SemanticAxisVector calculates pole centroids and unit contrast direction."""
    dim = 768
    pos_prompts = ["tense 1", "tense 2", "tense 3"]
    neg_prompts = ["calm 1", "calm 2", "calm 3"]
    pos_emb = np.array([_unit_vector(dim, i) for i in range(3)], dtype=np.float32)
    neg_emb = np.array([_unit_vector(dim, i + 10) for i in range(3)], dtype=np.float32)

    av = SemanticAxisVector.build(pos_prompts, neg_prompts, pos_emb, neg_emb)
    assert len(av.positive_prompts) == 3
    assert len(av.negative_prompts) == 3
    assert av.query_type == "semantic_axis"
    assert np.isclose(np.linalg.norm(av.values), 1.0, atol=1e-5)


def test_weighted_query_adjustments() -> None:
    """WeightedQuery applies z-score scale and offset factors correctly."""
    v = _unit_vector(768)
    qv = QueryVector(values=v, dimension=768, raw_norm=0.8)
    wq = WeightedQuery(query=qv, weight=2.0, mean_similarity=0.25, std_similarity=0.05)

    # adjusted_vector = w * raw_norm / sigma * v = 2.0 * 0.8 / 0.05 * v = 32.0 * v
    adj = wq.adjusted_vector()
    assert np.allclose(adj, 32.0 * v, atol=1e-5)

    # offset = w * mu / sigma = 2.0 * 0.25 / 0.05 = 10.0
    assert np.isclose(wq.offset(), 10.0, atol=1e-5)


def test_composed_query_mathematical_equivalence() -> None:
    """Mathematical linearity proof: single synthesized vector exactly reproduces sum of z-scores."""
    dim = 128
    num_songs = 50
    rng = np.random.default_rng(42)

    # Synthetic corpus of normalized song embeddings
    corpus_raw = rng.standard_normal((num_songs, dim)).astype(np.float32)
    corpus = corpus_raw / np.linalg.norm(corpus_raw, axis=1, keepdims=True)

    # Sub-query 1: Prototype (with raw_norm < 1.0)
    p1_dir = _unit_vector(dim, 100)
    p1_norm = 0.75
    q1 = QueryVector(values=p1_dir, dimension=dim, raw_norm=p1_norm, query_type="prototype")

    # Sub-query 2: Semantic Axis (raw_norm = 1.0)
    a1_dir = _unit_vector(dim, 200)
    q2 = QueryVector(values=a1_dir, dimension=dim, raw_norm=1.0, query_type="semantic_axis")

    # Sub-query 3: Prototype 2
    p2_dir = _unit_vector(dim, 300)
    p2_norm = 0.85
    q3 = QueryVector(values=p2_dir, dimension=dim, raw_norm=p2_norm, query_type="prototype")

    # Compute baseline distribution over corpus for each query
    # raw similarity = (x . v) * raw_norm
    raw_sims_1 = np.dot(corpus, q1.values) * q1.raw_norm
    mu_1, std_1 = float(np.mean(raw_sims_1)), float(np.std(raw_sims_1))

    raw_sims_2 = np.dot(corpus, q2.values) * q2.raw_norm
    mu_2, std_2 = float(np.mean(raw_sims_2)), float(np.std(raw_sims_2))

    raw_sims_3 = np.dot(corpus, q3.values) * q3.raw_norm
    mu_3, std_3 = float(np.mean(raw_sims_3)), float(np.std(raw_sims_3))

    w1, w2, w3 = 0.5, 0.3, 0.2

    # Theoretical sum of z-scores for each song
    z1 = (raw_sims_1 - mu_1) / std_1
    z2 = (raw_sims_2 - mu_2) / std_2
    z3 = (raw_sims_3 - mu_3) / std_3
    expected_combined_z = w1 * z1 + w2 * z2 + w3 * z3

    # Composed query synthesis
    composed = ComposedQuery()
    composed.add_query(q1, weight=w1)
    composed.queries[0].mean_similarity = mu_1
    composed.queries[0].std_similarity = std_1

    composed.add_query(q2, weight=w2)
    composed.queries[1].mean_similarity = mu_2
    composed.queries[1].std_similarity = std_2

    composed.add_query(q3, weight=w3)
    composed.queries[2].mean_similarity = mu_3
    composed.queries[2].std_similarity = std_3

    direction, norm_v, total_offset = composed.compose()

    # Single dot product score for each song: (x . direction) * norm_v - total_offset
    # Since cosine distance d = 1 - (x . direction), score = norm_v * (1 - d) - total_offset
    dot_products = np.dot(corpus, direction)
    composed_scores = (norm_v * dot_products) - total_offset

    # Assert exact numerical equivalence across all songs
    assert np.allclose(composed_scores, expected_combined_z, atol=1e-5), (
        f"Max diff: {np.max(np.abs(composed_scores - expected_combined_z))}"
    )


def test_repository_baseline_statistics(tmp_path: Path) -> None:
    """EmbeddingRepository.compute_baseline_statistics evaluates mean and std across corpus."""
    db_path = tmp_path / "test_stats.sqlite3"
    commit = "c" * 40
    revision = "rev1"
    weight_sha = "d" * 64
    dim = 768

    records = []
    with EmbeddingRepository(db_path) as repo:
        repo.open()
        for i in range(25):
            v = _unit_vector(dim, seed=i)
            rec = EmbeddingRecord(
                score_id=f"score_{i}",
                source_path=f"score_{i}.mei",
                source_sha256=f"sha_{i}",
                processing_fingerprint="fp",
                validation={"status": "PASS"},
                model_commit=commit,
                model_revision=revision,
                model_weight_sha256=weight_sha,
                raw_embedding=v,
                normalized_embedding=v,
                title=f"Song {i}",
                artist="Composer",
                work_created_date="1900",
            )
            repo.upsert(rec)
            records.append(rec)

        qv1 = QueryVector(values=_unit_vector(dim, 100), dimension=dim, raw_norm=0.7)
        qv2 = QueryVector(values=_unit_vector(dim, 200), dimension=dim, raw_norm=1.0)

        stats = repo.compute_baseline_statistics([qv1, qv2])
        assert len(stats) == 2

        # Verify against manual calculation
        all_vecs = np.vstack([r.raw_embedding for r in records])
        all_norm = all_vecs / np.linalg.norm(all_vecs, axis=1, keepdims=True)

        exp_dots_1 = np.dot(all_norm, qv1.values) * qv1.raw_norm
        exp_mu_1 = float(np.mean(exp_dots_1))
        exp_sigma_1 = float(np.std(exp_dots_1))

        assert np.isclose(stats[0][0], exp_mu_1, atol=1e-4)
        assert np.isclose(stats[0][1], exp_sigma_1, atol=1e-4)


def test_retrieval_service_e2e(tmp_path: Path) -> None:
    """RetrievalService executes single KNN query and returns rich SearchResults."""
    db_path = tmp_path / "retrieval_e2e.sqlite3"
    commit = "c" * 40
    revision = "rev1"
    weight_sha = "d" * 64
    dim = 768

    with EmbeddingRepository(db_path) as repo:
        repo.open()
        for i in range(15):
            v = _unit_vector(dim, seed=i)
            repo.upsert(
                EmbeddingRecord(
                    score_id=f"score_{i}",
                    source_path=f"score_{i}.mei",
                    source_sha256=f"sha_{i}",
                    processing_fingerprint="fp",
                    validation={"status": "PASS"},
                    model_commit=commit,
                    model_revision=revision,
                    model_weight_sha256=weight_sha,
                    raw_embedding=v,
                    normalized_embedding=v,
                    title=f"Song Title {i}",
                    artist=f"Artist {i % 3}",
                    work_created_date="1920",
                )
            )

        qv = QueryVector(values=_unit_vector(dim, 999), dimension=dim)
        composed = ComposedQuery()
        composed.add_query(qv, weight=1.0, name="concept_test")

        service = RetrievalService(repo)
        results = service.search_composed(composed, limit=5)

        assert len(results) == 5
        # Verify ordering is descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Verify SearchResult fields
        r0 = results[0]
        assert r0.rank == 1
        assert r0.song_title is not None
        assert "concept_test" in r0.component_scores
        d = r0.to_dict()
        assert d["rank"] == 1
        assert "score_definition" in d
        assert "outlierness" in d["score_definition"].lower()


def test_search_songs_by_combined_criteria_rich_list(tmp_path: Path) -> None:
    """search_songs_by_combined_criteria returns Option 1 rich list format."""
    db_path = tmp_path / "combined_tool.sqlite3"
    commit = "c" * 40
    revision = "rev1"
    weight_sha = "d" * 64
    dim = 768

    with EmbeddingRepository(db_path) as repo:
        repo.open()
        for i in range(10):
            v = _unit_vector(dim, seed=i)
            repo.upsert(
                EmbeddingRecord(
                    score_id=f"score_{i}",
                    source_path=f"score_{i}.mei",
                    source_sha256=f"sha_{i}",
                    processing_fingerprint="fp",
                    validation={"status": "PASS"},
                    model_commit=commit,
                    model_revision=revision,
                    model_weight_sha256=weight_sha,
                    raw_embedding=v,
                    normalized_embedding=v,
                    title=f"Piece {i}",
                    artist="Béla Bartók" if i < 5 else "J.S. Bach",
                    work_created_date="1926",
                )
            )

    def mock_embed(texts, config, **kwargs):
        raw = np.array([_unit_vector(dim, seed=hash(t) % 10000) for t in texts], dtype=np.float32)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return TextEmbeddingBatch(
            texts=tuple(texts),
            stems=tuple(f"text_{i:06d}" for i in range(len(texts))),
            raw=raw,
            normalized=raw / norms,
            model_identity=ClampModelIdentity(commit, revision, weight_sha, dim),
        )

    from unittest.mock import patch
    import os
    import sys
    from encoding_music_mcp.tools.prototype_retrieval import PrototypeSearchConfig
    from encoding_music_mcp.tools.score_embeddings import ClampRuntimeConfig

    def mock_config():
        return PrototypeSearchConfig(
            database_path=db_path,
            clamp=ClampRuntimeConfig(
                python_executable=Path(sys.executable),
                cache_dir=tmp_path / "cache",
                commit=commit,
                model_revision=revision,
                weight_sha256=weight_sha,
                expected_dimension=dim,
            ),
        )

    with patch.dict(os.environ, {"ENCODING_MUSIC_EMBEDDINGS_DATABASE": str(db_path)}), \
         patch("encoding_music_mcp.tools.combined_retrieval.config_from_environment", side_effect=mock_config), \
         patch("encoding_music_mcp.tools.combined_retrieval.embed_clamp3_texts", side_effect=mock_embed):

        protos = [
            PrototypeQuery(
                concept="Modernist",
                prompts=["modernist piece 1", "modernist piece 2", "modernist piece 3"],
                weight=0.7,
            )
        ]
        axes = [
            SemanticAxisQuery(
                positive_prompts=["tense 1", "tense 2", "tense 3"],
                negative_prompts=["calm 1", "calm 2", "calm 3"],
                weight=0.3,
            )
        ]

        results = search_songs_by_combined_criteria(protos, axes, limit=5)

        assert isinstance(results, list)
        assert len(results) == 5

        # Check all required keys for Option 1
        expected_keys = {
            "rank",
            "title",
            "song_title",
            "artist",
            "work_created_date",
            "score_id",
            "embedding_id",
            "score",
            "component_scores",
            "score_definition",
        }
        for item in results:
            assert isinstance(item, dict)
            assert expected_keys.issubset(item.keys())
            assert isinstance(item["rank"], int)
            assert isinstance(item["score"], float)
            assert isinstance(item["component_scores"], dict)
            assert "proto_0_Modernist" in item["component_scores"]
            assert "axis_0" in item["component_scores"]
            assert "outlierness" in item["score_definition"].lower()
