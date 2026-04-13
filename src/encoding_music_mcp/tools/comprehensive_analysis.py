"""Tool wrapper for comprehensive MEI analysis."""

from fastmcp import Context

from ..prompts.comprehensive_analysis_sampled import analyze_piece_comprehensively

__all__ = ["run_comprehensive_analysis"]


async def run_comprehensive_analysis(filename: str, ctx: Context | None = None) -> str:
    """Run the comprehensive analysis workflow and return the final text."""
    return await analyze_piece_comprehensively(filename, ctx)
