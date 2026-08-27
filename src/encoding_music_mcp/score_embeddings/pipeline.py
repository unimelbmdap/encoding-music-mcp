"""Standalone whole-score MusicXML and CLaMP embedding pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from music21 import converter

from .clamp_extractor import (
    ClampError,
    ClampRuntimeConfig,
    CommandRunner,
    EmbeddingValidationError,
    config_to_dict,
    load_and_normalize_embeddings,
    run_clamp3_extraction,
    setup_clamp3,
)
from .music_processing import (
    ScoreConversionResult,
    StandardizationConfig,
    process_score_to_xml,
)
from .mei_metadata import ScoreCatalogMetadata, extract_mei_catalog_metadata
from .storage import (
    EmbeddingRecord,
    EmbeddingRepository,
    SimilarityResult,
    StorageError,
)

LOGGER = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    """Raised when a pipeline run cannot complete safely."""


@dataclass(frozen=True, slots=True)
class ScoreInput:
    """One complete MEI score selected for processing."""

    score_id: str
    path: Path


@dataclass(frozen=True, slots=True)
class MeiAggregateManifest:
    """An include-only MEI document that points at score-bearing files."""

    source_path: Path
    referenced_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SkippedInput:
    """An input intentionally omitted from a directory-discovered batch."""

    source_path: Path
    kind: str
    reason: str
    referenced_files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation used by run manifests."""
        return {
            "source_path": str(self.source_path),
            "kind": self.kind,
            "reason": self.reason,
            "referenced_files": list(self.referenced_files),
        }


@dataclass(slots=True)
class PipelineConfig:
    """Configuration for one whole-score embedding run."""

    inputs: Sequence[str | Path]
    output_dir: str | Path
    database_path: str | Path
    clamp: ClampRuntimeConfig
    standardization: StandardizationConfig = field(
        default_factory=StandardizationConfig
    )
    tolerance: float = 0.02
    warning_threshold: float = 0.99
    keep_intermediates: bool = False
    verify_clamp_setup: bool = True

    def __post_init__(self) -> None:
        self.inputs = tuple(Path(value).expanduser().resolve() for value in self.inputs)
        self.output_dir = Path(self.output_dir).expanduser().resolve()
        self.database_path = Path(self.database_path).expanduser().resolve()
        if not self.inputs:
            raise ValueError("At least one MEI input is required")
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            raise ValueError("tolerance must be a non-negative finite number")
        if not math.isfinite(self.warning_threshold) or not (
            0 <= self.warning_threshold <= 1
        ):
            raise ValueError("warning_threshold must be a finite value between 0 and 1")


@dataclass(frozen=True, slots=True)
class ScoreRunResult:
    """Durable disposition for one input score."""

    score_id: str
    source_path: Path
    source_sha256: str
    conversion_status: str
    embedding_id: int | None
    error: str | None


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Result and manifest location for a completed run."""

    run_id: str
    manifest_path: Path
    scores: tuple[ScoreRunResult, ...]
    skipped_inputs: tuple[SkippedInput, ...] = ()


@dataclass(frozen=True, slots=True)
class _DiscoveryBatch:
    scores: tuple[ScoreInput, ...]
    skipped_inputs: tuple[SkippedInput, ...]


def _local_name(tag: str) -> str:
    """Return an XML tag's local name for namespaced and plain documents."""
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def classify_mei_aggregate(path: str | Path) -> MeiAggregateManifest | None:
    """Classify a valid include-only MEI document without resolving includes.

    Malformed XML and documents without a score that do not contain usable
    includes are deliberately unclassified so they continue through the normal
    per-score diagnostic path.
    """
    source_path = Path(path).expanduser().resolve()
    try:
        root = ET.parse(source_path).getroot()
    except (ET.ParseError, OSError):
        return None
    if _local_name(root.tag) != "mei":
        return None

    has_score = False
    referenced_files: list[str] = []
    for element in root.iter():
        local_name = _local_name(element.tag)
        if local_name == "score":
            has_score = True
        elif local_name == "include":
            href = element.get("href")
            if href is not None and (cleaned_href := href.strip()):
                referenced_files.append(cleaned_href)
    if has_score or not referenced_files:
        return None
    return MeiAggregateManifest(source_path, tuple(referenced_files))


