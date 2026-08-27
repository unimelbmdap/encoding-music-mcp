"""Tests for whole-score pipeline orchestration and CLI behavior."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from music21 import converter, stream

from encoding_music_mcp.score_embeddings.clamp_extractor import (
    ClampExecutionError,
    ClampRuntimeConfig,
)
from encoding_music_mcp.score_embeddings.music_processing import (
    ConversionReport,
    ConversionStatus,
    ScoreConversionResult,
)
from encoding_music_mcp.score_embeddings.mei_metadata import (
    ScoreCatalogMetadata,
    extract_mei_catalog_metadata,
)
from encoding_music_mcp.score_embeddings.pipeline import (
    PipelineConfig,
    PipelineError,
    classify_mei_aggregate,
    cli,
    discover_mei_inputs,
    run_pipeline,
)
from encoding_music_mcp.score_embeddings.storage import EmbeddingRepository


def _completed(args) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(args), 0, stdout="", stderr="")


def _write_mei(
    path: Path,
    *,
    title: str = "Work title",
    artist: str = "Composer Name",
    work_created_date: str | None = "1723",
) -> None:
    creation = (
        f"<creation><date isodate='{work_created_date}'/></creation>"
        if work_created_date is not None
        else ""
    )
    path.write_text(
        "<mei xmlns='http://www.music-encoding.org/ns/mei'>"
        "<meiHead>"
        "<fileDesc><titleStmt><title>File title</title><respStmt>"
        f"<persName role='composer'>{artist}</persName>"
        "</respStmt></titleStmt><pubStmt><date isodate='2026-08-25'/></pubStmt>"
        "</fileDesc>"
        f"<workList><work><title>{title}</title><composer>{artist}</composer>"
        f"{creation}</work></workList>"
        "</meiHead><music/></mei>",
        encoding="utf-8",
    )


def _write_aggregate(
    path: Path,
    references: tuple[str, ...] = ("movement-1.mei", "movement-2.mei"),
    *,
    prefixed: bool = False,
) -> None:
    namespace = " xmlns:xi='http://www.w3.org/2001/XInclude'" if prefixed else ""
    prefix = "xi:" if prefixed else ""
    includes = "".join(
        f"<{prefix}include href='{reference}'/>" for reference in references
    )
    path.write_text(
        f"<mei{namespace}><music><body>{includes}</body></music></mei>",
        encoding="utf-8",
    )


def _runtime(tmp_path: Path) -> ClampRuntimeConfig:
    checkout = tmp_path / "cache" / "source"
    for script in (
        checkout / "preprocessing" / "abc" / "batch_xml2abc.py",
        checkout / "preprocessing" / "abc" / "batch_interleaved_abc.py",
        checkout / "code" / "extract_clamp3.py",
    ):
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("# fake\n", encoding="utf-8")
    return ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )


def _conversion(
    score_id: str,
    output_dir: str | Path,
    status: ConversionStatus = ConversionStatus.PASS,
) -> ScoreConversionResult:
    xml_path = Path(output_dir) / f"{score_id}.xml"
    xml_path.write_text("<score-partwise version='4.0'/>", encoding="utf-8")
    agreement = 1.0 if status is not ConversionStatus.FAIL else 0.0
    report = ConversionReport(
        status=status,
        source_event_count=1,
        converted_event_count=1,
        pitch_agreement=agreement,
        timing_agreement=agreement,
        tolerance=0.02,
        message=status.value,
    )
    return ScoreConversionResult(
        score_id=score_id,
        xml_path=xml_path,
        source_events=(),
        converted_events=(),
        report=report,
        processing_fingerprint="processing-v1",
    )


def _successful_runner(workspaces: list[Path]):
    stems: list[str] = []

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        if command[1].endswith("batch_xml2abc.py"):
            source = Path(command[2])
            workspaces.append(source.parent)
            stems.extend(path.stem for path in sorted(source.glob("*.xml")))
        elif command[1].endswith("extract_clamp3.py"):
            destination = Path(command[3])
            destination.mkdir(parents=True, exist_ok=True)
            for index, stem in enumerate(stems):
                vector = np.zeros(768, dtype=np.float32)
                vector[index] = 1.0
                np.save(destination / f"{stem}.npy", vector)
        return _completed(command)

    return runner


def test_discovery_is_recursive_deterministic_deduplicated_and_collision_safe(
    tmp_path: Path,
):
    first = tmp_path / "b" / "same.mei"
    second = tmp_path / "a" / "same.mei"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    discovered = discover_mei_inputs([first, tmp_path, second])

    assert [item.path for item in discovered] == [second.resolve(), first.resolve()]
    assert len({item.score_id for item in discovered}) == 2
    assert all(item.score_id.startswith("same-") for item in discovered)


@pytest.mark.parametrize("prefixed", [False, True])
def test_directory_discovery_skips_include_only_aggregates_for_namespace_forms(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    prefixed: bool,
):
    aggregate = tmp_path / "aggregate.mei"
    _write_aggregate(aggregate, prefixed=prefixed)
    first = tmp_path / "movement-2.mei"
    second = tmp_path / "movement-1.mei"
    _write_mei(first)
    _write_mei(second)
    caplog.set_level(logging.INFO)

    discovered = discover_mei_inputs([tmp_path])

    assert [item.path for item in discovered] == [second.resolve(), first.resolve()]
    assert "Skipping include-only aggregate MEI manifest" in caplog.text
    classification = classify_mei_aggregate(aggregate)
    assert classification is not None
    assert classification.referenced_files == (
        "movement-1.mei",
        "movement-2.mei",
    )


def test_score_element_prevents_aggregate_classification(tmp_path: Path):
    source = tmp_path / "score-with-include.mei"
    source.write_text(
        "<mei><music><body><include href='other.mei'/><score/></body></music></mei>",
        encoding="utf-8",
    )

    assert classify_mei_aggregate(source) is None
    assert [item.path for item in discover_mei_inputs([tmp_path])] == [source.resolve()]


def test_explicit_aggregate_wins_over_directory_and_lists_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    aggregate = tmp_path / "aggregate.mei"
    _write_aggregate(aggregate)
    _write_mei(tmp_path / "movement-1.mei")

    for inputs in ([aggregate], [tmp_path, aggregate]):
        with pytest.raises(PipelineError) as captured:
            discover_mei_inputs(inputs)

        message = str(captured.value)
        assert "include-only aggregate" in message
        assert "movement-1.mei" in message
        assert "movement-2.mei" in message

    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: pytest.fail("recognized aggregates must fail before music21"),
    )
    with pytest.raises(PipelineError, match="movement-1.mei"):
        run_pipeline(
            PipelineConfig(
                inputs=[aggregate],
                output_dir=tmp_path / "runs",
                database_path=tmp_path / "embeddings.sqlite3",
                clamp=_runtime(tmp_path),
                verify_clamp_setup=False,
            )
        )


def test_directory_containing_only_aggregates_fails_actionably(tmp_path: Path):
    _write_aggregate(tmp_path / "aggregate.mei")

    with pytest.raises(PipelineError, match="No score-bearing .mei inputs"):
        discover_mei_inputs([tmp_path])


def test_real_crim_aggregate_is_classified_and_child_is_parseable():
    corpus = (
        Path(__file__).parents[2]
        / "src"
        / "encoding_music_mcp"
        / "resources"
        / "mei_files"
    )
    aggregate = corpus / "CRIM_Mass_0002.mei"
    movement = corpus / "CRIM_Mass_0002_1.mei"

    classification = classify_mei_aggregate(aggregate)

    assert classification is not None
    assert "CRIM_Mass_0002_1.mei" in classification.referenced_files
    assert discover_mei_inputs([movement])[0].path == movement.resolve()
    parsed = converter.parse(str(movement))
    assert len(parsed.parts) > 0


def test_mei_metadata_prefers_work_fields_and_nulls_missing_or_ambiguous_values(
    tmp_path: Path,
):
    complete = tmp_path / "complete.mei"
    _write_mei(complete)
    assert extract_mei_catalog_metadata(complete) == ScoreCatalogMetadata(
        title="Work title",
        artist="Composer Name",
        work_created_date="1723",
    )

    missing = tmp_path / "missing.mei"
    missing.write_text(
        "<mei><meiHead><fileDesc><titleStmt/></fileDesc>"
        "<pubStmt><date isodate='2026-08-25'/></pubStmt>"
        "</meiHead></mei>",
        encoding="utf-8",
    )
    assert extract_mei_catalog_metadata(missing) == ScoreCatalogMetadata(
        None, None, None
    )

    ambiguous = tmp_path / "ambiguous.mei"
    ambiguous.write_text(
        "<mei><meiHead><fileDesc><titleStmt><title>Fallback</title>"
        "<respStmt><persName role='composer'>Fallback Artist</persName></respStmt>"
        "</titleStmt></fileDesc><workList><work><title>One</title>"
        "<title>Two</title><composer>First</composer><composer>Second</composer>"
        "<creation><date>1600</date><date>1601</date></creation>"
        "</work></workList></meiHead></mei>",
        encoding="utf-8",
    )
    assert extract_mei_catalog_metadata(ambiguous) == ScoreCatalogMetadata(
        None, None, None
    )


@pytest.mark.parametrize("keep_intermediates", [False, True])
def test_pipeline_stores_ordered_results_writes_manifest_and_obeys_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    keep_intermediates: bool,
):
    for name in ("b.mei", "a.mei"):
        _write_mei(tmp_path / name, title=f"Title {name[0].upper()}")
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(score_id, output_dir),
    )
    workspaces: list[Path] = []
    caplog.set_level(logging.INFO)
    database = tmp_path / "embeddings.sqlite3"
    result = run_pipeline(
        PipelineConfig(
            inputs=[tmp_path],
            output_dir=tmp_path / "runs",
            database_path=database,
            clamp=_runtime(tmp_path),
            keep_intermediates=keep_intermediates,
            verify_clamp_setup=False,
        ),
        clamp_runner=_successful_runner(workspaces),
    )

    assert [score.score_id for score in result.scores] == ["a", "b"]
    assert all(score.embedding_id is not None for score in result.scores)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [entry["score_id"] for entry in manifest["scores"]] == ["a", "b"]
    assert [entry["title"] for entry in manifest["scores"]] == ["Title A", "Title B"]
    assert all(entry["artist"] == "Composer Name" for entry in manifest["scores"])
    assert all(entry["work_created_date"] == "1723" for entry in manifest["scores"])
    assert manifest["run_error"] is None
    assert "Pipeline manifest written" in caplog.text
    assert not workspaces[0].exists()
    assert (
        result.manifest_path.parent / "intermediates"
    ).exists() is keep_intermediates
    with EmbeddingRepository(database) as repository:
        stored = repository.get_by_score_id("a")[0]
        assert stored.title == "Title A"
        assert stored.artist == "Composer Name"
        assert stored.work_created_date == "1723"


def test_pipeline_reports_skipped_aggregate_without_a_score_result_or_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    aggregate = tmp_path / "aggregate.mei"
    _write_aggregate(aggregate, ("score.mei",))
    source = tmp_path / "score.mei"
    _write_mei(source)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(score_id, output_dir),
    )
    caplog.set_level(logging.INFO)
    workspaces: list[Path] = []

    result = run_pipeline(
        PipelineConfig(
            inputs=[tmp_path],
            output_dir=tmp_path / "runs",
            database_path=tmp_path / "embeddings.sqlite3",
            clamp=_runtime(tmp_path),
            verify_clamp_setup=False,
        ),
        clamp_runner=_successful_runner(workspaces),
    )

    assert [score.score_id for score in result.scores] == ["score"]
    assert result.scores[0].embedding_id is not None
    assert len(result.skipped_inputs) == 1
    assert result.skipped_inputs[0].source_path == aggregate.resolve()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_error"] is None
    assert manifest["skipped_inputs"] == [
        {
            "kind": "include_only_aggregate",
            "reason": "Include-only aggregate MEI manifest has no score element",
            "referenced_files": ["score.mei"],
            "source_path": str(aggregate.resolve()),
        }
    ]
    assert [entry["score_id"] for entry in manifest["scores"]] == ["score"]
    assert "Skipping include-only aggregate MEI manifest" in caplog.text


def test_malformed_and_nonaggregate_no_score_inputs_remain_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    malformed = tmp_path / "malformed.mei"
    malformed.write_text("<mei><music>", encoding="utf-8")
    no_score = tmp_path / "no-score.mei"
    no_score.write_text("<mei><music/></mei>", encoding="utf-8")
    parsed_paths: list[Path] = []

    def fail_parse(path: str):
        parsed_paths.append(Path(path))
        raise RuntimeError("ordinary no-score parse failure")

    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        fail_parse,
    )

    result = run_pipeline(
        PipelineConfig(
            inputs=[tmp_path],
            output_dir=tmp_path / "runs",
            database_path=tmp_path / "embeddings.sqlite3",
            clamp=_runtime(tmp_path),
            verify_clamp_setup=False,
        ),
        clamp_runner=lambda *args: pytest.fail("CLaMP must not run"),
    )

    assert [score.score_id for score in result.scores] == ["malformed", "no-score"]
    assert result.skipped_inputs == ()
    assert all(score.conversion_status == "ERROR" for score in result.scores)
    assert all(score.error for score in result.scores)
    # Malformed metadata fails before music21; the well-formed non-aggregate
    # remains in the ordinary conversion path.
    assert parsed_paths == [no_score.resolve()]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["skipped_inputs"] == []


def test_cli_success_is_based_on_score_results_not_skipped_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.run_pipeline",
        lambda config: SimpleNamespace(
            run_id="run-id",
            manifest_path=tmp_path / "manifest.json",
            scores=(SimpleNamespace(embedding_id=1),),
            skipped_inputs=(SimpleNamespace(source_path=tmp_path / "aggregate.mei"),),
        ),
    )

    exit_code = cli(
        [
            "extract",
            str(tmp_path),
            "--clamp-python",
            sys.executable,
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["run_id"] == "run-id"


def test_cli_partial_run_returns_failure_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.run_pipeline",
        lambda config: SimpleNamespace(
            run_id="partial-run",
            manifest_path=tmp_path / "manifest.json",
            scores=(
                SimpleNamespace(embedding_id=1),
                SimpleNamespace(embedding_id=None),
            ),
            skipped_inputs=(),
        ),
    )

    exit_code = cli(
        [
            "extract",
            str(tmp_path),
            "--clamp-python",
            sys.executable,
        ]
    )

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out)["run_id"] == "partial-run"


def test_failed_validation_never_invokes_clamp_or_creates_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "failed.mei"
    _write_mei(source)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(
            score_id, output_dir, ConversionStatus.FAIL
        ),
    )

    result = run_pipeline(
        PipelineConfig(
            inputs=[source],
            output_dir=tmp_path / "runs",
            database_path=tmp_path / "embeddings.sqlite3",
            clamp=_runtime(tmp_path),
            verify_clamp_setup=False,
        ),
        clamp_runner=lambda *args: pytest.fail("CLaMP must not run"),
    )

    assert result.scores[0].conversion_status == "FAIL"
    assert result.scores[0].embedding_id is None
    assert not (tmp_path / "embeddings.sqlite3").exists()


def test_mixed_batch_exposes_only_accepted_xml_and_persists_its_embedding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    for name in ("accepted.mei", "rejected.mei"):
        _write_mei(tmp_path / name)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )

    def convert(score, score_id, output_dir, **kwargs):
        status = (
            ConversionStatus.FAIL if score_id == "rejected" else ConversionStatus.PASS
        )
        return _conversion(score_id, output_dir, status)

    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        convert,
    )
    clamp_inputs: list[tuple[str, ...]] = []

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        if command[1].endswith("batch_xml2abc.py"):
            source = Path(command[2])
            clamp_inputs.append(
                tuple(path.name for path in sorted(source.glob("*.xml")))
            )
        elif command[1].endswith("extract_clamp3.py"):
            destination = Path(command[3])
            destination.mkdir(parents=True, exist_ok=True)
            vector = np.zeros(768, dtype=np.float32)
            vector[:2] = [3.0, 4.0]
            np.save(destination / "accepted.npy", vector)
        return _completed(command)

    database = tmp_path / "embeddings.sqlite3"
    result = run_pipeline(
        PipelineConfig(
            inputs=[tmp_path / "accepted.mei", tmp_path / "rejected.mei"],
            output_dir=tmp_path / "runs",
            database_path=database,
            clamp=_runtime(tmp_path),
            keep_intermediates=True,
            verify_clamp_setup=False,
        ),
        clamp_runner=runner,
    )

    assert clamp_inputs == [("accepted.xml",)]
    accepted, rejected = result.scores
    assert accepted.conversion_status == "PASS"
    assert accepted.embedding_id is not None
    assert rejected.conversion_status == "FAIL"
    assert rejected.embedding_id is None

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [entry["conversion_status"] for entry in manifest["scores"]] == [
        "PASS",
        "FAIL",
    ]
    assert manifest["scores"][1]["embedding_id"] is None
    retained = result.manifest_path.parent / "intermediates"
    assert {path.name for path in (retained / "xml").glob("*.xml")} == {
        "accepted.xml",
        "rejected.xml",
    }
    assert not list(retained.glob("clamp-input-*"))

    with EmbeddingRepository(database) as repository:
        assert repository.get_by_score_id("rejected") == []
        records = repository.get_by_score_id("accepted")
        assert len(records) == 1
        normalized_blob = repository.connection.execute(
            "SELECT normalized_embedding FROM embedding_vectors WHERE embedding_id = ?",
            (records[0].id,),
        ).fetchone()[0]
    normalized = np.frombuffer(normalized_blob, dtype=np.float32)
    assert normalized[:2] == pytest.approx([0.6, 0.8])


def test_partial_clamp_output_persists_present_and_reports_missing_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    for name in ("first.mei", "second.mei"):
        _write_mei(tmp_path / name)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(score_id, output_dir),
    )

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        if command[1].endswith("extract_clamp3.py"):
            destination = Path(command[3])
            destination.mkdir(parents=True, exist_ok=True)
            np.save(destination / "second.npy", np.ones(768, dtype=np.float32))
        return _completed(command)

    database = tmp_path / "embeddings.sqlite3"
    result = run_pipeline(
        PipelineConfig(
            inputs=[tmp_path / "first.mei", tmp_path / "second.mei"],
            output_dir=tmp_path / "runs",
            database_path=database,
            clamp=_runtime(tmp_path),
            verify_clamp_setup=False,
        ),
        clamp_runner=runner,
    )

    first, second = result.scores
    assert first.embedding_id is None
    assert first.error == (
        "CLaMP preprocessing or inference produced no embedding output for first"
    )
    assert second.embedding_id is not None
    assert second.error is None
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_error"] is None
    assert manifest["scores"][0]["error"] == first.error
    with EmbeddingRepository(database) as repository:
        assert repository.get_by_score_id("first") == []
        assert len(repository.get_by_score_id("second")) == 1


def test_zero_clamp_outputs_remain_fatal_and_create_no_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "score.mei"
    _write_mei(source)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(score_id, output_dir),
    )

    with pytest.raises(PipelineError, match="produced no embeddings"):
        run_pipeline(
            PipelineConfig(
                inputs=[source],
                output_dir=tmp_path / "runs",
                database_path=tmp_path / "embeddings.sqlite3",
                clamp=_runtime(tmp_path),
                verify_clamp_setup=False,
            ),
            clamp_runner=lambda args, cwd, env, timeout: _completed(args),
        )

    assert not (tmp_path / "embeddings.sqlite3").exists()
    manifest_path = next((tmp_path / "runs").glob("*/manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "produced no embeddings" in manifest["run_error"]
    assert manifest["scores"][0]["embedding_id"] is None


def test_subprocess_failure_is_propagated_with_manifest_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "score.mei"
    _write_mei(source)
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.converter.parse",
        lambda _: stream.Score(),
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.process_score_to_xml",
        lambda score, score_id, output_dir, **kwargs: _conversion(score_id, output_dir),
    )
    workspaces: list[Path] = []

    def failing_runner(args, cwd, env, timeout):
        workspaces.append(Path(args[2]).parent)
        raise ClampExecutionError("simulated subprocess failure")

    with pytest.raises(PipelineError, match="simulated subprocess failure"):
        run_pipeline(
            PipelineConfig(
                inputs=[source],
                output_dir=tmp_path / "runs",
                database_path=tmp_path / "embeddings.sqlite3",
                clamp=_runtime(tmp_path),
                verify_clamp_setup=False,
            ),
            clamp_runner=failing_runner,
        )

    manifests = list((tmp_path / "runs").glob("*/manifest.json"))
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert "simulated subprocess failure" in manifest["run_error"]
    assert "failed" in manifest["scores"][0]["error"].lower()
    assert not workspaces[0].exists()


def test_cli_setup_reports_json_and_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.setup_clamp3",
        lambda config: SimpleNamespace(
            checkout_dir=tmp_path / "cache" / "source",
            offline_ready=True,
        ),
    )

    exit_code = cli(
        [
            "--log-level",
            "DEBUG",
            "setup",
            "--clamp-python",
            sys.executable,
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["offline_ready"] is True


def test_cli_similarity_json_includes_catalog_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    result = SimpleNamespace(
        embedding=SimpleNamespace(
            id=4,
            score_id="catalog-score",
            title="Catalog title",
            artist="Catalog artist",
            work_created_date="1899",
        ),
        distance=0.125,
    )
    monkeypatch.setattr(
        "encoding_music_mcp.score_embeddings.pipeline.query_similar",
        lambda *args, **kwargs: [result],
    )

    exit_code = cli(
        [
            "similar",
            "--database",
            str(tmp_path / "catalog.sqlite3"),
            "--score-id",
            "catalog-score",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "embedding_id": 4,
            "score_id": "catalog-score",
            "title": "Catalog title",
            "artist": "Catalog artist",
            "work_created_date": "1899",
            "distance": 0.125,
        }
    ]
