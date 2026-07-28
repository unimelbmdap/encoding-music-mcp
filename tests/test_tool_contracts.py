"""Protocol-level contract tests for MCP App tool results."""

import asyncio

import pytest
from fastmcp import Client

from src.encoding_music_mcp.server import mcp


def test_tool_schemas_survive_mcp_protocol_listing():
    """MCP clients should receive all structured-result and metadata contracts."""

    async def list_tools():
        async with Client(mcp) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    tools = asyncio.run(list_tools())
    structured_result_tools = {
        "show_notation",
        "show_notation_highlight",
        "plot_voice_ranges",
        "plot_weighted_note_distribution",
        "plot_melodic_ngram_heatmap",
        "plot_sonority_ngram_progress",
        "play_excerpt",
        "load_audio_resource",
    }

    missing_schemas = {
        name for name in structured_result_tools if tools[name].outputSchema is None
    }
    metadata_schema = tools["get_mei_metadata"].inputSchema

    assert missing_schemas == set()
    assert metadata_schema["required"] == ["filename"]
    assert metadata_schema["properties"]["filename"] == {"type": "string"}


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_key"),
    [
        (
            "show_notation",
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
