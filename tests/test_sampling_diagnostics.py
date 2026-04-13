"""Tests for the lightweight sampling diagnostic tool."""

import asyncio

from src.encoding_music_mcp.tools.sampling_diagnostics import diagnose_sampling


class _FakeSamplingResult:
    def __init__(self, text: str | None, result: str) -> None:
        self.text = text
        self.result = result


def test_diagnose_sampling_reports_missing_context():
    """The diagnostic tool should report when no MCP context is available."""
    result = asyncio.run(diagnose_sampling())

    assert result == {
        "status": "no_context",
        "has_context": False,
        "supports_sampling_tools": False,
        "sampling_attempted": False,
    }


def test_diagnose_sampling_reports_unsupported_sampling():
    """The diagnostic tool should report unsupported sampling cleanly."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return False

    class FakeContext:
        session = FakeSession()

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            assert messages == 'Reply with exactly "sampling ok".'
            assert tools is None
            raise ValueError("Client does not support sampling")

    result = asyncio.run(diagnose_sampling(FakeContext()))

    assert result == {
        "status": "sampling_unsupported",
        "has_context": True,
        "supports_sampling_tools": False,
        "sampling_attempted": True,
        "error": "Client does not support sampling",
    }


def test_diagnose_sampling_reports_success():
    """The diagnostic tool should confirm a successful tiny sampling call."""

    class FakeSession:
        def check_client_capability(self, capability: object) -> bool:
            return True

    class FakeContext:
        session = FakeSession()

        async def sample(self, *, messages: str, tools: list[object] | None = None):
            assert messages == 'Reply with exactly "sampling ok".'
            assert tools is None
            return _FakeSamplingResult("sampling ok", "fallback")

    result = asyncio.run(diagnose_sampling(FakeContext()))

    assert result == {
        "status": "sampling_ok",
        "has_context": True,
        "supports_sampling_tools": True,
        "sampling_attempted": True,
        "sample_text": "sampling ok",
    }
