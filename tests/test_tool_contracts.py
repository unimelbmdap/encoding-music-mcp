"""Protocol-level contract tests for MCP App tool results."""

import asyncio

import pytest
from fastmcp import Client
from mcp.types import TextContent

from src.encoding_music_mcp.server import mcp


@pytest.fixture(autouse=True)
def run_fastmcp_sync_tools_inline(monkeypatch: pytest.MonkeyPatch):
    """Bypass only the sandbox-broken FastMCP worker-thread transport.

    Tool lookup, Pydantic argument validation, result conversion, and schema
    validation remain on FastMCP's registered boundary; only execution of the
    already-validated synchronous callable runs inline for this test module.
    """
    from fastmcp.tools import function_tool

    async def call_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(function_tool, "call_sync_fn_in_threadpool", call_inline)


def test_tool_schemas_survive_mcp_protocol_listing():
    """MCP clients should receive all structured-result and metadata contracts."""

    async def list_tools():
        async with Client(mcp) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    tools = asyncio.run(list_tools())
    structured_result_tools = {
        "show_notation",
        "show_chord_notation",
        "show_notation_highlight",
        "plot_voice_ranges",
        "plot_weighted_note_distribution",
        "plot_melodic_ngram_heatmap",
        "plot_sonority_ngram_progress",
        "play_excerpt",
        "load_audio_resource",
        "inspect_harmony",
        "get_chord_progression",
    }

    missing_schemas = {
        name for name in structured_result_tools if tools[name].outputSchema is None
    }
    metadata_schema = tools["get_mei_metadata"].inputSchema
    inspect_schema = tools["inspect_harmony"].inputSchema
    progression_schema = tools["get_chord_progression"].inputSchema
    progression_output = tools["get_chord_progression"].outputSchema
    chord_notation = tools["show_chord_notation"]

    assert missing_schemas == set()
    assert metadata_schema["required"] == ["filename"]
    assert metadata_schema["properties"]["filename"] == {"type": "string"}
    assert inspect_schema["required"] == ["filename"]
    assert inspect_schema["properties"]["filename"] == {"type": "string"}
    assert progression_schema["required"] == ["filename"]
    assert set(progression_schema["properties"]) == {
        "filename",
        "start_measure",
        "end_measure",
        "staff",
        "layer",
    }
    event_schema = progression_output["properties"]["result"]["items"]
    assert set(event_schema["properties"]) == {
        "name",
        "measure_number",
        "beat_str",
        "elements",
        "staff",
        "layer",
        "xml_id",
        "source",
    }
    assert event_schema["required"] == [
        "name",
        "measure_number",
        "beat_str",
        "elements",
        "staff",
        "layer",
        "xml_id",
        "source",
    ]
    assert "required" not in chord_notation.inputSchema
    assert set(chord_notation.outputSchema["properties"]) == {
        "filename",
        "svg",
        "page",
        "total_pages",
        "start_measure",
        "end_measure",
        "notation_mode",
    }
    assert chord_notation.outputSchema["properties"]["notation_mode"] == {
        "type": "string",
        "const": "chord_reduction",
    }
    assert "notation_mode" in chord_notation.outputSchema["required"]
    assert chord_notation.meta["ui"]["resourceUri"] == "ui://notation/view.html"


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_key"),
    [
        (
            "show_notation",
            {"filename": "Bach_BWV_0772.mei"},
            "svg",
        ),
        (
            "show_chord_notation",
            {"filename": "Bach_BWV_0772.mei"},
            "svg",
        ),
        (
            "show_notation_highlight",
            {
                "filename": "Bach_BWV_0772.mei",
                "highlight_note_ids": [],
            },
            "highlight_note_ids",
        ),
        (
            "plot_voice_ranges",
            {"filename": "Bach_BWV_0772.mei"},
            "staff_ranges",
        ),
        (
            "plot_weighted_note_distribution",
            {"filename": "Bach_BWV_0772.mei"},
            "traces",
        ),
        (
            "plot_melodic_ngram_heatmap",
            {
                "filename": "Bach_BWV_0772.mei",
                "top_n": 1,
            },
            "occurrences",
        ),
        (
            "plot_sonority_ngram_progress",
            {"filename": "Bartok_Mikrokosmos_022.mei"},
            "occurrences",
        ),
    ],
)
def test_app_tool_results_conform_to_registered_output_schemas(
    tool_name: str,
    arguments: dict[str, object],
    expected_key: str,
):
    """FastMCP should validate and preserve every app's structured payload."""
    result = asyncio.run(mcp.call_tool(tool_name, arguments))

    assert result.structured_content is not None
    assert expected_key in result.structured_content
    if tool_name == "show_chord_notation":
        assert result.structured_content["notation_mode"] == "chord_reduction"
        assert result.structured_content["svg"].startswith("<svg")
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert not result.content[0].text.lstrip().startswith("<svg")


def test_metadata_result_survives_registered_tool_boundary():
    """The metadata tool should be callable using its advertised filename schema."""
    result = asyncio.run(
        mcp.call_tool(
            "get_mei_metadata",
            {"filename": "Bach_BWV_0772.mei"},
        )
    )

    assert result.structured_content is not None
    assert result.structured_content["composer"] == "Bach, Johann Sebastian"


def test_harmony_tools_survive_registered_tool_boundary():
    """Both harmony tools should return structured data through FastMCP."""
    inspection = asyncio.run(
        mcp.call_tool("inspect_harmony", {"filename": "CRIM_Mass_0030_5.mei"})
    )
    progression = asyncio.run(
        mcp.call_tool("get_chord_progression", {"filename": "CRIM_Mass_0030_5.mei"})
    )

    assert inspection.structured_content is not None
    assert inspection.structured_content["harmony_count"] == 1
    assert progression.structured_content is not None
    assert progression.structured_content["result"][0] == {
        "name": "6 5♯",
        "measure_number": 3,
        "beat_str": "2",
        "elements": [],
        "staff": "5",
        "layer": "1",
        "xml_id": "m-146",
        "source": "explicit_harm",
    }
