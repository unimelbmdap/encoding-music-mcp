# Use an MCP App for report downloads

Conversation reports use an MCP App with an explicit **Download report** button and the host-mediated `ui/download-file` request. A plain-text JSONL tool result remains available as the cross-client fallback. FastMCP's generic `File` helper was rejected because its `application/jsonl` blob is interpreted by Claude Desktop as an unsupported image, while relying on generic embedded-resource rendering cannot guarantee a download action across Claude clients.
