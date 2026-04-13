"""Tests for the comprehensive analysis tool wrapper."""

import asyncio

from src.encoding_music_mcp.prompts.comprehensive_analysis import (
    analyze_piece_comprehensively as render_legacy_comprehensive_analysis_prompt,
)
from src.encoding_music_mcp.tools import comprehensive_analysis as comprehensive_analysis_tool


class _FakeSamplingResult:
    def __init__(self, text: str | None, result: str) -> None:
        self.text = text
        self.result = result


def test_run_comprehensive_analysis_returns_sampled_text():
    """The tool should return the final sampled analysis text."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return True

    class FakeContext:
        def __init__(self) -> None:
            self.session = FakeSession()

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            assert messages == render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
            assert tools is not None
            return _FakeSamplingResult("Structured analysis", "fallback")

    result = asyncio.run(
        comprehensive_analysis_tool.run_comprehensive_analysis(
            "Bach_BWV_0772.mei",
            FakeContext(),
        )
    )

    assert result == "[sampled path]\nStructured analysis"


def test_run_comprehensive_analysis_falls_back_without_context():
    """The tool should preserve the prompt fallback behavior when no context exists."""

    result = asyncio.run(
        comprehensive_analysis_tool.run_comprehensive_analysis("Bach_BWV_0772.mei")
    )

    assert result == (
        "[legacy fallback]\n"
        + render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
    )


def test_run_comprehensive_analysis_falls_back_when_sampling_is_unsupported():
    """The tool should return the legacy prompt when sampling is unsupported."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return False

    class FakeContext:
        session = FakeSession()

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            raise ValueError("Client does not support sampling")

    result = asyncio.run(
        comprehensive_analysis_tool.run_comprehensive_analysis(
            "Bach_BWV_0772.mei",
            FakeContext(),
        )
    )

    assert result == (
        "[legacy fallback]\n"
        + render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
    )
