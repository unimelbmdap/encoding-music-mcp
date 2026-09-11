"""Offline CLaMP-to-sqlite-vec integration for semantic-axis search."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from encoding_music_mcp.tools.score_embeddings import (
    ClampRuntimeConfig,
    EmbeddingRecord,
    EmbeddingRepository,
    embed_clamp3_texts,
)
from encoding_music_mcp.tools.semantic_axis_retrieval import (
    SemanticAxisSearchConfig,
    run_semantic_axis_search,
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


def test_offline_semantic_axis_search_uses_prompt_ensembles_and_exact_model_filter(
    tmp_path: Path,
):
    cache = tmp_path / "cache"
    code = cache / "source" / "code"
    code.mkdir(parents=True)
    (code / "extract_clamp3.py").write_text("# fake extractor\n", encoding="utf-8")
    database = tmp_path / "songs.sqlite3"
    compatible_commit = "c" * 40
    expected_axis = (_unit(0) - _unit(1)) / np.sqrt(2.0)
    with EmbeddingRepository(database) as repository:
        near = repository.upsert(
            _record("positive-near", expected_axis, commit=compatible_commit)
        )
        negative = repository.upsert(
            _record("negative", _unit(1), commit=compatible_commit)
        )
        repository.upsert(
            _record("wrong-model", expected_axis, commit="e" * 40)
        )

    config = SemanticAxisSearchConfig(
        database_path=database,
        clamp=ClampRuntimeConfig(
            python_executable=Path(sys.executable),
            cache_dir=cache,
            commit=compatible_commit,
            model_revision="revision-a",
            weight_sha256="d" * 64,
        ),
    )
    positive = [
        "Music expressing a joyful and optimistic mood.",
        "Happy, energetic music with a cheerful emotional character.",
        "Happy, calm music with a warm and contented character.",
    ]
    negative_prompts = [
        "Music expressing a sorrowful and pessimistic mood.",
        "Sad, energetic music with a distressed emotional character.",
        "Sad, calm music with a melancholic and subdued character.",
    ]
    ordered = positive + negative_prompts
    calls: list[list[str]] = []

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        calls.append(command)
        input_dir = Path(command[2])
        output_dir = Path(command[3])
        for index, prompt in enumerate(ordered):
            assert (input_dir / f"text_{index:06d}.txt").read_text() == prompt
            vector = _unit(0) * float(3 - index) if index < 3 else _unit(1)
            np.save(output_dir / f"text_{index:06d}.npy", vector)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def embed_without_setup(texts, runtime, *, runner):
        return embed_clamp3_texts(
            texts, runtime, runner=runner, verify_setup=False
        )

    result = run_semantic_axis_search(
        positive,
        negative_prompts,
        config=config,
        runner=runner,
        embed_texts=embed_without_setup,
    )

    assert len(calls) == 1
    assert [match.embedding_id for match in result.matches] == [near.id, negative.id]
    assert result.positive_prompts == tuple(positive)
    assert result.negative_prompts == tuple(negative_prompts)
    assert result.matches[0].score_id == "positive-near"
    assert result.matches[0].title == "Title positive-near"
    assert result.matches[0].artist == "Artist positive-near"
    assert result.matches[0].work_created_date == "1900"
    assert all(match.score_id != "wrong-model" for match in result.matches)
    assert not hasattr(result.matches[0], "vector")
