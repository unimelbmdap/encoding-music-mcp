# Reports

`src/encoding_music_mcp/tools/reports/` parses saved conversation reports,
re-executes their tool calls, and displays results in a browser. Replay uses
current code and MEI data; it does not reproduce stored outputs.

## Package map

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package marker; no registration side effects. |
| `models.py` | `ReportHeader`, `RecordedCall`, and `ConversationReport` describe input; `ReplayedCall` and `ReplayResult` hold outcomes. |
| `settings.py` | Route paths, report version and input limits; `base_url()` uses the HTTP request origin or returns a relative path. The SDK version constant is currently unused. |
| `parser.py` | `parse_report_jsonl()` validates the complete input and builds ordered records before execution. |
| `replay.py` | Sequential execution, timeouts, skipped tools, result summaries, and app resource discovery from tool metadata. |
| `routes.py` | Registers HTTP endpoints, serializes replay/tool results, and serves app HTML with a Content Security Policy (CSP). |
| `html.py` | Upload/session page, collapsible results and index, and an inline MCP Apps messaging bridge. Supports light/dark themes. |
| `testfile.jsonl` | Sample report containing chart and notation calls for manual replay. |

Outside this package, `middleware.py` records successful calls with a session ID;
`tools/conversation_report.py` stores and exports them; `tools/report_replay.py`
provides the MCP URL helper. `server.py` registers the HTTP routes.

## Recording and replay

Tools arguments are recorded and saved as a conversation report, tied to a specific session.
* `get_conversation_report` returns an embedded JSONL
resource plus filename, MIME type, and upload URL. A session with no recorded
calls exports empty text, which the parser rejects.

`replay_report(session_id=None)` returns a upload URL for conversation reports, which can then be replayed. Session_id argument will be provided when you are in active conversation with agent, and will automatically contain that conversation's tool calls. 
Opening the URL does not execute tools: **Replay tools** sends
the POST request (from html.py to routes.py). The parser validates the report, then calls execute in order.

Replay and app follow-up calls use `run_middleware=False`: they neither record
new history nor create, inject, or clean up sessions. `expose_session_id` makes
the recording parameter optional on ordinary tools. The header's original ID
is metadata only; retrieving an active report still requires its session ID.

## JSONL contract

The first nonblank line is a version `"1"` header; subsequent lines are calls:

```json
{"type":"conversation_report","version":"1","session_id":"session-123"}
{"tool_name":"analyze_key","args":{"filename":"Bach_BWV_0772.mei"}}
```

Blank lines are ignored. Invalid JSON, non-object records, unsupported versions,
missing/invalid fields, duplicate headers, and `session_id` in saved arguments
raise `ValueError`. Errors identify source lines where applicable. Calls receive
zero-based positions and IDs such as `call-0001`. FastMCP validates tool arguments
when executing; parsing does not guarantee execution success.

## HTTP routes

Paths below are relative to `/reports/replay`.

| Path | Method | Behaviour |
|------|--------|-----------|
| (base path) | GET / POST | Serve upload HTML / replay UTF-8 JSONL from the request body. |
| `/{session_id}` | GET / POST | Serve session HTML / retrieve and replay the stored report. |
| `/apps/{tool_name}` | GET | Read `tool.meta["ui"]["resourceUri"]` and return the app HTML. |
| `/app-call` | POST | Execute `{ "tool_name": "…", "arguments": {} }`; return MCP-shaped `content`, `structuredContent`, and `isError`. |

Register `/app-call` before `/{session_id}` so it is not interpreted as a session
ID. Both app endpoints convert exceptions to HTTP 500 with `{"error": "…"}`.
Upload/session parsing and retrieval exceptions currently propagate to the
server rather than receiving that JSON error wrapper.

Replay responses contain `status` and ordered `calls`. Each call includes
`tool_name`, `arguments`, `status`, `output`, and an optional `message`.
Successful app calls also include `app` with its resource URI, browser URL,
and MCP-shaped result.

## Outcomes and limits

Individual calls are `success`, `error`, or `skipped`; execution continues after
call failures. Unknown tools are skipped, as are `create_session`, `end_session`,
`get_conversation_report`, `replay_report`, `register_mei_file_from_path`, and
`load_audio_resource` in saved reports.

| Overall status | Meaning |
|----------------|---------|
| `success` | Every call succeeded. |
| `partial` | Mixed outcomes with at least one success, or all calls skipped. |
| `failed` | At least one error and no successes. |
| `empty` | Valid header with no calls. |

Defaults: **1,000,000 input bytes**, **100 calls**, **120 seconds per call**,
**600 seconds per replay**. Remaining calls are skipped when the replay budget
expires. App follow-up calls have their own 120-second timeout.

Ordinary output summaries cap strings at 20,000 characters, collections at 500
entries per level, and nesting beyond eight levels. Binary/non-text content and
base64 fields become summaries. Successful apps retain full JSON-compatible
structured results; these summary limits do not bound app payloads.

## Browser apps

The iframe URL loads app HTML; the parent bridge then sends saved arguments and
new results over `postMessage`. The bridge handles initialization, resizing,
pings, and tool calls forwarded through `/app-call`. App heights are clamped to
240–1,200 px. Load/initialization failures fall back to JSON after at most a
10-second initialization wait. JSON is rendered as text, not HTML.

Iframes use `sandbox="allow-scripts"` and no referrer. The CSP blocks resources
by default, allows inline scripts/styles and scripts/connections to unpkg,
data/blob images, and blob media. App templates load their SDK from the CDN;
the parent bridge is implemented inline. These browser restrictions do not
restrict server-side tools: app follow-up calls can invoke any registered tool,
without a per-app allowlist or the saved-report skip list.

## Limitations and development

Routes are unauthenticated; possession of a session URL allows access to that
report. Session history is in memory and disappears on deletion or restart.
Reports contain no original outputs, timestamps, or tool versions, and cannot
restore uploaded MEI files. Replay is not a tool-execution sandbox or a
transaction with rollback.

Future work includes authentication, format migration policy, consistent HTTP
errors, deployed-stack integration tests, and decisions about richer reports
and persistent retention.

```bash
# Open http://localhost:8000/reports/replay
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 uv run encoding-music-mcp

# Tests: parser, replay, routes, export, and registered tool schemas
uv run pytest tests/test_report_replay.py tests/test_report_replay_contract.py tests/test_conversation_report.py tests/test_tool_contracts.py
```

User guides: [Conversation Report](../tools/conversation-report.md) and
[Replay Report](../tools/report-replay.md).
