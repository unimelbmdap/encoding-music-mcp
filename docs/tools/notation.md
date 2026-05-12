# Notation Display

The `show_notation` tool renders MEI files as sheet music using [Verovio](https://www.verovio.org/), a lightweight music notation engraving library. The rendered notation is displayed inline via the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps).

## Prerequisites

This tool requires an MCP client that supports the MCP Apps extension (e.g., Claude Desktop with the extension enabled). Without the extension, the tool still returns a text description of the page being shown.

## Usage

### Full piece

!!! example "Try asking:"
    "Show me the notation for Bach_BWV_0772.mei"

Displays the first page of the piece with prev/next pagination controls.

When `filename` is omitted, or when the requested filename is not available and
the MCP client supports elicitation, the tool asks which MEI file to show. You
can select a built-in or registered filename, type another registered filename,
or type a local path to a `.mei` file on the machine running the MCP server.

### Specific measures

!!! example "Try asking:"
    "Show me measures 19 to 22 of Bach_BWV_0772.mei"

Filters the MEI to only include the requested measures before rendering.

### Page navigation

The notation viewer displays one system per page. For multi-page pieces, use the interactive prev/next buttons in the viewer, or request a specific page:

!!! example "Try asking:"
    "Show page 3 of Bach_BWV_0772.mei"

## show_notation_highlight

The `show_notation_highlight` tool renders the same notation payload as
`show_notation`, then adds a list of MEI note IDs for the viewer to highlight.
Use `resolve_note_ids_for_highlight`, `get_melodic_ngram_matches`, or
`get_first_occur_melodic_ngrams` to obtain note IDs from analysis locations.

Call this tool once for the requested score or excerpt. The widget handles page
navigation with the same highlight set, so clients do not need to call the tool
once per page.

### Highlight Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | string | Yes | None | MEI filename to render |
| `highlight_note_ids` | list[string] | Yes | None | MEI `xml:id` values to highlight |
| `start_measure` | integer | No | None | First measure to display |
| `end_measure` | integer | No | start_measure | Last measure to display |
| `page` | integer | No | 1 | Page number to display |

The structured result includes the same SVG and pagination fields as
`show_notation`, plus:

```python
{
    "highlight_note_ids": ["note-1", "note-2"]
}
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | string | No | None | MEI filename to render. If omitted or unavailable, the tool elicits a file when supported. |
| `start_measure` | integer | No | None | First measure to display |
| `end_measure` | integer | No | start_measure | Last measure to display |
| `page` | integer | No | 1 | Page number to display |

## Return Value

The tool returns a `ToolResult` with:

- **Text content**: A description of what is being shown (e.g., "Showing Bach_BWV_0772.mei, page 1 of 7")
- **Structured content**: SVG data and pagination metadata for the viewer app

```python
{
    "filename": "Bach_BWV_0772.mei",
    "svg": "<svg ...>...</svg>",
    "page": 1,
    "total_pages": 7,
    # If measure range was requested:
    "start_measure": 19,
    "end_measure": 22
}
```

## How It Works

1. If `filename` is omitted or unavailable, the tool elicits the exact MEI file when supported
2. Local paths entered through elicitation are registered for the current server session
3. The MEI file is read from the registered uploads or built-in collection
4. If `start_measure`/`end_measure` are specified, the MEI XML is filtered to include only those measures
5. Verovio renders the MEI to SVG server-side (one system per page, ~50-60KB per page)
6. The SVG is sent to the notation viewer app, which displays it in a sandboxed iframe
7. Pagination buttons in the viewer call `show_notation` again with a different `page` parameter

## Technical Details

- **Rendering engine**: Verovio 5.5+ (Python bindings, server-side)
- **Output format**: SVG, one system per page
- **Page size**: Each SVG page is approximately 50-60KB to stay within MCP transport limits
- **Viewer**: Custom HTML app using the `@modelcontextprotocol/ext-apps` SDK
