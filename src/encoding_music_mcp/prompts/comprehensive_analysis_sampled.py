"""Sampled comprehensive MEI file analysis prompt."""

from fastmcp import Context
from mcp.types import ClientCapabilities, SamplingCapability, SamplingToolsCapability

from ..tools.intervals import (
    get_cadences,
    get_harmonic_intervals,
    get_melodic_intervals,
    get_melodic_ngrams,
    get_notes,
)
from ..tools.key_analysis import analyze_key
from ..tools.metadata import get_mei_metadata
from .comprehensive_analysis import (
    analyze_piece_comprehensively as render_legacy_comprehensive_analysis_prompt,
)

__all__ = ["analyze_piece_comprehensively", "analyze_piece_comprehensively_sampled"]

_ANALYSIS_TOOLS = [
    get_mei_metadata,
    analyze_key,
    get_notes,
    get_melodic_intervals,
    get_melodic_ngrams,
    get_harmonic_intervals,
    get_cadences,
]


def _client_supports_sampling_tools(ctx: Context) -> bool:
    """Return whether the connected client supports tool-enabled sampling."""
    return ctx.session.check_client_capability(
        ClientCapabilities(
            sampling=SamplingCapability(tools=SamplingToolsCapability()),
        )
    )


async def analyze_piece_comprehensively_sampled(filename: str, ctx: Context) -> str:
    """Perform comprehensive analysis through an MCP sampling request."""
    sample = await ctx.sample(
        messages=render_legacy_comprehensive_analysis_prompt(filename),
        tools=_ANALYSIS_TOOLS if _client_supports_sampling_tools(ctx) else None,
    )
    return sample.text or str(sample.result)


async def analyze_piece_comprehensively(filename: str, ctx: Context | None = None) -> str:
    """Default comprehensive analysis path with automatic sampling fallback."""
    if ctx is None:
        return "[legacy fallback]\n" + render_legacy_comprehensive_analysis_prompt(filename)

    try:
        return "[sampled path]\n" + await analyze_piece_comprehensively_sampled(filename, ctx)
    except ValueError as exc:
        if "Client does not support sampling" not in str(exc):
            raise
        return "[legacy fallback]\n" + render_legacy_comprehensive_analysis_prompt(filename)
