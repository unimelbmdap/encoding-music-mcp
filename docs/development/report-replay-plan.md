# Report Replay (Beta)

Report replay re-runs the tool calls saved by `get_conversation_report`. It is
currently a beta feature: the version 1 report contract is supported, but the
browser experience, response format, and security model may change.

## Scope

The feature has two entry points:

- The MCP tool `replay_report` returns a browser URL. With an active
  `session_id`, the URL points to that session's server-side report. Without a
  session ID, it points to the JSONL upload page.
- The HTTP routes `/reports/replay` and `/reports/replay/{session_id}` display
  the browser page and accept replay requests.

The MCP tool only returns the URL. Tool execution happens after the user opens
the page and selects **Replay tools**.

## Current Flow

1. `get_conversation_report` exports a version 1 JSONL report.
2. The browser sends either the uploaded JSONL or an active session ID to the
   replay route.
3. The parser validates the complete report before any saved tool runs.
4. The replay service creates a fresh temporary session.
5. Replayable calls run in their saved order. The fresh session ID replaces
   the historical ID where a tool accepts `session_id`.
6. The temporary session is closed, including when a replayed call fails.
7. The browser receives JSON containing the overall status and one result per
   saved call.

Replay bypasses conversation-report middleware, so replayed calls do not
create another report.

## Version 1 Input Contract

The first non-empty line must be:

```json
{"type":"conversation_report","version":"1","session_id":"session-123"}
```

Each later line must contain a tool name and an arguments object:

```json
{"tool_name":"analyze_key","args":{"filename":"Bach_BWV_0772.mei"}}
```

Validation rejects malformed JSON, duplicate headers, unsupported versions,
missing fields, non-object arguments, and any saved `session_id` argument.

## Replay Behaviour

Calls continue after an individual error. Each call is reported as `success`,
`error`, or `skipped`. The overall status is:

| Status | Meaning |
|--------|---------|
| `success` | Every saved call succeeded. |
| `partial` | Some calls succeeded or all calls were skipped. |
| `failed` | No call succeeded and at least one call failed. |
| `empty` | The report contained no calls. |

Unknown tools are preserved in the response as skipped calls. These tools are
also skipped because they mutate state, depend on temporary resources, or
could recursively create reports:

- `create_session`
- `end_session`
- `get_conversation_report`
- `load_audio_resource`
- `register_mei_file_from_path`
- `replay_report`

Ordinary replay results return JSON values. Binary and non-text content is
omitted, large strings are shortened, and base64 values are replaced with a
size summary. Successful MCP App calls retain their complete structured output
and render the registered `ui://` resource in a sandboxed iframe. If the app
cannot load, the page falls back to the JSON response.

The replay page acts as a small MCP Apps host. It reads the resource URI from
the registered tool metadata, completes the app handshake, and sends the saved
arguments and new result to the iframe. Interactive calls are restricted to
notation pagination and playback audio loading.

## Beta Limits

| Limit | Current value |
|-------|---------------|
| Report size | 1,000,000 bytes |
| Calls per report | 100 |
| Time per call | 120 seconds |
| Total replay time | 600 seconds |
| Output string length | 20,000 characters |

Structured lists and objects are limited to 500 entries at each level, and
deeply nested output is omitted after eight levels.

## Security

Uploaded reports are untrusted input. The implementation validates the whole
file before execution, blocks caller-supplied session IDs, uses a fresh
temporary session, and skips tools that can load local files or manage
sessions.

The server does not currently authenticate replay routes. A session-specific
URL is therefore a bearer credential: anyone who has the URL can replay that
active session's report. Do not include secrets or sensitive paths in reports.
Production deployments should add authentication and access control before
relying on session isolation.

Replay executes current tool code against current data. It is not a sandbox or
an exact historical reproduction, and its output can differ from the original
conversation.

## Local Development

The browser routes require HTTP transport:

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 uv run encoding-music-mcp
```

Open `http://localhost:8000/reports/replay`. When `replay_report` runs without
an HTTP request context, it returns a relative path rather than a complete URL.

Run the focused tests with:

```bash
uv run pytest tests/test_report_replay.py tests/test_report_replay_contract.py
```

The main implementation is split across:

- `tools/report_replay.py`: MCP URL helper
- `tools/reports/parser.py`: version 1 validation
- `tools/reports/replay.py`: ordered execution and output limits
- `tools/reports/routes.py`: HTTP routes and JSON response
- `tools/reports/html.py`: upload and session replay page

## Known Limitations

- Only report version 1 is accepted.
- Reports store inputs, not original outputs, timestamps, or tool versions.
- Session reports are held in memory and disappear when the session ends or
  the server restarts.
- Uploaded files cannot restore user-registered local MEI files.
- MCP App resources load their pinned browser SDK from a public CDN.
- App-initiated calls are limited to the explicit replay allowlist.
- Per-call internal diagnostic messages are not yet included in the HTTP JSON
  response.

## Beta Exit Criteria

Before treating replay as stable:

1. Add authentication and authorization for session-specific replay.
2. Define a versioning and migration policy for report formats.
3. Finalize the HTTP response and error contracts.
4. Add integration coverage using the deployed HTTP stack.
5. Decide whether reports need original outputs, tool versions, or timestamps.
6. Document retention and cleanup for any persistent report store.

## Related Documentation

- [Conversation Report](../tools/conversation-report.md)
- [Replay Report Tool](../tools/report-replay.md)
- [Testing](testing.md)
- [Project Structure](structure.md)
