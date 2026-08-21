"""Tests for chord-reduction notation."""

import asyncio
from pathlib import Path

import pytest
from mcp.types import TextContent
from music21 import chord, converter, note, stream

from src.encoding_music_mcp.tools.helpers import remove_uploaded_mei
from src.encoding_music_mcp.tools.chord_notation import (
    _build_chordified_score,
    show_chord_notation,
)


class _AcceptedElicitation:
    def __init__(self, data: str):
        self.data = data


class _FakeContext:
    def __init__(self, response: str):
        self.response = response
        self.messages = []

    async def elicit(self, message, response_type):
        self.messages.append((message, response_type))
        return _AcceptedElicitation(self.response)


def _bundled_score() -> Path:
    return (
        Path(__file__).parent.parent
        / "src"
        / "encoding_music_mcp"
        / "resources"
        / "mei_files"
        / "Bach_BWV_0772.mei"
    )


def _pitched_content(part: stream.Part) -> list[tuple[str, ...]]:
    """Return ordered pitch names for notes and chords in a part."""
    content = []
    for element in part.recurse().getElementsByClass([note.Note, chord.Chord]):
        if isinstance(element, note.Note):
            content.append((element.pitch.nameWithOctave,))
        else:
            content.append(tuple(pitch.nameWithOctave for pitch in element.pitches))
    return content


def test_chordified_score_appends_reduction_after_original_parts():
    """The display score should retain source parts before one derived part."""
    source_score = converter.parse(_bundled_score())
    display_score = _build_chordified_score(_bundled_score(), None, None)

    assert len(source_score.parts) == 2
    assert len(display_score.parts) == len(source_score.parts) + 1
    for source_part, display_part in zip(
        source_score.parts, display_score.parts[:-1], strict=True
    ):
        assert _pitched_content(display_part) == _pitched_content(source_part)


def test_chordified_score_final_part_contains_simultaneous_sonorities():
    """The appended reduction should contain closed octave-4 sonorities."""
    display_score = _build_chordified_score(_bundled_score(), None, None)

    sonorities = list(display_score.parts[-1].recurse().getElementsByClass(chord.Chord))
    assert sonorities
    assert any(len(sonority.pitches) > 1 for sonority in sonorities)
    assert all(sonority.bass().octave == 4 for sonority in sonorities)
    assert all(
        sonority.pitches[-1].midi - sonority.pitches[0].midi < 12
        for sonority in sonorities
    )


def test_measure_range_is_applied_to_chordified_score():
    """The inclusive range should select the same measures in every part."""
    display_score = _build_chordified_score(_bundled_score(), 3, 4)

    assert len(display_score.parts) == 3
    assert [
        [measure.number for measure in part.getElementsByClass(stream.Measure)]
        for part in display_score.parts
    ] == [[3, 4], [3, 4], [3, 4]]
    assert list(display_score.parts[-1].recurse().getElementsByClass(chord.Chord))


def test_no_measure_range_keeps_complete_combined_score():
    """Omitting the range should keep every source and reduction measure."""
    source_score = converter.parse(_bundled_score())
    display_score = _build_chordified_score(_bundled_score(), None, None)

    assert len(display_score.parts) == 3
    expected_measures_by_part = [
        [measure.number for measure in part.getElementsByClass(stream.Measure)]
        for part in source_score.parts
    ]
    assert all(expected_measures_by_part)
    assert [
        [measure.number for measure in part.getElementsByClass(stream.Measure)]
        for part in display_score.parts[:-1]
    ] == expected_measures_by_part
    assert [
        measure.number
        for measure in display_score.parts[-1].getElementsByClass(stream.Measure)
    ] == expected_measures_by_part[0]


def test_show_chord_notation_returns_selected_svg_and_one_summary_content_block():
    """The result should keep SVG structured and return one text summary."""
    high = asyncio.run(show_chord_notation("Bach_BWV_0772.mei", page=9999))

    assert high.structured_content["svg"].startswith("<svg")
    assert high.structured_content["notation_mode"] == "chord_reduction"
    assert high.structured_content["page"] == high.structured_content["total_pages"]
    assert len(high.content) == 1
    assert isinstance(high.content[0], TextContent)
    assert not high.content[0].text.lstrip().startswith("<svg")
    assert "page" in high.content[0].text


