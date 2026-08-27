"""Tests for whole-score MusicXML processing."""

from pathlib import Path

import pytest
from music21 import chord, dynamics, instrument, note, stream, tempo, tie

from encoding_music_mcp.score_embeddings.music_processing import (
    ConversionStatus,
    NoteEvent,
    StandardizationConfig,
    evaluate_conversion,
    export_score_to_xml,
    extract_note_events,
    process_score_to_xml,
    safe_score_stem,
    standardize_score,
)


def _score_with_metadata() -> stream.Score:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Violin())
    part.insert(0, tempo.MetronomeMark(number=88))
    measure = stream.Measure(number=1)
    measure.insert(0, dynamics.Dynamic("f"))
    pitched = note.Note("C4", quarterLength=1)
    pitched.volume.velocity = 12
    measure.append(pitched)
    measure.append(chord.Chord(["E4", "G4"], quarterLength=1))
    part.append(measure)
    score.insert(0, part)
    return score


def test_standardize_score_is_non_mutating_and_replaces_nested_metadata():
    original = _score_with_metadata()

    standardized = standardize_score(
        original,
        StandardizationConfig(tempo_bpm=120, velocity=64),
    )

    assert isinstance(original.parts[0].getInstrument(), instrument.Violin)
    assert original.parts[0].recurse().notes[0].volume.velocity == 12
    assert list(original.recurse().getElementsByClass(dynamics.Dynamic))

    standardized_instruments = list(
        standardized.recurse().getElementsByClass(instrument.Instrument)
    )
    standardized_tempos = list(
        standardized.recurse().getElementsByClass(tempo.MetronomeMark)
    )
    assert len(standardized_instruments) == 1
    assert isinstance(standardized_instruments[0], instrument.Piano)
    assert [mark.number for mark in standardized_tempos] == [120]
    assert not list(standardized.recurse().getElementsByClass(dynamics.Dynamic))
    assert {pitched.volume.velocity for pitched in standardized.recurse().notes} == {64}


@pytest.mark.parametrize(
    ("tempo_bpm", "velocity", "message"),
    [
        (0, 64, "tempo_bpm"),
        (120, 128, "velocity"),
    ],
)
def test_standardization_config_rejects_invalid_values(
    tempo_bpm: float,
    velocity: int,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        StandardizationConfig(tempo_bpm=tempo_bpm, velocity=velocity)


def test_extract_note_events_expands_chords_and_collapses_ties():
    part = stream.Part()
    first = note.Note("C4", quarterLength=1)
    first.tie = tie.Tie("start")
    second = note.Note("C4", quarterLength=1)
    second.tie = tie.Tie("stop")
    part.append(first)
    part.append(second)
    part.append(chord.Chord(["E4", "G4"], quarterLength=2))

    assert extract_note_events(part) == (
        NoteEvent(0.0, 60, 2.0),
        NoteEvent(2.0, 64, 2.0),
        NoteEvent(2.0, 67, 2.0),
    )
    assert len(part.notes) == 3


def test_extract_note_events_accepts_an_empty_score():
    assert extract_note_events(stream.Score()) == ()


def test_evaluate_conversion_classifies_exact_warning_and_failure():
    source = tuple(NoteEvent(float(i), 60 + i, 1.0) for i in range(100))
    exact = evaluate_conversion(source, source)
    warning_candidate = list(source)
    warning_candidate[-1] = NoteEvent(99.0, 200, 1.0)
    warning = evaluate_conversion(source, warning_candidate)
    failure = evaluate_conversion(source, source[:-1])

    assert exact.status is ConversionStatus.PASS
    assert warning.status is ConversionStatus.PASS_WITH_WARNINGS
    assert warning.pitch_agreement == pytest.approx(0.99)
    assert failure.status is ConversionStatus.FAIL
    assert "Length mismatch" in failure.message


@pytest.mark.parametrize(
    ("converted", "expected_status", "expected_timing_agreement"),
    [
        (NoteEvent(0.019, 60, 1.0), ConversionStatus.PASS, 1.0),
        (NoteEvent(0.021, 60, 1.0), ConversionStatus.FAIL, 0.0),
        (NoteEvent(0.0, 60, 1.019), ConversionStatus.PASS, 1.0),
        (NoteEvent(0.0, 60, 1.021), ConversionStatus.FAIL, 0.0),
    ],
)
def test_evaluate_conversion_applies_tolerance_to_onset_and_duration(
    converted: NoteEvent,
    expected_status: ConversionStatus,
    expected_timing_agreement: float,
):
    report = evaluate_conversion(
        [NoteEvent(0.0, 60, 1.0)],
        [converted],
        tolerance=0.02,
    )

    assert report.status is expected_status
    assert report.pitch_agreement == 1.0
    assert report.timing_agreement == expected_timing_agreement


def test_safe_score_stem_is_deterministic_and_sanitized():
    first = safe_score_stem("folder/Unsafe score")
    second = safe_score_stem("folder/Unsafe score")

    assert first == second
    assert "/" not in first
    assert " " not in first


def test_export_and_validate_real_musicxml_roundtrip(tmp_path: Path):
    original = _score_with_metadata()

    result = process_score_to_xml(original, "example score", tmp_path)

    assert result.xml_path.suffix == ".xml"
    assert result.xml_path.is_file()
    assert result.report.status is ConversionStatus.PASS
    assert result.source_events == result.converted_events


def test_export_score_to_xml_always_uses_xml_suffix(tmp_path: Path):
    standardized = standardize_score(_score_with_metadata())

    output = export_score_to_xml(standardized, "piece.musicxml", tmp_path)

    assert output.suffix == ".xml"
    assert not output.name.endswith(".musicxml.xml")
