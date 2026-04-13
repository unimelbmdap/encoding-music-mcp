"""Lightweight MCP sampling diagnostics."""

from typing import Any

from fastmcp import Context

from ..prompts.comprehensive_analysis_sampled import _client_supports_sampling_tools

__all__ = ["diagnose_sampling"]


async def diagnose_sampling(ctx: Context | None = None) -> dict[str, Any]:
    """Report whether the current tool call has usable MCP sampling support."""
    if ctx is None:
        return {
            "status": "no_context",
            "has_context": False,
            "supports_sampling_tools": False,
            "sampling_attempted": False,
        }

    supports_sampling_tools = _client_supports_sampling_tools(ctx)

    try:
        sample = await ctx.sample(
            messages='Reply with exactly "sampling ok".',
            tools=None,
        )
    except ValueError as exc:
        return {
            "status": "sampling_unsupported",
            "has_context": True,
            "supports_sampling_tools": supports_sampling_tools,
            "sampling_attempted": True,
            "error": str(exc),
        }

    return {
        "status": "sampling_ok",
        "has_context": True,
        "supports_sampling_tools": supports_sampling_tools,
        "sampling_attempted": True,
        "sample_text": sample.text or str(sample.result),
    }
