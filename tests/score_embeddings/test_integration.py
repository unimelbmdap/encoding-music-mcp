"""Module-boundary tests for real MusicXML, subprocess, and sqlite-vec behavior."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from encoding_music_mcp.tools.score_embeddings.clamp_extractor import ClampRuntimeConfig
from encoding_music_mcp.tools.score_embeddings.pipeline import (
    PipelineConfig,
    PipelineError,
    query_similar,
    run_pipeline,
)
from encoding_music_mcp.tools.score_embeddings.storage import EmbeddingRepository

PROJECT_ROOT = Path(__file__).parents[2]
MEI_DIR = PROJECT_ROOT / "src" / "encoding_music_mcp" / "resources" / "mei_files"


def _write_script(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")


def _fake_runtime(
    tmp_path: Path, *, fail_extraction: bool = False
) -> ClampRuntimeConfig:
    checkout = tmp_path / "cache" / "source"
    _write_script(
        checkout / "preprocessing" / "abc" / "batch_xml2abc.py",
        """
        import sys
        from pathlib import Path

        source, destination = map(Path, sys.argv[1:3])
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.rglob("*.xml")):
            (destination / f"{path.stem}.abc").write_text(
                "X:1\\nK:C\\nC|\\n", encoding="utf-8"
            )
        """,
    )
    _write_script(
        checkout / "preprocessing" / "abc" / "batch_interleaved_abc.py",
        """
        import shutil
        import sys
        from pathlib import Path

        source, destination = map(Path, sys.argv[1:3])
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.rglob("*.abc")):
            shutil.copy2(path, destination / path.name)
        """,
    )
    extraction_source = (
        """
        import sys
        print("simulated extractor failure", file=sys.stderr)
        raise SystemExit(7)
        """
        if fail_extraction
        else """
        import sys
        from pathlib import Path
        import numpy as np

        source, destination = map(Path, sys.argv[1:3])
        destination.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(sorted(source.rglob("*.abc")), start=1):
            vector = np.zeros(768, dtype=np.float32)
            vector[0] = 1.0
            vector[index] = 0.25 * index
            np.save(destination / f"{path.stem}.npy", vector)
        """
    )
    _write_script(checkout / "code" / "extract_clamp3.py", extraction_source)
    return ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )


def test_bundled_mei_to_xml_subprocess_embeddings_database_and_similarity(
    tmp_path: Path,
):
    sources = [MEI_DIR / "Bach_BWV_0772.mei", MEI_DIR / "Bach_BWV_0773.mei"]
    database = tmp_path / "embeddings.sqlite3"

    result = run_pipeline(
        PipelineConfig(
            inputs=sources,
            output_dir=tmp_path / "runs",
            database_path=database,
            clamp=_fake_runtime(tmp_path),
            keep_intermediates=True,
            verify_clamp_setup=False,
        )
    )

    assert all(score.embedding_id is not None for score in result.scores)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [entry["conversion_status"] for entry in manifest["scores"]] == [
        "PASS",
        "PASS",
    ]
    assert [entry["title"] for entry in manifest["scores"]] == [
        "Invention No. 1 in C major",
        "Invention No. 2 in C minor",
    ]
    assert all(
        entry["artist"] == "Bach, Johann Sebastian" for entry in manifest["scores"]
    )
    assert all(entry["work_created_date"] is None for entry in manifest["scores"])
    xml_files = sorted(
        (result.manifest_path.parent / "intermediates" / "xml").glob("*")
    )
    assert xml_files and all(path.suffix == ".xml" for path in xml_files)
    assert not list((result.manifest_path.parent / "intermediates").rglob("*.mid"))

    with EmbeddingRepository(database) as repository:
        first_id = result.scores[0].embedding_id
        assert first_id is not None
        stored = repository.get(first_id)
        assert stored.dimension == 768
        assert stored.validation["status"] == "PASS"
        assert stored.title == "Invention No. 1 in C major"
        assert stored.artist == "Bach, Johann Sebastian"
        assert stored.work_created_date is None
        neighbors = repository.similarity_search_by_id(first_id, limit=1)
    assert neighbors[0].embedding.score_id == result.scores[1].score_id
    assert neighbors[0].embedding.title == "Invention No. 2 in C minor"

    queried = query_similar(database, score_id=result.scores[0].score_id, limit=1)
    assert queried[0].embedding.score_id == result.scores[1].score_id


def test_real_subprocess_failure_is_nonzero_manifested_and_cleaned(tmp_path: Path):
    source = MEI_DIR / "Bach_BWV_0772.mei"

    with pytest.raises(PipelineError, match="exit code 7"):
        run_pipeline(
            PipelineConfig(
                inputs=[source],
                output_dir=tmp_path / "runs",
                database_path=tmp_path / "embeddings.sqlite3",
                clamp=_fake_runtime(tmp_path, fail_extraction=True),
                keep_intermediates=False,
                verify_clamp_setup=False,
            )
        )

    manifest_path = next((tmp_path / "runs").glob("*/manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "exit code 7" in manifest["run_error"]
    assert not (manifest_path.parent / "intermediates").exists()
    assert not (tmp_path / "embeddings.sqlite3").exists()
