"""HTML page for uploading or replaying a conversation report."""

from .parser import MAX_REPORT_BYTES
from .settings import MCP_APPS_SDK_VERSION, REPLAY_APP_CALL_PATH


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
    body {{ max-width: 72rem; margin: 3rem auto; padding: 0 1rem; font: 1rem/1.5 sans-serif; }}
    main {{ display: grid; gap: 1rem; }}
    label, button {{ font: inherit; }}
    button {{ width: fit-content; padding: .5rem .8rem; }}
    .replay-results {{ display: grid; grid-template-columns: 14rem minmax(0, 1fr); gap: 1rem; align-items: start; }}
    [hidden] {{ display: none !important; }}
    .tool-index {{ position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; overflow-wrap: anywhere; }}
    .tool-index ol {{ margin: .5rem 0; padding-left: 2rem; }}
    .tool-index a {{ display: block; padding: .25rem; color: inherit; }}
    .tool-calls {{ display: grid; gap: 1rem; min-width: 0; }}
    .tool-call {{ scroll-margin-top: 1rem; }}
    .tool-call:target {{ outline: 2px solid #476b9b; }}
    @media (max-width: 48rem) {{
      .replay-results {{ grid-template-columns: 1fr; }}
      .tool-index {{ position: static; max-height: 12rem; }}
    }}
    .tool-call {{ border: 1px solid #c8cdd3; border-radius: .4rem; overflow: hidden; }}
    .tool-call header {{ padding: 1rem; background: #f3f5f7; }}
    .tool-call h2 {{ margin: 0; font-size: 1.1rem; }}
    .tool-call h2:has([aria-expanded="true"]) {{ margin-bottom: .75rem; }}
    .tool-arguments, .tool-response {{ padding: 1rem; }}
    .tool-arguments {{ padding: 0; }}
    .tool-response {{ border-top: 1px solid #c8cdd3; }}
    .tool-call h3 {{ margin: 0 0 .5rem; font-size: 1rem; }}
    .collapse-toggle {{ padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; cursor: pointer; }}
    .collapse-toggle::before {{ content: "▾"; display: inline-block; width: 1.2em; }}
    .collapse-toggle[aria-expanded="false"]::before {{ content: "▸"; }}
    .tool-app-frame {{ width: 100%; min-height: 28rem; border: 0; background: white; }}
    .app-fallback-note {{ margin: 0 0 .75rem; }}
    pre {{ overflow: auto; margin: 0; white-space: pre-wrap; }}
    .error {{ color: #a12622; }}
  </style>
</head>
<body>
  <main>
    <h1>Replay a conversation report</h1>
    <p>Select a conversation-report JSONL file to replay its saved tool calls. MCP App results are displayed in their interactive views.</p>
    <p>JSONL version 1, up to {MAX_REPORT_BYTES // 1_000_000} MB.</p>
    {picker}
    <button id="open-report" type="button"{button_disabled}>Replay tools</button>
    <p id="client-error" class="error" role="alert" aria-live="polite"></p>
    <section id="replay-result" class="replay-results" hidden aria-live="polite"></section>
  </main>
  <script>
    const sessionMode = {session_mode_json};
    const input = document.getElementById("report-file");
    const button = document.getElementById("open-report");
    const error = document.getElementById("client-error");
    const output = document.getElementById("replay-result");
    class PostMessageTransport {{
      constructor(target, source) {{
        this.target = target;
        this.source = source;
        this.onmessage = null;
        this._handler = (event) => {{
          if (event.source !== this.source) return;
          let data = event.data;
          if (typeof data === "string") {{
            try {{ data = JSON.parse(data); }} catch (_) {{ return; }}
          }}
          if (this.onmessage) this.onmessage(data);
        }};
      }}
      start() {{
        window.addEventListener("message", this._handler);
      }}
      close() {{
        window.removeEventListener("message", this._handler);
      }}
      send(message) {{
        this.target?.postMessage(message, "*");
      }}
    }}

    class AppBridge {{
      constructor(client, hostInfo, capabilities, options = {{}}) {{
        this.hostInfo = hostInfo || {{ name: "encoding-music-report-replay", version: "1.0.0" }};
        this.capabilities = capabilities || {{}};
        this.hostContext = options.hostContext || {{}};
        this.transport = null;
        this.onsizechange = null;
        this.oncalltool = null;
        this.oninitialized = null;
      }}

      async connect(transport) {{
        this.transport = transport;
        transport.onmessage = async (data) => {{
          if (!data || typeof data !== "object") return;

          if (data.method === "ui/initialize") {{
            transport.send({{
              jsonrpc: "2.0",
              id: data.id,
              result: {{
                protocolVersion: data.params?.protocolVersion || "0.1.0",
                hostInfo: this.hostInfo,
                hostCapabilities: this.capabilities,
                hostContext: this.hostContext
              }}
            }});
            return;
          }}

          if (data.method === "ui/notifications/initialized" || data.method === "ui/initialized") {{
            if (this.oninitialized) await this.oninitialized();
            return;
          }}

          if (data.method === "ui/notifications/size-changed" || data.method === "ui/sizeChange") {{
            if (this.onsizechange) this.onsizechange(data.params || {{}});
            return;
          }}

          if (data.method === "tools/call") {{
            if (this.oncalltool) {{
              try {{
                const res = await this.oncalltool(data.params || {{}});
                transport.send({{ jsonrpc: "2.0", id: data.id, result: res }});
              }} catch (err) {{
                transport.send({{
                  jsonrpc: "2.0",
                  id: data.id,
                  error: {{ code: -32603, message: err.message || "Tool execution failed" }}
                }});
              }}
            }}
            return;
          }}

          if (data.method === "ping") {{
            transport.send({{ jsonrpc: "2.0", id: data.id, result: {{}} }});
            return;
          }}
        }};
        transport.start();
      }}

      close() {{
        this.transport?.close();
      }}

      async sendToolInput(params) {{
        this.transport?.send({{
          jsonrpc: "2.0",
          method: "ui/notifications/tool-input",
          params: params || {{}}
        }});
      }}

      async sendToolResult(result) {{
        this.transport?.send({{
          jsonrpc: "2.0",
          method: "ui/notifications/tool-result",
          params: result || {{}}
        }});
      }}
    }}

    async function loadBridgeModule() {{
      return {{ AppBridge, PostMessageTransport }};
    }}

    function valueBlock(value) {{
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(value, null, 2);
      return pre;
    }}

    function makeCollapsible(heading, ...contents) {{
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "collapse-toggle";
      toggle.textContent = heading.textContent;
      toggle.setAttribute("aria-expanded", "false");
      contents.forEach(content => {{ content.hidden = true; }});
      toggle.addEventListener("click", () => {{
        const collapsed = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!collapsed));
        contents.forEach(content => {{ content.hidden = collapsed; }});
      }});
      heading.replaceChildren(toggle);
    }}

    function labelledValue(className, label, value) {{
      const container = document.createElement("div");
      container.className = className;
      const heading = document.createElement("h3");
      heading.textContent = label;
      const content = valueBlock(value);
      container.append(heading, content);
      makeCollapsible(heading, content);
      return container;
    }}

    function showJsonFallback(response, call, message) {{
      response.replaceChildren();
      if (message) {{
        const note = document.createElement("p");
        note.className = "error app-fallback-note";
        note.textContent = message;
        response.append(note);
      }}
      response.append(valueBlock(call.output));
    }}

    async function renderAppResponse(response, call) {{
      const frame = document.createElement("iframe");
      frame.className = "tool-app-frame";
      frame.title = `${{call.tool_name}} replay app`;
      frame.setAttribute("sandbox", "allow-scripts");
      frame.referrerPolicy = "no-referrer";
      response.append(frame);

      let bridge;
      let ready = false;
      let failed = false;
      let initializationTimer;
      const fail = (reason) => {{
        if (failed || ready) return;
        failed = true;
        clearTimeout(initializationTimer);
        try {{ bridge?.close(); }} catch {{}}
        console.error("MCP App failed:", reason);
        showJsonFallback(response, call, `App unavailable: ${{reason}}`);
      }};

      try {{
        const {{ AppBridge, PostMessageTransport }} = await loadBridgeModule();
        bridge = new AppBridge(
          null,
          {{ name: "encoding-music-report-replay", version: "1.0.0" }},
          {{ serverTools: {{}}, logging: {{}} }},
          {{
            hostContext: {{
              displayMode: "inline",
              theme: window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light",
              containerDimensions: {{ maxHeight: 1200 }}
            }}
          }}
        );
        bridge.onsizechange = (size) => {{
          if (Number.isFinite(size.height)) {{
            frame.style.height = `${{Math.min(1200, Math.max(240, size.height))}}px`;
          }}
        }};
        bridge.oncalltool = async (params) => {{
          const appResponse = await fetch("{REPLAY_APP_CALL_PATH}", {{
            method: "POST",
            headers: {{
              "Accept": "application/json",
              "Content-Type": "application/json"
            }},
            body: JSON.stringify({{
              source_tool: call.tool_name,
              tool_name: params.name,
              arguments: params.arguments || {{}}
            }})
          }});
          const payload = await appResponse.json();
          if (!appResponse.ok) {{
            throw new Error(payload.error || "The app tool call failed.");
          }}
          return payload;
        }};
        bridge.oninitialized = async () => {{
          clearTimeout(initializationTimer);
          try {{
            await bridge.sendToolInput({{ arguments: call.arguments }});
            await bridge.sendToolResult(call.app.result);
            ready = true;
          }} catch (appError) {{
            fail(appError.message || String(appError));
          }}
        }};

        await bridge.connect(
          new PostMessageTransport(frame.contentWindow, frame.contentWindow)
        );
        initializationTimer = window.setTimeout(
          () => fail("The app did not initialize."),
          10000
        );
        frame.addEventListener("error", () => fail("The app resource did not load."));
        frame.src = call.app.resource_url;
      }} catch (appError) {{
        console.error("MCP App bridge error:", appError);
        fail(appError.message || String(appError));
      }}
    }}

    function renderResults(result) {{
      output.replaceChildren();
      const index = document.createElement("nav");
      index.className = "tool-index";
      index.setAttribute("aria-label", "Tool call index");
      const indexTitle = document.createElement("strong");
      indexTitle.textContent = "Tool calls";
      const indexList = document.createElement("ol");
      index.append(indexTitle, indexList);
      const calls = document.createElement("div");
      calls.className = "tool-calls";
      output.append(index, calls);
      for (const [position, call] of (result.calls || []).entries()) {{
        const toolCall = document.createElement("section");
        toolCall.className = "tool-call";
        toolCall.id = `tool-call-${{position + 1}}`;
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = `#${{toolCall.id}}`;
        link.textContent = call.tool_name;
        link.addEventListener("click", () => {{
          const toggle = toolCall.querySelector("h2 button");
          if (toggle.getAttribute("aria-expanded") === "false") toggle.click();
          toggle.focus({{ preventScroll: true }});
        }});
        item.append(link);
        indexList.append(item);

        const header = document.createElement("header");
        const name = document.createElement("h2");
        name.textContent = `${{position + 1}}. ${{call.tool_name}}`;
        const args = labelledValue("tool-arguments", "Arguments", call.arguments);
        header.append(name, args);

        const response = document.createElement("div");
        response.className = "tool-response";
        const responseHeading = document.createElement("h3");
        responseHeading.textContent = `Response (${{call.status}})`;
        const responseContent = document.createElement("div");
        response.append(responseHeading, responseContent);
        makeCollapsible(responseHeading, responseContent);
        makeCollapsible(name, args, response);
        if (call.app && call.status === "success") {{
          renderAppResponse(responseContent, call);
        }} else {{
          showJsonFallback(responseContent, call, call.message || "");
        }}
        toolCall.append(header, response);
        calls.append(toolCall);
      }}
      output.hidden = false;
    }}

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
        renderResults(result);
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
