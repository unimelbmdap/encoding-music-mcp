from fastmcp.server.dependencies import get_http_request

REPLAY_PATH = "/reports/replay"
REPLAY_SESSION_PATH = f"{REPLAY_PATH}/{{session_id}}"
REPLAY_APP_PATH = f"{REPLAY_PATH}/apps/{{tool_name}}"
REPLAY_APP_CALL_PATH = f"{REPLAY_PATH}/app-call"
REPORT_VERSION = "1"
MAX_REPORT_BYTES = 1_000_000
MAX_REPORT_CALLS = 100
MCP_APPS_SDK_VERSION = "0.4.0"

# Tool names registered with an MCP App UI. Replay HTML can use this list to
# distinguish app payloads from ordinary JSON tool responses.
MCP_APP_TOOLS = [
    "show_notation",
    "show_notation_highlight",
    "plot_voice_ranges",
    "plot_weighted_note_distribution",
    "plot_melodic_ngram_heatmap",
    "plot_sonority_ngram_progress",
    "play_excerpt",
]

# App-initiated calls permitted by the replay host. Keep this narrower than the
# full MCP tool list because the replay page is an unauthenticated beta route.
MCP_APP_ALLOWED_CALLS = {
    "show_notation": {"show_notation"},
    "show_notation_highlight": {"show_notation_highlight"},
    "plot_voice_ranges": set(),
    "plot_weighted_note_distribution": set(),
    "plot_melodic_ngram_heatmap": set(),
    "plot_sonority_ngram_progress": set(),
    "play_excerpt": {"load_audio_resource"},
}


def base_url() -> str:
    """Return the browser URL that can replay one active session's report.
    If none is provided, return the upload page URL."""
    try:
        request = get_http_request()
        return f"{str(request.base_url).rstrip('/')}{REPLAY_PATH}"
    except RuntimeError:
        return REPLAY_PATH
