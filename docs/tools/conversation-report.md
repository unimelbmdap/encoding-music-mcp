# Conversation Report

The `get_conversation_report` tool exports the successful tool calls recorded
during an analysis session as a JSON Lines (`.jsonl`) file.

Supports users who want reproducible analysis or later replay in structured format.

## Overview

Calls to eligible tools are recorded in order for the current session. The
report begins with a metadata record and is followed by one record per
successful tool call. Calling `get_conversation_report` returns that history as
an embedded resource named `conversation-report.jsonl`.

The export tool itself is excluded from the report. Failed tool calls and calls
without a session ID are not recorded.

It is intended to be the source of truth for tool usage within a session. The report is human-readable, allowing users to save a record of the session’s activity, and machine-readable, allowing another tool to reconstruct the tool-usage report.

This project uses the default in-memory store, so session state remains available until:
- end_session deletes it, or
- the server process stops or restarts.

Replay of tool calls from report is a planned feature. 

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | ID of the session whose conversation report should be exported. |

## Return Value

The tool returns a `ToolResult` containing:

- **Text content**: `The conversation report is attached.`
- **Embedded resource**: The report text at `file:///conversation-report.jsonl`
- **Structured content**: The output filename and MIME type

```json
{
  "filename": "conversation-report.jsonl",
  "mime_type": "application/jsonl"
}
```
## Report Format

Each line is an independent JSON object. The first line contains report
metadata:

```json
{"type":"conversation_report","version":"1","session_id":"session-123"}
```

Later lines describe successful tool calls in the order they completed:

```json
{"tool_name":"get_mei_metadata","args":{"filename":"Bach_BWV_0772.mei"}}
{"tool_name":"analyze_key","args":{"filename":"Bach_BWV_0772.mei"}}
```

The `session_id` argument used internally for recording is omitted from each
tool-call record.

The version identifies replay compatibility. Tool calls captured under a given version should reproduce the same outputs when replayed against functions with that version, provided the inputs and execution environment have not changed. Increment the version whenever a tool’s interface or behavior changes in a way that could affect replay results.

## Example Usage

after using a few tools, try asking in the same conversation:
"Download my conversation report"



## Typical Workflow

1. Run one or more analysis, notation, visualisation, or playback tools.
2. Ask the client to export or download the conversation report.
3. Save the returned `conversation-report.jsonl` file.


## Privacy and Security

This server does not currently authenticate users. A session ID therefore acts as a bearer credential: anyone with access to the server and a valid session ID may access the associated report. Do not include sensitive information in conversation reports. User-level session isolation requires authentication to be configured.


## Limitations

- Only successful calls with a session ID are recorded.
- Tool results are not included in the current report format.
- No authentication of user before returning tool report.
- Limited control over return formatting: Claude does not consistently provide JSONL output as a downloadable file. Instead, users must either open the tool-call payload manually or explicitly ask Claude to create a downloadable file.
- Forces every tool call to include session ID

