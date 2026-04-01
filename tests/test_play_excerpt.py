"""Tests for MP3 playback preparation tool."""

import wave
from pathlib import Path

import pytest

from src.encoding_music_mcp.tools import play_excerpt as play_excerpt_module


def _write_test_wav(path: Path, duration_sec: float = 1.0, framerate: int = 8000) -> None:
    """Create a tiny silent WAV file for tests."""
    frame_count = int(duration_sec * framerate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


class _DummyToolkit:
    def renderToMIDI(self) -> str:
        return "ZHVtbXk="


@pytest.fixture
def fake_mei_file(tmp_path: Path) -> Path:
    mei_path = tmp_path / "sample.mei"
    mei_path.write_text("<mei><measure n='1' /></mei>", encoding="utf-8")
    return mei_path


def test_play_excerpt_full_piece_returns_stream_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_mei_file: Path):
    """Full-piece playback should return an audio resource URI and registry entry."""
    output_dir = tmp_path / "audio-cache"

    monkeypatch.setattr(play_excerpt_module, "_AUDIO_CACHE_DIR", output_dir)
    monkeypatch.setattr(play_excerpt_module, "get_mei_filepath", lambda filename: fake_mei_file)
    monkeypatch.setattr(play_excerpt_module, "_create_toolkit", lambda mei_data: _DummyToolkit())

    def fake_render(midi_b64: str, wav_path: Path) -> None:
        _write_test_wav(wav_path, duration_sec=1.25)

    def fake_convert(input_wav: Path, output_mp3: Path) -> None:
        output_mp3.write_bytes(b"fake-mp3")

    monkeypatch.setattr(play_excerpt_module, "_render_midi_b64_to_wav_file", fake_render)
    monkeypatch.setattr(play_excerpt_module, "_convert_wav_to_mp3", fake_convert)

    result = play_excerpt_module.play_excerpt("sample.mei", bpm=72)
    payload = result.structured_content

    assert payload is not None
    assert payload["audio_resource_uri"].startswith("audio://files/")
    assert payload["mime_type"] == "audio/mpeg"
    assert payload["start_q"] == 0.0
    assert payload["end_q"] is None
    assert pytest.approx(payload["duration_sec"], rel=1e-3) == 1.25

    token = payload["audio_resource_uri"].rsplit("/", 1)[-1]
    audio_entry = play_excerpt_module.get_registered_audio(token)
    assert audio_entry is not None
    assert audio_entry["path"].exists()
    assert audio_entry["mime_type"] == "audio/mpeg"


def test_play_excerpt_range_trims_audio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_mei_file: Path):
    """Ranged playback should trim before MP3 conversion."""
    output_dir = tmp_path / "audio-cache"

    monkeypatch.setattr(play_excerpt_module, "_AUDIO_CACHE_DIR", output_dir)
    monkeypatch.setattr(play_excerpt_module, "get_mei_filepath", lambda filename: fake_mei_file)
    monkeypatch.setattr(play_excerpt_module, "_create_toolkit", lambda mei_data: _DummyToolkit())

    trim_calls: list[tuple[float, float]] = []

    def fake_render(midi_b64: str, wav_path: Path) -> None:
        _write_test_wav(wav_path, duration_sec=4.0)

    def fake_trim(input_wav: Path, output_wav: Path, start_sec: float, end_sec: float) -> None:
        trim_calls.append((start_sec, end_sec))
        _write_test_wav(output_wav, duration_sec=end_sec - start_sec)

    def fake_convert(input_wav: Path, output_mp3: Path) -> None:
        output_mp3.write_bytes(b"fake-mp3")

    monkeypatch.setattr(play_excerpt_module, "_render_midi_b64_to_wav_file", fake_render)
    monkeypatch.setattr(play_excerpt_module, "_trim_wav_file", fake_trim)
    monkeypatch.setattr(play_excerpt_module, "_convert_wav_to_mp3", fake_convert)

    result = play_excerpt_module.play_excerpt("sample.mei", start_q=2.0, end_q=6.0, bpm=120)
    payload = result.structured_content

    assert payload is not None
    assert trim_calls == [(1.0, 3.125)]
    assert pytest.approx(payload["duration_sec"], rel=1e-3) == 2.125


def test_play_excerpt_rejects_invalid_range():
    """Invalid ranges should be rejected before any rendering starts."""
    with pytest.raises(ValueError, match="end_q must be greater than start_q"):
        play_excerpt_module.play_excerpt("anything.mei", start_q=3.0, end_q=3.0)


def test_play_excerpt_rejects_negative_start():
    """Negative quarter-note offsets should be rejected."""
    with pytest.raises(ValueError, match="start_q must be greater than or equal to 0"):
        play_excerpt_module.play_excerpt("anything.mei", start_q=-1.0)


def test_load_audio_resource_returns_base64(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Registered audio resources should be loadable as base64 payloads."""
    mp3_path = tmp_path / "sample.mp3"
    mp3_path.write_bytes(b"fake-mp3-bytes")

    monkeypatch.setattr(play_excerpt_module, "_AUDIO_REGISTRY", {
        "token123": {
            "path": mp3_path,
            "mime_type": "audio/mpeg",
            "duration_sec": 1.0,
        }
    })

    result = play_excerpt_module.load_audio_resource("audio://files/token123")
    payload = result.structured_content

    assert payload is not None
    assert payload["resource_uri"] == "audio://files/token123"
    assert payload["mime_type"] == "audio/mpeg"
    assert payload["audio_base64"] == "ZmFrZS1tcDMtYnl0ZXM="


def test_normalize_zero_velocities_rewrites_silent_notes():
    """Zero-velocity note and chord events should be made audible for playback."""
    mei = '<note vel="0"/><chord dur="4" vel="0"/><note vel="42"/>'

    normalized = play_excerpt_module._normalize_zero_velocities(mei, default_velocity=64)

    assert '<note vel="64"/>' in normalized
    assert '<chord dur="4" vel="64"/>' in normalized
    assert 'vel="42"' in normalized
