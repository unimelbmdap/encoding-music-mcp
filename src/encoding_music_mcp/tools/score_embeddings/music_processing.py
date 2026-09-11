"""Whole-score standardization, MusicXML export, and conversion validation."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from music21 import chord, converter, dynamics, instrument, note, stream, tempo

DEFAULT_TEMPO = 120.0
DEFAULT_VELOCITY = 64
DEFAULT_TIMING_TOLERANCE = 0.02
DEFAULT_WARNING_THRESHOLD = 0.99
EVENT_PRECISION = 6


class MusicProcessingError(RuntimeError):
    """Base error for score standardization and conversion."""


class XMLExportError(MusicProcessingError):
    """Raised when a standardized score cannot be exported as MusicXML."""


class XMLValidationError(MusicProcessingError):
    """Raised when exported MusicXML cannot be reparsed for validation."""


class ConversionStatus(str, Enum):
    """Disposition of a symbolic-score round trip."""

    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS WITH WARNINGS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True, order=True)
class NoteEvent:
    """Pitch event used to compare symbolic-score conversions."""

    onset: float
    pitch: int
    duration: float


@dataclass(frozen=True, slots=True)
class StandardizationConfig:
    """Deterministic values applied to a copied score."""

    tempo_bpm: float = DEFAULT_TEMPO
    velocity: int = DEFAULT_VELOCITY

    def __post_init__(self) -> None:
        if not math.isfinite(self.tempo_bpm) or self.tempo_bpm <= 0:
            raise ValueError("tempo_bpm must be a positive finite number")
        if not 0 <= self.velocity <= 127:
            raise ValueError("velocity must be between 0 and 127")

    def fingerprint(self) -> str:
        """Return a stable fingerprint for persistence provenance."""
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ConversionReport:
    """Structured comparison between source and reparsed XML events."""

    status: ConversionStatus
    source_event_count: int
    converted_event_count: int
    pitch_agreement: float
    timing_agreement: float
    tolerance: float
    message: str

    @property
    def accepted(self) -> bool:
        """Return whether the score may proceed to embedding extraction."""
        return self.status is not ConversionStatus.FAIL

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass(frozen=True, slots=True)
class ScoreConversionResult:
    """Artifacts and evidence produced for one complete score."""

    score_id: str
    xml_path: Path
    source_events: tuple[NoteEvent, ...]
    converted_events: tuple[NoteEvent, ...]
    report: ConversionReport
    processing_fingerprint: str


def _stream_containers(score: stream.Stream) -> list[stream.Stream]:
    """Collect each stream container once before mutating the copied hierarchy."""
    containers: list[stream.Stream] = [score]
    seen = {id(score)}
    for element in score.recurse().getElementsByClass(stream.Stream):
        if id(element) not in seen:
            containers.append(element)
            seen.add(id(element))
    return containers


def standardize_score(
    score: stream.Stream,
    config: StandardizationConfig | None = None,
) -> stream.Stream:
    """Return a standardized deep copy of a complete symbolic score.

    Existing tempo, instrument, and dynamic objects are removed from their owning
    stream containers without consulting or mutating ``activeSite``. Each part is
    assigned a piano, a single tempo mark, and a deterministic note velocity.
    """
    if not isinstance(score, stream.Stream):
        raise TypeError("score must be a music21 Stream")

    selected = config or StandardizationConfig()
    standardized = copy.deepcopy(score)

    removable_classes = [
        tempo.MetronomeMark,
        instrument.Instrument,
        dynamics.Dynamic,
    ]
    for container in _stream_containers(standardized):
        container.removeByClass(removable_classes)

    parts = list(standardized.parts)
    targets: list[stream.Stream] = parts or [standardized]
    for target in targets:
        target.insert(0.0, instrument.Piano())
        target.insert(0.0, tempo.MetronomeMark(number=selected.tempo_bpm))
        for pitched in target.recurse().notes:
            pitched.volume.velocity = selected.velocity

    return standardized


def extract_note_events(
    score: stream.Stream,
    *,
    precision: int = EVENT_PRECISION,
) -> tuple[NoteEvent, ...]:
    """Extract ordered note events, expanding every chord pitch.

    Tied notes are collapsed on a copied stream, so caller-owned content remains
    unchanged. Pitch values are MIDI integers used only for comparison; no MIDI
    file is produced.
    """
    if precision < 0:
        raise ValueError("precision must be non-negative")
    if not isinstance(score, stream.Stream):
        raise TypeError("score must be a music21 Stream")

    stripped = score.stripTies(inPlace=False)
    flattened = stripped.flatten()
    events: list[NoteEvent] = []
    for element in flattened.notes:
        onset = round(float(element.offset), precision)
        duration = round(float(element.quarterLength), precision)
        if isinstance(element, note.Note):
            events.append(NoteEvent(onset, int(element.pitch.midi), duration))
        elif isinstance(element, chord.Chord):
            events.extend(
                NoteEvent(onset, int(pitch.midi), duration) for pitch in element.pitches
            )
    return tuple(sorted(events))


def evaluate_conversion(
    source_events: tuple[NoteEvent, ...] | list[NoteEvent],
    converted_events: tuple[NoteEvent, ...] | list[NoteEvent],
    *,
    tolerance: float = DEFAULT_TIMING_TOLERANCE,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
) -> ConversionReport:
    """Compare two ordered event collections and classify their agreement."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a non-negative finite number")
    if not 0 <= warning_threshold <= 1:
        raise ValueError("warning_threshold must be between 0 and 1")

    source = tuple(sorted(source_events))
    converted = tuple(sorted(converted_events))
    source_count = len(source)
    converted_count = len(converted)

    if source_count != converted_count:
        return ConversionReport(
            status=ConversionStatus.FAIL,
            source_event_count=source_count,
            converted_event_count=converted_count,
            pitch_agreement=0.0,
            timing_agreement=0.0,
            tolerance=tolerance,
            message=f"Length mismatch: {source_count} vs {converted_count}",
        )

    if not source:
        return ConversionReport(
            status=ConversionStatus.PASS,
            source_event_count=0,
            converted_event_count=0,
            pitch_agreement=1.0,
            timing_agreement=1.0,
            tolerance=tolerance,
            message="No events to compare",
        )

    pitch_matches = sum(
        source_event.pitch == converted_event.pitch
        for source_event, converted_event in zip(source, converted, strict=True)
    )
    timing_matches = sum(
        math.isclose(source_event.onset, converted_event.onset, abs_tol=tolerance)
        and math.isclose(
            source_event.duration,
            converted_event.duration,
            abs_tol=tolerance,
        )
        for source_event, converted_event in zip(source, converted, strict=True)
    )
    pitch_agreement = pitch_matches / source_count
    timing_agreement = timing_matches / source_count

    if pitch_agreement == 1.0 and timing_agreement == 1.0:
        status = ConversionStatus.PASS
    elif pitch_agreement >= warning_threshold and timing_agreement >= warning_threshold:
        status = ConversionStatus.PASS_WITH_WARNINGS
    else:
        status = ConversionStatus.FAIL

    return ConversionReport(
        status=status,
        source_event_count=source_count,
        converted_event_count=converted_count,
        pitch_agreement=pitch_agreement,
        timing_agreement=timing_agreement,
        tolerance=tolerance,
        message=(f"Pitch: {pitch_agreement:.2%}, Timing: {timing_agreement:.2%}"),
    )


