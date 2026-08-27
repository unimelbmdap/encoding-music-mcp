"""Offline CLaMP-to-sqlite-vec integration for contrastive emotion search."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from encoding_music_mcp.score_embeddings import (
    ClampRuntimeConfig,
    EmbeddingRecord,
    EmbeddingRepository,
    embed_clamp3_texts,
)
from encoding_music_mcp.tools.emotion_retrieval import (
    EmotionSearchConfig,
    run_emotion_search,
)


def _unit(index: int) -> np.ndarray:
    vector = np.zeros(768, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _record(score_id: str, vector: np.ndarray, *, commit: str) -> EmbeddingRecord:
    return EmbeddingRecord(
        score_id=score_id,
        title=f"Title {score_id}",
        artist=f"Artist {score_id}",
        work_created_date="1900",
        source_path=f"/scores/{score_id}.mei",
        source_sha256=f"source-{score_id}",
        processing_fingerprint="processing-v1",
        validation={"status": "PASS"},
        model_commit=commit,
        model_revision="revision-a",
        model_weight_sha256="d" * 64,
        raw_embedding=vector.copy(),
        normalized_embedding=vector.copy(),
    )


def test_offline_contrast_search_uses_fake_clamp_output_and_exact_model_filter(
    tmp_path: Path,
):
    cache = tmp_path / "cache"
    code = cache / "source" / "code"
    code.mkdir(parents=True)
    (code / "extract_clamp3.py").write_text("# fake extractor\n", encoding="utf-8")
    database = tmp_path / "songs.sqlite3"
    compatible_commit = "c" * 40
    with EmbeddingRepository(database) as repository:
        near = repository.upsert(_record("happy-near", _unit(0), commit=compatible_commit))
        sad = repository.upsert(_record("sad", _unit(1), commit=compatible_commit))
        repository.upsert(_record("wrong-model", _unit(0), commit="e" * 40))

    config = EmotionSearchConfig(
        database_path=database,
        clamp=ClampRuntimeConfig(
            python_executable=Path(sys.executable),
            cache_dir=cache,
            commit=compatible_commit,
            model_revision="revision-a",
            weight_sha256="d" * 64,
        ),
    )
    calls: list[list[str]] = []

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        calls.append(command)
        input_dir = Path(command[2])
        output_dir = Path(command[3])
        assert (input_dir / "text_000000.txt").read_text() == "happy"
        assert (input_dir / "text_000001.txt").read_text() == "sad"
        np.save(output_dir / "text_000000.npy", _unit(0))
        np.save(output_dir / "text_000001.npy", _unit(1))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def embed_without_setup(texts, runtime, *, runner):
        return embed_clamp3_texts(
            texts, runtime, runner=runner, verify_setup=False
        )

    result = run_emotion_search(
        "happy",
        "sad",
        config=config,
        runner=runner,
        embed_texts=embed_without_setup,
    )

    assert len(calls) == 1
    assert [match.embedding_id for match in result.matches] == [near.id, sad.id]
    assert result.matches[0].score_id == "happy-near"
    assert result.matches[0].title == "Title happy-near"
    assert result.matches[0].artist == "Artist happy-near"
    assert result.matches[0].work_created_date == "1900"
    assert all(match.score_id != "wrong-model" for match in result.matches)
    assert not hasattr(result.matches[0], "vector")
