"""Behavioural tests for explicit and inferred chord progressions."""

from pathlib import Path

import pytest
from music21 import converter, pitch

from src.encoding_music_mcp.tools import get_chord_progression as chord_module


@pytest.fixture
def inferred_mei(tmp_path: Path) -> Path:
    """Create a two-staff, two-layer MEI score with distinct sonorities."""
    filepath = tmp_path / "inferred.mei"
    filepath.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="5.0">
  <music><body><mdiv><score>
    <scoreDef meter.count="4" meter.unit="4">
      <staffGrp>
        <staffDef n="1" lines="5" clef.shape="G" clef.line="2"/>
        <staffDef n="2" lines="5" clef.shape="F" clef.line="4"/>
      </staffGrp>
    </scoreDef>
    <section>
      <measure n="1">
        <staff n="1">
          <layer n="1"><note pname="c" oct="4" dur="1"/></layer>
          <layer n="2"><note pname="e" oct="4" dur="1"/></layer>
        </staff>
        <staff n="2">
          <layer n="1"><note pname="g" oct="3" dur="1"/></layer>
          <layer n="2"><note pname="b" oct="3" dur="1"/></layer>
        </staff>
      </measure>
      <measure n="2">
        <staff n="1">
          <layer n="1"><note pname="d" oct="4" dur="1"/></layer>
          <layer n="2"><note pname="f" oct="4" dur="1"/></layer>
        </staff>
        <staff n="2">
          <layer n="1"><note pname="a" oct="3" dur="1"/></layer>
          <layer n="2"><note pname="c" oct="4" dur="1"/></layer>
        </staff>
      </measure>
    </section>
  </score></mdiv></body></music>
</mei>
""",
        encoding="utf-8",
    )
    return filepath


def _use_score(monkeypatch: pytest.MonkeyPatch, filepath: Path) -> None:
    monkeypatch.setattr(chord_module, "get_mei_filepath", lambda filename: filepath)


def test_inspect_harmony_reports_bundled_crim_annotation():
    inspection = chord_module.inspect_harmony("CRIM_Mass_0030_5.mei")

    assert inspection.harmony_count == 1
    assert inspection.has_explicit_labels is True
    assert inspection.requires_inference is False
    assert inspection.staves == ["1", "2", "3", "4", "5"]
    assert inspection.layers == ["1"]


def test_explicit_harmony_preserves_figured_bass_location_and_provenance():
    events = chord_module.get_chord_progression("CRIM_Mass_0030_5.mei")

    assert [event.model_dump() for event in events] == [
        {
            "name": "6 5♯",
            "measure_number": 3,
            "beat_str": "2",
            "elements": [],
            "staff": "5",
            "layer": "1",
            "xml_id": "m-146",
            "source": "explicit_harm",
        }
    ]


def test_explicit_path_does_not_invoke_music21(monkeypatch: pytest.MonkeyPatch):
    def unexpected_parse(*args, **kwargs):
        raise AssertionError("music21 must not parse a fully annotated score")

    monkeypatch.setattr(converter, "parse", unexpected_parse)

    events = chord_module.get_chord_progression("CRIM_Mass_0030_5.mei")

    assert len(events) == 1
    assert events[0].source == "explicit_harm"


def test_score_without_usable_harmony_dispatches_to_music21(
    monkeypatch: pytest.MonkeyPatch,
    inferred_mei: Path,
):
    _use_score(monkeypatch, inferred_mei)

    inspection = chord_module.inspect_harmony("inferred.mei")
    events = chord_module.get_chord_progression("inferred.mei")

    assert inspection.harmony_count == 0
    assert inspection.has_explicit_labels is False
    assert inspection.requires_inference is True
    assert events
    assert [(event.measure_number, event.beat_str) for event in events] == sorted(
        (event.measure_number, event.beat_str) for event in events
    )
    assert all(event.source == "inferred" for event in events)
    assert all(event.xml_id is None for event in events)
    assert all(event.name for event in events)
    assert all(event.elements for event in events)


def test_inferred_simultaneous_layer_notes_form_c_major_triad(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    filepath = tmp_path / "c-major-layers.mei"
    filepath.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="5.0">
  <music><body><mdiv><score>
    <scoreDef meter.count="4" meter.unit="4">
      <staffGrp><staffDef n="1" lines="5" clef.shape="G" clef.line="2"/></staffGrp>
    </scoreDef>
    <section><measure n="1"><staff n="1">
      <layer n="1"><note pname="c" oct="4" dur="1"/></layer>
      <layer n="2"><note pname="e" oct="4" dur="1"/></layer>
      <layer n="3"><note pname="g" oct="4" dur="1"/></layer>
    </staff></measure></section>
  </score></mdiv></body></music>
</mei>
""",
        encoding="utf-8",
    )
    _use_score(monkeypatch, filepath)

    events = chord_module.get_chord_progression("c-major-layers.mei")

    assert len(events) == 1
    assert events[0].name == "C-major triad"
    assert events[0].elements == ["C4", "E4", "G4"]


