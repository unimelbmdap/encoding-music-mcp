# Use a manually maintained replay compatibility version

Conversation report exports carry a `replay_version` maintained independently of the encoding-music-mcp package version, FastMCP version, advertised server version, and negotiated MCP protocol. This makes replay compatibility an explicit product decision instead of assuming that unrelated version numbers track changes to report structure or tool-call semantics. Maintainers increment it for incompatible report-schema or tool-contract changes; compatible additions do not require a bump.