def safe_score_stem(score_id: str) -> str:
    """Return a deterministic filesystem-safe stem for a score identity."""
    stripped = score_id.strip()
    if not stripped:
        raise ValueError("score_id must not be empty")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", stripped).strip("._-")
    slug = (slug or "score")[:80]
    digest = hashlib.sha256(stripped.encode("utf-8")).hexdigest()[:10]
    return f"{slug}-{digest}"


def export_score_to_xml(
    standardized_score: stream.Stream,
    score_id: str,
    output_dir: str | Path,
) -> Path:
    """Export a standardized complete score as uncompressed ``.xml`` MusicXML."""
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    xml_path = destination / f"{safe_score_stem(score_id)}.xml"
    try:
        written = standardized_score.write("musicxml", fp=str(xml_path))
    except Exception as exc:  # music21 exposes writer-specific exception types
        raise XMLExportError(
            f"Failed to export score {score_id!r} to {xml_path}: {exc}"
        ) from exc

    actual_path = Path(written).resolve() if written else xml_path
    if actual_path.suffix.lower() != ".xml" or not actual_path.is_file():
        raise XMLExportError(
            f"MusicXML export did not produce the required .xml file: {actual_path}"
        )
    return actual_path


def validate_xml_roundtrip(
    standardized_score: stream.Stream,
    xml_path: str | Path,
    *,
    tolerance: float = DEFAULT_TIMING_TOLERANCE,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
) -> tuple[tuple[NoteEvent, ...], tuple[NoteEvent, ...], ConversionReport]:
    """Reparse exported XML and compare its events with the standardized score."""
    source_events = extract_note_events(standardized_score)
    candidate = Path(xml_path).expanduser().resolve()
    if candidate.suffix.lower() != ".xml":
        raise XMLValidationError("Only .xml MusicXML files may be validated")
    try:
        converted_score = converter.parse(str(candidate))
    except Exception as exc:
        raise XMLValidationError(
            f"Failed to parse exported MusicXML {candidate}: {exc}"
        ) from exc
    converted_events = extract_note_events(converted_score)
    report = evaluate_conversion(
        source_events,
        converted_events,
        tolerance=tolerance,
        warning_threshold=warning_threshold,
    )
    return source_events, converted_events, report


def process_score_to_xml(
    score: stream.Stream,
    score_id: str,
    output_dir: str | Path,
    *,
    config: StandardizationConfig | None = None,
    tolerance: float = DEFAULT_TIMING_TOLERANCE,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
) -> ScoreConversionResult:
    """Standardize, export, reparse, and validate one complete score."""
    selected = config or StandardizationConfig()
    standardized = standardize_score(score, selected)
    xml_path = export_score_to_xml(standardized, score_id, output_dir)
    source_events, converted_events, report = validate_xml_roundtrip(
        standardized,
        xml_path,
        tolerance=tolerance,
        warning_threshold=warning_threshold,
    )
    return ScoreConversionResult(
        score_id=score_id,
        xml_path=xml_path,
        source_events=source_events,
        converted_events=converted_events,
        report=report,
        processing_fingerprint=selected.fingerprint(),
    )