def _aggregate_input_error(aggregate: MeiAggregateManifest) -> PipelineError:
    references = ", ".join(aggregate.referenced_files)
    return PipelineError(
        "Input is an include-only aggregate MEI manifest and cannot be embedded "
        f"as a complete score: {aggregate.source_path}. Referenced score files: "
        f"{references}. Supply the referenced score-bearing MEI files or their "
        "directory instead."
    )


def _discover_mei_inputs(inputs: Sequence[str | Path]) -> _DiscoveryBatch:
    """Discover score inputs and retain directory aggregates as diagnostics."""
    explicit_files: set[Path] = set()
    directories: list[Path] = []
    for value in inputs:
        candidate = Path(value).expanduser().resolve()
        if not candidate.exists():
            raise PipelineError(f"Input does not exist: {candidate}")
        if candidate.is_file():
            if candidate.suffix.lower() != ".mei":
                raise PipelineError(f"Input file is not MEI: {candidate}")
            explicit_files.add(candidate)
        elif candidate.is_dir():
            directories.append(candidate)
        else:
            raise PipelineError(f"Input is neither a file nor directory: {candidate}")

    # Explicit intent always wins, independent of argument order and even when
    # the same path is also reachable through a supplied directory.
    for path in sorted(explicit_files, key=lambda item: item.as_posix()):
        aggregate = classify_mei_aggregate(path)
        if aggregate is not None:
            raise _aggregate_input_error(aggregate)

    directory_files = {
        path.resolve()
        for directory in directories
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() == ".mei"
    }
    skipped: list[SkippedInput] = []
    score_paths = set(explicit_files)
    for path in sorted(directory_files, key=lambda item: item.as_posix()):
        aggregate = classify_mei_aggregate(path)
        if aggregate is None:
            score_paths.add(path)
            continue
        skipped_input = SkippedInput(
            source_path=path,
            kind="include_only_aggregate",
            reason="Include-only aggregate MEI manifest has no score element",
            referenced_files=aggregate.referenced_files,
        )
        skipped.append(skipped_input)
        LOGGER.info(
            "Skipping include-only aggregate MEI manifest %s (references: %s)",
            path,
            ", ".join(aggregate.referenced_files),
        )

    ordered = sorted(score_paths, key=lambda path: path.as_posix())
    if not ordered:
        if skipped:
            raise PipelineError(
                "No score-bearing .mei inputs were discovered; directory inputs "
                "contained only include-only aggregate manifests. Supply the "
                "referenced score-bearing MEI files."
            )
        raise PipelineError("No .mei files were discovered")

    counts: dict[str, int] = {}
    for path in ordered:
        counts[path.stem] = counts.get(path.stem, 0) + 1
    provisional: list[tuple[Path, str]] = []
    for path in ordered:
        score_id = path.stem
        if counts[score_id] > 1:
            suffix = _sha256_file(path)[:8]
            score_id = f"{score_id}-{suffix}"
        provisional.append((path, score_id))
    identity_counts: dict[str, int] = {}
    discovered: list[ScoreInput] = []
    for path, base_id in provisional:
        occurrence = identity_counts.get(base_id, 0) + 1
        identity_counts[base_id] = occurrence
        score_id = base_id if occurrence == 1 else f"{base_id}-{occurrence}"
        discovered.append(ScoreInput(score_id=score_id, path=path))
    return _DiscoveryBatch(tuple(discovered), tuple(skipped))


