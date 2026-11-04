"""Exercise resource requests through the inline replay HTML bridge."""

from pathlib import Path
import shutil
import subprocess

import pytest

from src.encoding_music_mcp.tools.reports.html import render_upload_page


def test_replay_bridge_forwards_notation_resource_reads():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the replay bridge")
    result = subprocess.run(
        [node, str(Path(__file__).with_name("replay_bridge_harness.cjs"))],
        input=render_upload_page(),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
