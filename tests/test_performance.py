"""Tests for analysis concurrency and result caching."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.encoding_music_mcp.tools import performance


def test_analysis_cache_coalesces_and_copies_results(
    monkeypatch,
    tmp_path: Path,
):
    """Identical concurrent requests should compute once and return safe copies."""
    mei_path = tmp_path / "score.mei"
    mei_path.write_text("<mei />", encoding="utf-8")
    monkeypatch.setattr(performance, "get_mei_filepath", lambda filename: mei_path)
    performance.clear_analysis_result_cache()

    calls = 0
    calls_lock = threading.Lock()

    def analyze(filename: str) -> dict[str, list[str]]:
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.05)
        return {"filenames": [filename]}

    cached = performance.cache_analysis_result(analyze)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: cached("score.mei"), range(4)))

    assert calls == 1
    assert results == [{"filenames": ["score.mei"]}] * 4
    results[0]["filenames"].append("mutated")
    assert cached("score.mei") == {"filenames": ["score.mei"]}


def test_analysis_cache_invalidates_when_file_changes(
    monkeypatch,
    tmp_path: Path,
):
    """A changed source fingerprint should cause a fresh computation."""
    mei_path = tmp_path / "score.mei"
    mei_path.write_text("<mei />", encoding="utf-8")
    monkeypatch.setattr(performance, "get_mei_filepath", lambda filename: mei_path)
    performance.clear_analysis_result_cache()

    calls = 0

    def analyze(filename: str) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"call": calls}

    cached = performance.cache_analysis_result(analyze)
    assert cached("score.mei") == {"call": 1}
    mei_path.write_text("<mei><music /></mei>", encoding="utf-8")
    assert cached("score.mei") == {"call": 2}


def test_analysis_concurrency_is_bounded():
    """The analysis wrapper should not run more than its configured slots."""
    active = 0
    maximum_active = 0
    active_lock = threading.Lock()
    gate = threading.Barrier(4)

    def analyze(value: int) -> int:
        nonlocal active, maximum_active
        with active_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with active_lock:
            active -= 1
        return value

    limited = performance.limit_analysis_concurrency(analyze)

    def invoke(value: int) -> int:
        gate.wait()
        return limited(value)

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(invoke, range(4))) == list(range(4))

    assert maximum_active <= performance._ANALYSIS_CONCURRENCY