def discover_mei_inputs(inputs: Sequence[str | Path]) -> tuple[ScoreInput, ...]:
    """Resolve files/directories into a deterministic, de-duplicated MEI batch."""
    return _discover_mei_inputs(inputs).scores


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _retain_intermediates(workspace: Path, run_dir: Path) -> None:
    shutil.copytree(workspace, run_dir / "intermediates", dirs_exist_ok=True)


def _score_result(entry: dict[str, Any]) -> ScoreRunResult:
    return ScoreRunResult(
        score_id=str(entry["score_id"]),
        source_path=Path(entry["source_path"]),
        source_sha256=str(entry["source_sha256"]),
        conversion_status=str(entry["conversion_status"]),
        embedding_id=entry.get("embedding_id"),
        error=entry.get("error"),
    )


def run_pipeline(
    config: PipelineConfig,
    *,
    clamp_runner: CommandRunner | None = None,
) -> PipelineRunResult:
    """Convert, validate, embed, and persist complete MEI scores."""
    discovery = _discover_mei_inputs(config.inputs)
    discovered = discovery.scores
    run_id = _run_id()
    run_dir = Path(config.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = run_dir / "manifest.json"
    # Always isolate paths passed to the pinned upstream preprocessor. That
    # script constructs an internal shell command, so user-selected output paths
    # must never flow into its command string.
    temporary = tempfile.TemporaryDirectory(prefix="encoding-music-embeddings-")
    workspace = Path(temporary.name)
    xml_dir = workspace / "xml"
    embedding_dir = workspace / "embeddings"
    xml_dir.mkdir()

    entries: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "manifest_version": 1,
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
        "database_path": str(Path(config.database_path)),
        "keep_intermediates": config.keep_intermediates,
        "standardization": asdict(config.standardization),
        "tolerance": config.tolerance,
        "warning_threshold": config.warning_threshold,
        "clamp": config_to_dict(config.clamp),
        "skipped_inputs": [item.to_dict() for item in discovery.skipped_inputs],
        "scores": entries,
        "run_error": None,
    }
    accepted: list[
        tuple[ScoreInput, str, ScoreCatalogMetadata, ScoreConversionResult]
    ] = []
    try:
        for item in discovered:
            source_sha256 = _sha256_file(item.path)
            entry: dict[str, Any] = {
                "score_id": item.score_id,
                "source_path": str(item.path),
                "source_sha256": source_sha256,
                "title": None,
                "artist": None,
                "work_created_date": None,
                "xml_filename": None,
                "conversion_status": "ERROR",
                "validation": None,
                "embedding_id": None,
                "error": None,
            }
            entries.append(entry)
            try:
                metadata = extract_mei_catalog_metadata(item.path)
                entry["title"] = metadata.title
                entry["artist"] = metadata.artist
                entry["work_created_date"] = metadata.work_created_date
                score = converter.parse(str(item.path))
                conversion = process_score_to_xml(
                    score,
                    item.score_id,
                    xml_dir,
                    config=config.standardization,
                    tolerance=config.tolerance,
                    warning_threshold=config.warning_threshold,
                )
                entry["xml_filename"] = conversion.xml_path.name
                entry["conversion_status"] = conversion.report.status.value
                entry["validation"] = conversion.report.to_dict()
                if conversion.report.accepted:
                    accepted.append((item, source_sha256, metadata, conversion))
                else:
                    entry["error"] = conversion.report.message
                    LOGGER.warning("Validation rejected %s", item.path)
            except Exception as exc:
                entry["error"] = str(exc)
                LOGGER.exception("Failed to convert score %s", item.path)

        if accepted:
            LOGGER.info("Extracting embeddings for %d validated scores", len(accepted))
            # Keep every exported XML in the diagnostic workspace, but expose
            # only validation-accepted files to the external CLaMP runtime.
            # The transient staging directory is removed before optional
            # intermediate retention, including when extraction fails.
            with tempfile.TemporaryDirectory(
                prefix="clamp-input-",
                dir=workspace,
            ) as clamp_input:
                clamp_input_dir = Path(clamp_input)
                for _, _, _, conversion in accepted:
                    shutil.copy2(
                        conversion.xml_path,
                        clamp_input_dir / conversion.xml_path.name,
                    )
                extraction_arguments = (clamp_input_dir, embedding_dir, config.clamp)
                if clamp_runner is None:
                    run_clamp3_extraction(
                        *extraction_arguments,
                        verify_setup=config.verify_clamp_setup,
                    )
                else:
                    run_clamp3_extraction(
                        *extraction_arguments,
                        runner=clamp_runner,
                        verify_setup=config.verify_clamp_setup,
                    )
            stems = [conversion.xml_path.stem for _, _, _, conversion in accepted]
            batch = load_and_normalize_embeddings(
                embedding_dir,
                expected_dim=config.clamp.expected_dimension,
                expected_stems=stems,
                allow_missing_expected=True,
            )
            if not batch.stems:
                raise EmbeddingValidationError(
                    "CLaMP produced no embeddings for the validated score batch"
                )
            embedding_indexes = {stem: index for index, stem in enumerate(batch.stems)}
            with EmbeddingRepository(
                config.database_path,
                dimension=config.clamp.expected_dimension,
            ) as repository:
                for item, source_sha256, metadata, conversion in accepted:
                    stem = conversion.xml_path.stem
                    index = embedding_indexes.get(stem)
                    entry = entries[discovered.index(item)]
                    if index is None:
                        entry["error"] = (
                            "CLaMP preprocessing or inference produced no embedding "
                            f"output for {stem}"
                        )
                        LOGGER.warning(
                            "CLaMP produced no embedding output for validated score %s",
                            item.path,
                        )
                        continue
                    stored = repository.upsert(
                        EmbeddingRecord(
                            score_id=item.score_id,
                            title=metadata.title,
                            artist=metadata.artist,
                            work_created_date=metadata.work_created_date,
                            source_path=str(item.path),
                            source_sha256=source_sha256,
                            processing_fingerprint=conversion.processing_fingerprint,
                            validation=conversion.report.to_dict(),
                            model_commit=config.clamp.commit,
                            model_revision=config.clamp.model_revision,
                            model_weight_sha256=config.clamp.weight_sha256,
                            raw_embedding=batch.raw[index],
                            normalized_embedding=batch.normalized[index],
                        )
                    )
                    entry["embedding_id"] = stored.id

        if config.keep_intermediates:
            _retain_intermediates(workspace, run_dir)
        manifest["completed_at"] = datetime.now(UTC).isoformat()
        _write_manifest(manifest_path, manifest)
        LOGGER.info("Pipeline manifest written to %s", manifest_path)
        return PipelineRunResult(
            run_id=run_id,
            manifest_path=manifest_path,
            scores=tuple(_score_result(entry) for entry in entries),
            skipped_inputs=discovery.skipped_inputs,
        )
    except Exception as exc:
        retention_error: OSError | None = None
        if config.keep_intermediates:
            try:
                _retain_intermediates(workspace, run_dir)
            except OSError as copy_error:
                retention_error = copy_error
        for entry in entries:
            if entry["embedding_id"] is None and entry["error"] is None:
                entry["error"] = f"Extraction or persistence failed: {exc}"
        manifest["run_error"] = str(exc)
        if retention_error is not None:
            manifest["run_error"] += (
                f"; retaining intermediate diagnostics also failed: {retention_error}"
            )
        manifest["completed_at"] = datetime.now(UTC).isoformat()
        _write_manifest(manifest_path, manifest)
        raise PipelineError(
            f"Pipeline failed; diagnostics were written to {manifest_path}: {exc}"
        ) from exc
    finally:
        temporary.cleanup()