def test_inferred_fields_use_normalized_music21_values(
    monkeypatch: pytest.MonkeyPatch,
    inferred_mei: Path,
):
    class FakeSonority:
        pitches = (pitch.Pitch("C4"), pitch.Pitch("E4"))
        pitchedCommonName = "C-major third"
        measureNumber = None
        beatStr = "1  1/3"
        offset = 0.0

    class FakeFlat:
        def getElementsByClass(self, element_class):
            return [FakeSonority()]

    class FakeChordified:
        def flatten(self):
            return FakeFlat()

    class FakeMaterial:
        def chordify(self):
            return FakeChordified()

    _use_score(monkeypatch, inferred_mei)
    monkeypatch.setattr(converter, "parse", lambda filepath: object())
    monkeypatch.setattr(
        chord_module,
        "_select_music21_material",
        lambda score, staff_ids, staff, layer: FakeMaterial(),
    )

    event = chord_module.get_chord_progression("inferred.mei")[0]

    assert event.name == "C-major third"
    assert event.measure_number is None
    assert event.beat_str == "1 1/3"
    assert event.elements == ["C4", "E4"]
    assert event.xml_id is None
    assert event.source == "inferred"


def test_explicit_measure_staff_and_layer_filters():
    assert (
        len(
            chord_module.get_chord_progression(
                "CRIM_Mass_0030_5.mei",
                start_measure=3,
                end_measure=3,
                staff="5",
                layer="1",
            )
        )
        == 1
    )
    assert (
        chord_module.get_chord_progression("CRIM_Mass_0030_5.mei", start_measure=4)
        == []
    )
    assert chord_module.get_chord_progression("CRIM_Mass_0030_5.mei", staff="1") == []


def test_inferred_measure_staff_and_layer_filters(
    monkeypatch: pytest.MonkeyPatch,
    inferred_mei: Path,
):
    _use_score(monkeypatch, inferred_mei)

    measure_events = chord_module.get_chord_progression(
        "inferred.mei", start_measure=2, end_measure=2
    )
    staff_events = chord_module.get_chord_progression("inferred.mei", staff="1")
    layer_events = chord_module.get_chord_progression("inferred.mei", layer="1")

    assert measure_events and {event.measure_number for event in measure_events} == {2}
    assert staff_events and {event.staff for event in staff_events} == {"1"}
    assert layer_events and {event.layer for event in layer_events} == {"1"}
    assert {event.name for event in staff_events} != {
        event.name for event in layer_events
    }


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"start_measure": 0}, "start_measure must be at least 1"),
        ({"end_measure": 0}, "end_measure must be at least 1"),
        (
            {"start_measure": 4, "end_measure": 3},
            "start_measure must be less than or equal to end_measure",
        ),
        ({"staff": "99"}, "Unknown staff '99'"),
        ({"layer": "99"}, "Unknown layer '99'"),
    ],
)
def test_invalid_filters_raise_clear_value_errors(arguments, message):
    with pytest.raises(ValueError, match=message):
        chord_module.get_chord_progression("CRIM_Mass_0030_5.mei", **arguments)


@pytest.mark.parametrize(
    "function", [chord_module.inspect_harmony, chord_module.get_chord_progression]
)
def test_missing_files_raise_file_not_found(function):
    with pytest.raises(FileNotFoundError, match="MEI file not found: missing.mei"):
        function("missing.mei")