def test_show_chord_notation_clamps_low_page():
    """The requested initial page should clamp to the first returned SVG page."""
    result = asyncio.run(show_chord_notation("Bach_BWV_0772.mei", page=0))

    assert result.structured_content["page"] == 1


def test_notation_app_routes_only_chord_reduction_pages_to_chord_tool():
    """The shared app should preserve trusted mode, filename, range, and direction."""
    app_template = (
        Path(__file__).parent.parent
        / "src"
        / "encoding_music_mcp"
        / "resources"
        / "templates"
        / "notation_app.html"
    ).read_text(encoding="utf-8")

    assert (
        'currentState.notation_mode === "chord_reduction"\n'
        '                ? "show_chord_notation"\n'
        '                : "show_notation"'
    ) in app_template
    assert "const args = { filename: currentState.filename, page: newPage };" in (
        app_template
    )
    assert "args.start_measure = currentState.start_measure;" in app_template
    assert "args.end_measure = currentState.end_measure;" in app_template
    assert "app.callServerTool({ name: toolName, arguments: args })" in app_template
    assert "extractSvgPages" not in app_template
    assert "chord_pages" not in app_template
    assert "goToPage(currentState.page - 1);" in app_template
    assert "goToPage(currentState.page + 1);" in app_template


def test_show_chord_notation_defaults_end_measure_to_start():
    """A lone start measure should select that measure from the reduction."""
    result = asyncio.run(show_chord_notation("Bach_BWV_0772.mei", start_measure=3))

    assert result.structured_content["start_measure"] == 3
    assert result.structured_content["end_measure"] == 3
    assert result.structured_content["svg"].startswith("<svg")
    assert len(result.content) == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"start_measure": 0}, "start_measure must be at least 1"),
        ({"start_measure": 4, "end_measure": 3}, "less than or equal"),
        ({"end_measure": 3}, "end_measure requires start_measure"),
        ({"start_measure": 9999}, "No measures found"),
    ],
)
def test_show_chord_notation_rejects_invalid_measure_ranges(kwargs, message):
    """Invalid or empty ranges should fail with actionable errors."""
    with pytest.raises(ValueError, match=message):
        asyncio.run(show_chord_notation("Bach_BWV_0772.mei", **kwargs))


def test_show_chord_notation_rejects_missing_file():
    """Missing scores should retain the established notation error style."""
    with pytest.raises(FileNotFoundError, match="MEI file not found"):
        asyncio.run(show_chord_notation("missing-score.mei"))


def test_show_chord_notation_requires_filename_without_context():
    """Omitted input without an MCP context should keep a clear error."""
    with pytest.raises(ValueError, match="filename is required to show notation"):
        asyncio.run(show_chord_notation())


def test_show_chord_notation_elicits_omitted_filename():
    """Omitted chord filename should reuse notation's elicitation path."""
    ctx = _FakeContext("Bach_BWV_0772.mei")

    result = asyncio.run(show_chord_notation(ctx=ctx))

    assert ctx.messages
    assert "Which MEI file" in ctx.messages[0][0]
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"


def test_show_chord_notation_elicits_missing_filename():
    """An unavailable chord filename should be replaceable through elicitation."""
    ctx = _FakeContext("Bach_BWV_0772.mei")

    result = asyncio.run(show_chord_notation("missing-score.mei", ctx=ctx))

    assert ctx.messages
    assert "could not find" in ctx.messages[0][0]
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"


def test_show_chord_notation_registers_elicited_local_path():
    """A missing basename should be reused for an elicited local score."""
    filename = "Elicited_Chord_Copy.mei"
    remove_uploaded_mei(filename)
    ctx = _FakeContext(str(_bundled_score()))

    try:
        result = asyncio.run(show_chord_notation(filename, ctx=ctx))
    finally:
        remove_uploaded_mei(filename)

    assert ctx.messages
    assert result.structured_content["filename"] == filename
    assert result.structured_content["svg"].startswith("<svg")


def test_show_chord_notation_does_not_elicit_valid_filename():
    """An existing filename should bypass elicitation even with context."""
    ctx = _FakeContext("Bach_BWV_0773.mei")

    result = asyncio.run(show_chord_notation("Bach_BWV_0772.mei", ctx=ctx))

    assert ctx.messages == []
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"