def query_similar(
    database_path: str | Path,
    *,
    score_id: str | None = None,
    embedding_id: int | None = None,
    limit: int = 10,
) -> list[SimilarityResult]:
    """Query nearest neighbors using either a score or embedding identity."""
    if (score_id is None) == (embedding_id is None):
        raise ValueError("Provide exactly one of score_id or embedding_id")
    with EmbeddingRepository(database_path) as repository:
        selected_id = embedding_id
        if score_id is not None:
            records = repository.get_by_score_id(score_id)
            if not records:
                raise KeyError(f"No embedding is stored for score_id {score_id!r}")
            selected_id = records[-1].id
        assert selected_id is not None
        return repository.similarity_search_by_id(selected_id, limit=limit)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="encoding-music-embeddings",
        description="Create whole-score CLaMP embeddings from MEI files.",
    )
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Prepare pinned CLaMP assets")
    setup_parser.add_argument("--clamp-python", required=True, type=Path)
    setup_parser.add_argument("--cache-dir", type=Path)
    setup_parser.add_argument("--timeout", type=float, default=3600.0)

    extract_parser = subparsers.add_parser("extract", help="Embed complete MEI scores")
    extract_parser.add_argument("inputs", nargs="+", type=Path)
    extract_parser.add_argument(
        "--database", type=Path, default=Path("score-embeddings.sqlite3")
    )
    extract_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/score_embeddings"),
    )
    extract_parser.add_argument("--clamp-python", required=True, type=Path)
    extract_parser.add_argument("--cache-dir", type=Path)
    extract_parser.add_argument("--tolerance", type=float, default=0.02)
    extract_parser.add_argument("--timeout", type=float, default=3600.0)
    extract_parser.add_argument("--keep-intermediates", action="store_true")

    similar_parser = subparsers.add_parser("similar", help="Query cosine neighbors")
    similar_parser.add_argument("--database", required=True, type=Path)
    identity = similar_parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--score-id")
    identity.add_argument("--embedding-id", type=int)
    similar_parser.add_argument("--limit", type=int, default=10)
    return parser


