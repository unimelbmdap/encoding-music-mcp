import pytest
from unittest.mock import patch
import numpy as np
import os
import sys
from pathlib import Path
import sqlite3

from encoding_music_mcp.tools.combined_retrieval import (
    search_songs_by_combined_criteria, PrototypeQuery, SemanticAxisQuery
)
from encoding_music_mcp.score_embeddings import (
    ClampModelIdentity, EmbeddingRecord, EmbeddingRepository, TextEmbeddingBatch
)
from encoding_music_mcp.tools import prototype_retrieval, semantic_axis_retrieval

def _mock_text_batch(texts, commit, revision, weight_sha256, dimension, get_vector_for_text):
    raw = np.array([get_vector_for_text(t) for t in texts], dtype=np.float32)
    # add small epsilon to avoid divide by zero if vector is all zeros
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = raw / norms
    return TextEmbeddingBatch(
        texts=tuple(texts),
        stems=tuple(f"text_{i:06d}" for i in range(len(texts))),
        raw=raw,
        normalized=normalized,
        model_identity=ClampModelIdentity(commit, revision, weight_sha256, dimension)
    )

def _random_cluster_vector(start_idx, end_idx):
    vector = np.random.randn(768).astype(np.float32) * 0.1
    if start_idx is not None and end_idx is not None:
        vector[start_idx:end_idx] += 2.0
    return vector

def test_weighted_combination_mocked(tmp_path):
    db_path = tmp_path / "mock.sqlite3"
    commit = "c" * 40
    revision = "revision-a"
    weight_sha256 = "d" * 64
    
    with EmbeddingRepository(db_path) as repo:
        repo.open()
        # Bach: 0-256
        for i in range(10):
            v = _random_cluster_vector(0, 256)
            repo.upsert(EmbeddingRecord(
                score_id=f"bach_{i}", source_path=f"bach_{i}.mei", source_sha256=f"sha_bach_{i}",
                processing_fingerprint="fp", validation={"status": "PASS"},
                model_commit=commit, model_revision=revision, model_weight_sha256=weight_sha256,
                raw_embedding=v, normalized_embedding=v / np.linalg.norm(v),
                title=f"Bach {i}", artist="Bach", work_created_date="1700"
            ))
        
        # Bartok: 256-512
        for i in range(19):
            v = _random_cluster_vector(256, 512)
            repo.upsert(EmbeddingRecord(
                score_id=f"bartok_{i}", source_path=f"bartok_{i}.mei", source_sha256=f"sha_bartok_{i}",
                processing_fingerprint="fp", validation={"status": "PASS"},
                model_commit=commit, model_revision=revision, model_weight_sha256=weight_sha256,
                raw_embedding=v, normalized_embedding=v / np.linalg.norm(v),
                title=f"Bartok {i}", artist="Bartok", work_created_date="1900"
            ))
            
        # Morley: 512-768
        for i in range(10):
            v = _random_cluster_vector(512, 768)
            repo.upsert(EmbeddingRecord(
                score_id=f"morley_{i}", source_path=f"morley_{i}.mei", source_sha256=f"sha_morley_{i}",
                processing_fingerprint="fp", validation={"status": "PASS"},
                model_commit=commit, model_revision=revision, model_weight_sha256=weight_sha256,
                raw_embedding=v, normalized_embedding=v / np.linalg.norm(v),
                title=f"Morley {i}", artist="Morley", work_created_date="1500"
            ))

    def get_text_vector(text):
        t = text.lower()
        if "tense" in t or "modernist" in t:
            return _random_cluster_vector(256, 512)
        elif "peaceful" in t:
            v = np.random.randn(768).astype(np.float32) * 0.1
            v[0:256] += 2.0
            v[512:768] += 2.0
            return v
        return np.random.randn(768).astype(np.float32)

    def mock_embed(texts, config, **kwargs):
        return _mock_text_batch(texts, config.commit, config.model_revision, config.weight_sha256, config.expected_dimension, get_text_vector)

    env = {
        "ENCODING_MUSIC_EMBEDDINGS_DATABASE": str(db_path),
        "ENCODING_MUSIC_CLAMP_PYTHON": sys.executable,
    }

    prototype_retrieval.close_prototype_retrieval_resources()
    semantic_axis_retrieval.close_semantic_axis_retrieval_resources()
    
    original_run_proto = prototype_retrieval.run_prototype_search
    original_run_axis = semantic_axis_retrieval.run_semantic_axis_search
    def mock_run_proto(*a, **k):
        k["embed_texts"] = mock_embed
        return original_run_proto(*a, **k)
    def mock_run_axis(*a, **k):
        k["embed_texts"] = mock_embed
        return original_run_axis(*a, **k)

    from encoding_music_mcp.tools.prototype_retrieval import PrototypeSearchConfig
    from encoding_music_mcp.score_embeddings import ClampRuntimeConfig
    def mock_config():
        return PrototypeSearchConfig(
            database_path=db_path,
            clamp=ClampRuntimeConfig(
                python_executable=Path(sys.executable),
                cache_dir=tmp_path / "cache",
                commit=commit,
                model_revision=revision,
                weight_sha256=weight_sha256,
                expected_dimension=768,
            )
        )

    with patch.dict(os.environ, env), \
         patch("encoding_music_mcp.tools.prototype_retrieval.run_prototype_search", side_effect=mock_run_proto), \
         patch("encoding_music_mcp.tools.semantic_axis_retrieval.run_semantic_axis_search", side_effect=mock_run_axis), \
         patch("encoding_music_mcp.tools.prototype_retrieval.config_from_environment", side_effect=mock_config), \
         patch("encoding_music_mcp.tools.semantic_axis_retrieval.config_from_environment", side_effect=mock_config):
        
        prototypes = [PrototypeQuery(concept="20th-Century Modernist", prompts=["modernist 1", "modernist 2", "modernist 3"], weight=0.6)]
        axes = [SemanticAxisQuery(positive_prompts=["tense 1", "tense 2", "tense 3"], negative_prompts=["peaceful 1", "peaceful 2", "peaceful 3"], weight=0.4)]
        
        results = search_songs_by_combined_criteria(prototypes, axes, limit=19)
        
        assert len(results) == 19
        for res in results:
            assert "Bartok" in res["title"]

    prototype_retrieval.close_prototype_retrieval_resources()
    semantic_axis_retrieval.close_semantic_axis_retrieval_resources()

