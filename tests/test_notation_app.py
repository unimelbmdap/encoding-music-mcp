"""Exercise pagination in the actual notation widget scripts."""

from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("template", ["notation_app.html", "notation_highlight.html"])
@pytest.mark.parametrize("scenario", ["pagination", "error"])
def test_notation_widget_resource_pagination(template, scenario):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the widget scripts")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            node,
            str(Path(__file__).with_name("notation_app_harness.cjs")),
            str(root / "src/encoding_music_mcp/resources/templates" / template),
            scenario,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