def _runtime_from_args(args: argparse.Namespace) -> ClampRuntimeConfig:
    kwargs: dict[str, Any] = {
        "python_executable": args.clamp_python,
        "timeout_seconds": args.timeout,
    }
    if args.cache_dir is not None:
        kwargs["cache_dir"] = args.cache_dir
    return ClampRuntimeConfig(**kwargs)


def cli(argv: Sequence[str] | None = None) -> int:
    """Execute the command-line interface and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    level = getattr(logging, str(args.log_level).upper(), None)
    if not isinstance(level, int):
        parser.error(f"invalid log level: {args.log_level}")
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    try:
        if args.command == "setup":
            result = setup_clamp3(_runtime_from_args(args))
            print(
                json.dumps(
                    {
                        "cache_dir": str(result.checkout_dir.parent),
                        "offline_ready": result.offline_ready,
                    }
                )
            )
        elif args.command == "extract":
            result = run_pipeline(
                PipelineConfig(
                    inputs=args.inputs,
                    output_dir=args.output_dir,
                    database_path=args.database,
                    clamp=_runtime_from_args(args),
                    tolerance=args.tolerance,
                    keep_intermediates=args.keep_intermediates,
                )
            )
            print(
                json.dumps(
                    {"run_id": result.run_id, "manifest": str(result.manifest_path)}
                )
            )
            if any(score.embedding_id is None for score in result.scores):
                return 1
        else:
            results = query_similar(
                args.database,
                score_id=args.score_id,
                embedding_id=args.embedding_id,
                limit=args.limit,
            )
            print(
                json.dumps(
                    [
                        {
                            "embedding_id": result.embedding.id,
                            "score_id": result.embedding.score_id,
                            "title": result.embedding.title,
                            "artist": result.embedding.artist,
                            "work_created_date": result.embedding.work_created_date,
                            "distance": result.distance,
                        }
                        for result in results
                    ]
                )
            )
    except (PipelineError, ClampError, StorageError, KeyError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


def main() -> None:
    """Run the console entry point."""
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
