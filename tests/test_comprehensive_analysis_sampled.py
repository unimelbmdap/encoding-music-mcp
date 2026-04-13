"""Tests for sampled comprehensive analysis prompt."""

import asyncio

from src.encoding_music_mcp.prompts.comprehensive_analysis import (
    analyze_piece_comprehensively as render_legacy_comprehensive_analysis_prompt,
)
from src.encoding_music_mcp.prompts.comprehensive_analysis_sampled import (
    analyze_piece_comprehensively,
    analyze_piece_comprehensively_sampled,
)


class _FakeSamplingResult:
    def __init__(self, text: str | None, result: str) -> None:
        self.text = text
        self.result = result


def test_sampled_comprehensive_analysis_uses_tool_enabled_sampling_when_supported():
    """The sampled prompt should expose analysis tools when the client supports them."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return True

    class FakeContext:
        def __init__(self) -> None:
            self.session = FakeSession()
            self.calls: list[dict[str, object]] = []

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            self.calls.append({"messages": messages, "tools": tools})
            return _FakeSamplingResult("Sampled analysis", "fallback")

    ctx = FakeContext()

    result = asyncio.run(
        analyze_piece_comprehensively_sampled("Bach_BWV_0772.mei", ctx)
    )

    assert result == "Sampled analysis"
    assert ctx.calls == [{
        "messages": render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei"),
        "tools": ctx.calls[0]["tools"],
    }]
    assert ctx.calls[0]["tools"] is not None
    assert len(ctx.calls[0]["tools"]) == 7


def test_sampled_comprehensive_analysis_falls_back_to_plain_sampling():
    """The sampled prompt should omit tools when the client lacks tool sampling support."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return False

    class FakeContext:
        def __init__(self) -> None:
            self.session = FakeSession()

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            assert messages == render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
            assert tools is None
            return _FakeSamplingResult(None, "Fallback analysis")

    result = asyncio.run(
        analyze_piece_comprehensively_sampled("Bach_BWV_0772.mei", FakeContext())
    )

    assert result == "Fallback analysis"


def test_default_comprehensive_analysis_uses_sampling_when_context_is_available():
    """The canonical prompt should sample when MCP context is present."""

    class FakeContext:
        async def sample(self, *, messages: str, tools: list[object] | None = None):
            return _FakeSamplingResult("Sampled default analysis", "fallback")

        session = type("FakeSession", (), {"check_client_capability": lambda self, capability: True})()

    result = asyncio.run(
        analyze_piece_comprehensively("Bach_BWV_0772.mei", FakeContext())
    )

    assert result == "[sampled path]\nSampled default analysis"


def test_default_comprehensive_analysis_falls_back_to_legacy_prompt_without_context():
    """The canonical prompt should preserve legacy behavior when no context exists."""
    result = asyncio.run(analyze_piece_comprehensively("Bach_BWV_0772.mei"))

    assert result == (
        "[legacy fallback]\n"
        + render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
    )


def test_default_comprehensive_analysis_falls_back_when_sampling_is_unsupported():
    """The canonical prompt should fall back to the legacy prompt on sampling capability errors."""

    class FakeContext:
        async def sample(self, *, messages: str, tools: list[object] | None = None):
            raise ValueError("Client does not support sampling")

        session = type("FakeSession", (), {"check_client_capability": lambda self, capability: False})()

    result = asyncio.run(
        analyze_piece_comprehensively("Bach_BWV_0772.mei", FakeContext())
    )

    assert result == (
        "[legacy fallback]\n"
        + render_legacy_comprehensive_analysis_prompt("Bach_BWV_0772.mei")
    )
