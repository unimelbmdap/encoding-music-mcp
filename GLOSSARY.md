# Conversation Reporting

Terms for capturing and exporting the activity of an encoding-music-mcp session.

## Language

**Conversation Report**:
An ordered, session-scoped record comprising report metadata followed by successful tool calls. Its metadata identifies the source session; its tool-call records contain each tool name and supplied arguments but not tool results, export calls, or conversational prose.
_Avoid_: Transcript, chat history, complete conversation

**Report Export**:
A downloadable, versioned JSON Lines snapshot of a non-empty Conversation Report at the time the user requests it. It contains the source session ID and is intended to support later replay, but does not contain original tool results.
_Avoid_: Automatic backup, live report

**Report Replay**:
Later re-execution of the tool calls captured by a Report Export. Replay requires a compatible Version plus the same unchanged MEI inputs; it does not promise byte-identical original results.
_Avoid_: Restore, exact reproduction

**Replay Version**:
A manually assigned compatibility identifier shared by Report Exports and future replay implementations. Equal values indicate that replay compatibility is intended; the identifier is independent of package, framework, and protocol versions.
_Avoid_: Package version, FastMCP version, MCP protocol version
