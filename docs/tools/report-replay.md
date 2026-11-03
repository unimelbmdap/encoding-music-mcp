# Replay Report (Beta)

The `replay_report` tool returns the browser URL used to replay a conversation
report. It does not execute the report itself.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | No | Active session to replay. Omit it to open the JSONL upload page. |

## Return Value

A URL string:

```text
https://example.test/reports/replay/session-123
```

Without `session_id`, the tool returns the upload page:

```text
https://example.test/reports/replay
```

When no HTTP request context is available, the result is a relative path such
as `/reports/replay/session-123`.

## Usage

For an active session:

1. Ask the client to call `replay_report` with the current `session_id`.
2. Open the returned URL.
3. Select **Replay tools**.

For an exported report, call `replay_report` without a session ID, open the
returned upload page, and select the `.jsonl` file from
`get_conversation_report`.

The replay runs saved calls against the current server. Ordinary results are
shown as JSON, while successful MCP App tools use their interactive iframe.
If an app cannot load, its JSON response is shown instead. Results may differ
from the original run. See the
[beta development notes](../development/report-replay-plan.md) for limits,
skipped tools, and security details.
