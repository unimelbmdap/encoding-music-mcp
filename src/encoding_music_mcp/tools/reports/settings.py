from fastmcp.server.dependencies import get_http_request

REPLAY_PATH = "/reports/replay"
REPLAY_SESSION_PATH = f"{REPLAY_PATH}/{{session_id}}"
REPORT_VERSION = "1"
MAX_REPORT_BYTES = 1_000_000
MAX_REPORT_CALLS = 100


def base_url() -> str:
    """Return the browser URL that can replay one active session's report.
    If none is provided, return the upload page URL."""
    try:
        request = get_http_request()
        return f"{str(request.base_url).rstrip('/')}{REPLAY_PATH}"
    except RuntimeError:
        return REPLAY_PATH
