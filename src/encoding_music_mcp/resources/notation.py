"""Read notation pages without making another recorded tool call."""

import json

from ..tools.notation import show_notation


async def notation_page(
    filename: str,
    page: int,
    start_measure: int | None = None,
    end_measure: int | None = None,
) -> str:
    """Return a rendered page as JSON for widget pagination."""
    result = await show_notation(
        filename=filename,
        page=page,
        start_measure=start_measure,
        end_measure=end_measure,
    )
    return json.dumps(result.structured_content)
