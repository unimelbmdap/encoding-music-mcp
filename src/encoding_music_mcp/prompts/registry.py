"""Prompt registry - all prompts are registered here."""

from ..server import mcp
from .comprehensive_analysis import (
    analyze_piece_comprehensively as legacy_analyze_piece_comprehensively,
)
from .comprehensive_analysis_sampled import analyze_piece_comprehensively

# Register all prompts here
# To add a new prompt: import it, then add mcp.prompt()(your_prompt) below
mcp.prompt()(analyze_piece_comprehensively)
mcp.prompt(name="analyze_piece_comprehensively_legacy")(legacy_analyze_piece_comprehensively)
