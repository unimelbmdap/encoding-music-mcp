"""HTML page for uploading or replaying a conversation report."""

from .parser import MAX_REPORT_BYTES


def render_upload_page(*, session_mode: bool = False) -> str:
    """Render a file picker or a page for replaying the current session."""

    picker = (
        '<label for="report-file">Conversation report</label>\n'
        '    <input id="report-file" type="file" '
        'accept=".jsonl,application/jsonl,application/x-ndjson">'
        if not session_mode
        else "<p>This session's conversation report is ready to replay.</p>"
    )
    button_disabled = "" if session_mode else " disabled"
    #session_mode determines whether the page is for replaying the current session or uploading a report file.
    session_mode_json = "true" if session_mode else "false"

    return f"""<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Replay a conversation report</title>
  <style>
    body {{ max-width: 48rem; margin: 3rem auto; padding: 0 1rem; font: 1rem/1.5 sans-serif; }}
    main {{ display: grid; gap: 1rem; }}
    label, button {{ font: inherit; }}
    button {{ width: fit-content; padding: .5rem .8rem; }}
    pre {{ overflow: auto; padding: 1rem; background: #f3f5f7; white-space: pre-wrap; }}
    .error {{ color: #a12622; }}
  </style>
</head>
<body>
  <main>
    <h1>Replay a conversation report</h1>
    <p>Select a conversation-report JSONL file to replay its saved tool calls. The replay response contains JSON values only.</p>
    <p>JSONL version 1, up to {MAX_REPORT_BYTES // 1_000_000} MB.</p>
    {picker}
    <button id="open-report" type="button"{button_disabled}>Replay tools</button>
    <p id="client-error" class="error" role="alert" aria-live="polite"></p>
    <pre id="replay-result" hidden></pre>
  </main>
  <script>
    const sessionMode = {session_mode_json};
    const input = document.getElementById("report-file");
    const button = document.getElementById("open-report");
    const error = document.getElementById("client-error");
    const output = document.getElementById("replay-result");

    if (input) {{
      input.addEventListener("change", () => {{
        button.disabled = !input.files[0];
        error.textContent = "";
        output.hidden = true;
      }});
    }}

    button.addEventListener("click", async () => {{
      const file = input ? input.files[0] : null;
      if (!file && !sessionMode) return;

      if (file && file.size > {MAX_REPORT_BYTES}) {{
        error.textContent = "The selected report is larger than the permitted size.";
        return;
      }}

      button.disabled = true;
      button.textContent = "Replaying tools…";
      error.textContent = "";
      output.hidden = true;

      try {{
        const options = {{
          method: "POST",
          headers: {{
            "Accept": "application/json"
          }}
        }};
        // If a file is selected (upload mode), read its contents and set the Content-Type header to application/jsonl. 
        // If none is selected, post request is empty, which backend will handle
        if (file) {{
          options.headers["Content-Type"] = "application/jsonl";
          options.body = await file.text();
        }}
        const response = await fetch(window.location.pathname, options);
        const result = await response.json();
        if (!response.ok) {{
          error.textContent = result.error || "The report could not be replayed.";
          return;
        }}
        // Display the JSON result. #TODO improve formatting
        output.textContent = JSON.stringify(result, null, 2);
        output.hidden = false;
      }} catch {{
        error.textContent = "The report could not be sent to the replay server.";
      }} finally {{
        button.disabled = false;
        button.textContent = "Replay tools";
      }}
    }});
  </script>
</body>
</html>"""
