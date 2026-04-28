# Uploaded MEI Files

The upload tools let an MCP client register local MEI file paths during the
current server session. Once registered, the filename works with the same tools
as built-in files, including `show_notation`, `get_notes`,
`get_melodic_ngrams`, `analyze_key`, visualisation tools, and `play_excerpt`.

The server stores the original path in the session registry. It does not accept
raw MEI/XML text and does not copy uploaded files into a temp cache.

```python
register_mei_file_from_path(
    file_path="C:\\Users\\name\\Downloads\\CRIM_Model_0002.mei",
    filename="CRIM_Model_0002.mei",
)
```

If the client supports elicitation, it can omit `file_path` and let the server
ask the user for the path:

```python
register_mei_file_from_path(filename="CRIM_Model_0002.mei")
```

## register_mei_file_from_path

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | `str | None` | No | Local path to a `.mei` file visible to the MCP server process. If omitted, the server elicits it from the user when supported. |
| `filename` | `str | None` | No | Session filename to register. Defaults to the path basename. |

Returns:

```python
{
    "filename": "CRIM_Model_0002.mei",
    "registered": True,
    "source_path": "C:\\Users\\name\\Downloads\\CRIM_Model_0002.mei",
    "message": "Registered CRIM_Model_0002.mei from local path ..."
}
```

The file path is validated by the MCP server, not by the model. Filenames must
be basenames ending in `.mei`; path-like names are rejected.

## Notes

Registered file paths are resolved before built-in files. Re-registering the
same filename replaces the active registration for that session.
