"""Comprehensive MEI file analysis prompt."""

__all__ = ["analyze_piece_comprehensively"]


def analyze_piece_comprehensively(filename: str) -> str:
    """Perform a comprehensive analysis of an MEI file.

    This prompt guides the LLM through a complete musical analysis including
    metadata extraction, key analysis, melodic/harmonic interval analysis,
    and cadence identification.

    Args:
        filename: Name of the MEI file to analyze (e.g., "Bach_BWV_0772.mei")

    Returns:
        A detailed prompt for comprehensive analysis
    """
    return f"""Perform a comprehensive musical analysis of the MEI file "{filename}".

Please conduct the following analyses and provide a structured summary:

1. **Metadata**: Extract and display basic information about the piece
   - Use get_mei_metadata("{filename}")
   - Include: title, composer, editors, publication date

2. **Key Analysis**: Determine the tonal center and confidence
   - Use analyze_key("{filename}")
   - Report the detected key and confidence score

3. **Melodic Content**: Analyze the melodic material
   - Use get_notes("{filename}") to see the pitch content
   - Use get_melodic_intervals("{filename}") to analyze melodic movement
   - Use get_melodic_ngrams("{filename}") to identify recurring melodic patterns

4. **Harmonic Content**: Analyze the harmonic intervals
   - Use get_harmonic_intervals("{filename}")
   - Identify predominant harmonic intervals and patterns

5. **Cadences**: Identify cadential patterns (especially for Renaissance/Baroque works)
   - Use get_cadences("{filename}") if applicable
   - Note: This is most relevant for polyphonic vocal music

6. **Summary**: Synthesize the findings into a coherent musical characterization
   - Describe the overall style and characteristics
   - Note any distinctive features or patterns
   - Provide context based on the composer and period

Please present your analysis in a clear, structured format suitable for musicological study."""