def test_real_embeddings_combination(tmp_path):
    db_path = Path("src/encoding_music_mcp/resources/score-embeddings.sqlite").resolve()
    if not db_path.is_file():
        db_path = Path("src/encoding_music_mcp/resources/score-embeddings.sqlite3").resolve()
    if not db_path.is_file():
        db_path = Path("src/encoding_music_mcp/score_embeddings/colab-verification/score-embeddings.sqlite3").resolve()
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    bartok_vectors = []
    other_vectors = []
    
    cur.execute("SELECT artist, raw_embedding FROM score_embeddings")
    for row in cur.fetchall():
        artist, raw_bytes = row
        v = np.frombuffer(raw_bytes, dtype=np.float32)
        if artist and ("Bartók" in artist or "Bartok" in artist):
            bartok_vectors.append(v)
        else:
            other_vectors.append(v)
    conn.close()
    
    bartok_mean = np.mean(bartok_vectors, axis=0) if bartok_vectors else np.zeros(768, dtype=np.float32)
    other_mean = np.mean(other_vectors, axis=0) if other_vectors else np.zeros(768, dtype=np.float32)
    
    def get_text_vector(text):
        t = text.lower()
        if "tense" in t or "modernist" in t:
            return bartok_mean.copy()
        elif "peaceful" in t:
            return other_mean.copy()
        return np.random.randn(768).astype(np.float32)

    def mock_embed(texts, config, **kwargs):
        return _mock_text_batch(texts, config.commit, config.model_revision, config.weight_sha256, config.expected_dimension, get_text_vector)

    env = {
        "ENCODING_MUSIC_EMBEDDINGS_DATABASE": str(db_path),
        "ENCODING_MUSIC_CLAMP_PYTHON": sys.executable,
    }

    prototype_retrieval.close_prototype_retrieval_resources()
    semantic_axis_retrieval.close_semantic_axis_retrieval_resources()
    
    original_run_proto = prototype_retrieval.run_prototype_search
    original_run_axis = semantic_axis_retrieval.run_semantic_axis_search
    def mock_run_proto(*a, **k):
        k["embed_texts"] = mock_embed
        return original_run_proto(*a, **k)
    def mock_run_axis(*a, **k):
        k["embed_texts"] = mock_embed
        return original_run_axis(*a, **k)

    with patch.dict(os.environ, env), \
         patch("encoding_music_mcp.tools.prototype_retrieval.run_prototype_search", side_effect=mock_run_proto), \
         patch("encoding_music_mcp.tools.semantic_axis_retrieval.run_semantic_axis_search", side_effect=mock_run_axis):
        
        prototypes = [PrototypeQuery(concept="20th-Century Modernist", prompts=["modernist 1", "modernist 2", "modernist 3"], weight=0.6)]
        axes = [SemanticAxisQuery(positive_prompts=["tense 1", "tense 2", "tense 3"], negative_prompts=["peaceful 1", "peaceful 2", "peaceful 3"], weight=0.4)]
        
        results = search_songs_by_combined_criteria(prototypes, axes, limit=18)
        
        assert len(results) > 0
        for res in results:
            assert "Mikrokosmos" in res["title"]

    prototype_retrieval.close_prototype_retrieval_resources()
    semantic_axis_retrieval.close_semantic_axis_retrieval_resources()
