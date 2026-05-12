"""Prompt registry - all prompts are registered here."""

from ..server import mcp
from .comprehensive_analysis import analyze_piece_comprehensively

# Register all prompts here
# To add a new prompt: import it, then add mcp.prompt()(your_prompt) below
mcp.prompt()(analyze_piece_comprehensively)
