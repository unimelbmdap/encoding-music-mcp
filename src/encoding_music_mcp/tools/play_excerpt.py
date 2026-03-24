import base64
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import verovio
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from .helpers import get_mei_filepath

_VEROVIO_RESOURCE_PATH = str(Path(verovio.__file__).parent / "data")

# A SoundFont is needed by FluidSynth to turn MIDI into actual audio.
_SOUNDFONT_PATH = Path(__file__).resolve().parent.parent / "resources" / "GeneralUser-GS.sf2"

# Defines a fallback location for the FluidSynth executable on Windows. (use `where.exe fluidsynth`)
_FALLBACK_FLUIDSYNTH_EXE = Path(r"C:\ProgramData\chocolatey\bin\fluidsynth.exe")

__all__ = ["play_excerpt"]


def _inject_or_replace_tempo(mei_text: str, bpm: int) -> str:
    """Insert a tempo marking into MEI text or replace an existing MIDI tempo.

    If the MEI already contains a ``midi.bpm="..."`` attribute, this function
    replaces its first occurrence with the requested BPM value. Otherwise, it
    inserts a ``<tempo>`` element immediately after the first ``<measure>`` tag.

    Args:
        mei_text : str
            The MEI document as a string.
        bpm : int
            The tempo in beats per minute.

    Returns:
        str
            The modified MEI text with the requested tempo.
    """
    if 'midi.bpm="' in mei_text:
        return re.sub(
            r'midi\.bpm="\d+(\.\d+)?"',
            f'midi.bpm="{bpm}"',
            mei_text,
            count=1,
        )

    return re.sub(
        r"(<measure\b[^>]*>)",
        rf'\1\n  <tempo midi.bpm="{bpm}">♩ = {bpm}</tempo>',
        mei_text,
        count=1,
    )


def _create_toolkit(mei_data: str) -> verovio.toolkit:
    """Create and initialise a Verovio toolkit from MEI data.

    Args:
        mei_data : str
            The MEI document as a string.

    Returns:
        verovio.toolkit
            A Verovio toolkit loaded with the given MEI data.

    Raises:
        ValueError
            If Verovio fails to load the MEI data.
    """
    tk = verovio.toolkit()
    tk.setResourcePath(_VEROVIO_RESOURCE_PATH)
    if not tk.loadData(mei_data):
        raise ValueError("Verovio failed to load the MEI data.")
    return tk


def _find_fluidsynth_executable() -> Path:
    """Locate the FluidSynth executable.

    The function first looks for ``fluidsynth`` on the system PATH. If it is
    not found, it falls back to a predefined Windows installation path.

    Returns:
        Path
            The path to the FluidSynth executable.

    Raises:
        FileNotFoundError
            If FluidSynth cannot be found in either location.
    """
    exe = shutil.which("fluidsynth")
    if exe:
        return Path(exe)

    if _FALLBACK_FLUIDSYNTH_EXE.exists():
        return _FALLBACK_FLUIDSYNTH_EXE

    raise FileNotFoundError(
        "FluidSynth executable not found. "
        "Install it on Windows and make sure it is on PATH, "
        f"or place it at {_FALLBACK_FLUIDSYNTH_EXE}."
    )


def _render_midi_b64_to_wav_file(midi_b64: str, wav_path: Path) -> None:
    """Render a base64-encoded MIDI file to WAV using FluidSynth.

    The MIDI data are decoded, written to a temporary ``.mid`` file, and then
    synthesised to a WAV file using the configured SoundFont and FluidSynth
    executable.

    Parameters:
        midi_b64 : str
            Base64-encoded MIDI data.
        wav_path : Path
            Output path for the rendered WAV file.

    Raises:
        FileNotFoundError
            If the SoundFont or FluidSynth executable cannot be found.
        RuntimeError
            If FluidSynth fails or does not produce the WAV file.
    """
    if not _SOUNDFONT_PATH.exists():
        raise FileNotFoundError(
            f"SoundFont not found at {_SOUNDFONT_PATH}. "
            "Put GeneralUser-GS.sf2 there or update _SOUNDFONT_PATH."
        )

    fluidsynth_exe = _find_fluidsynth_executable()
    midi_bytes = base64.b64decode(midi_b64)

    with tempfile.TemporaryDirectory() as tmpdir:
        midi_path = Path(tmpdir) / "full.mid"
        midi_path.write_bytes(midi_bytes)

        cmd = [
            str(fluidsynth_exe),
            "-q",
            "-ni",
            "-o", "audio.driver=file",
            "-T", "wav",
            "-F", str(wav_path),
            "-r", "44100",
            str(_SOUNDFONT_PATH),
            str(midi_path),
        ]

        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(
                f"FluidSynth failed with exit code {result.returncode}"
                + (f". stderr: {stderr}" if stderr else "")
            )

        if not wav_path.exists():
            raise RuntimeError("FluidSynth did not produce a WAV file.")


def _trim_wav_file(input_wav: Path, output_wav: Path, start_sec: float, end_sec: float) -> None:
    """Trim a time interval from a WAV file and save it as a new WAV file.

    Parameters:
        input_wav : Path
            Path to the source WAV file.
        output_wav : Path
            Path where the trimmed WAV file will be written.
        start_sec : float
            Start time of the excerpt in seconds.
        end_sec : float
            End time of the excerpt in seconds.

    Raises:
        ValueError
            If ``end_sec`` is not greater than ``start_sec``, or if the excerpt is
            empty after clamping to the audio duration.
    """
    if end_sec <= start_sec:
        raise ValueError("end_sec must be greater than start_sec")

    with wave.open(str(input_wav), "rb") as src:
        nchannels = src.getnchannels()
        sampwidth = src.getsampwidth()
        framerate = src.getframerate()
        comptype = src.getcomptype()
        compname = src.getcompname()
        nframes = src.getnframes()

        duration_sec = nframes / framerate
        start_sec = max(0.0, min(start_sec, duration_sec))
        end_sec = max(0.0, min(end_sec, duration_sec))

        if end_sec <= start_sec:
            raise ValueError(
                f"Requested excerpt is empty after clamping. "
                f"Audio duration is {duration_sec:.3f}s, "
                f"requested [{start_sec:.3f}, {end_sec:.3f}]s."
            )

        start_frame = int(start_sec * framerate)
        end_frame = int(end_sec * framerate)
        frame_count = max(0, end_frame - start_frame)

        src.setpos(start_frame)
        audio_frames = src.readframes(frame_count)

    with wave.open(str(output_wav), "wb") as dst:
        dst.setparams((nchannels, sampwidth, framerate, 0, comptype, compname))
        dst.writeframes(audio_frames)


def _wav_file_to_b64(wav_path: Path) -> str:
    """Encode a WAV file as a base64 ASCII string.

    Parameters:
        wav_path : Path
            Path to the WAV file.

    Returns:
        str
            Base64-encoded WAV data.
    """
    return base64.b64encode(wav_path.read_bytes()).decode("ascii")


def play_excerpt(
    filename: str, start_q: float, end_q: float, bpm: int = 60,
) -> ToolResult:
    """Render an MEI file to audio and return a requested excerpt.

    The function reads the MEI file, injects or replaces its tempo, renders it
    to MIDI with Verovio, synthesises the MIDI to WAV with FluidSynth, trims
    the requested time interval, and returns the excerpt as base64-encoded WAV
    data in the tool result.

    The end time is extended slightly before trimming so that the rendered audio
    does not cut off the final note too early.

    Parameters:
        filename : str
            Name of the MEI file to load.
        start_q : float
            Start position of the excerpt in quarter-note units.
        end_q : float
            End position of the excerpt in quarter-note units.
        bpm : int, default=60
            Playback tempo in beats per minute.

    Returns:
        ToolResult
            A tool result containing a text message and structured payload with the
            audio excerpt and related metadata.

    Raises:
        ValueError
            If ``end_q`` is not greater than ``start_q`` or if ``bpm`` is not
            positive.
        FileNotFoundError
            If the MEI file does not exist.
    """
    if end_q <= start_q:
        raise ValueError("end_q must be greater than start_q")
    if bpm <= 0:
        raise ValueError("bpm must be positive")

    filepath = get_mei_filepath(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    mei_text = filepath.read_text(encoding="utf-8")
    mei_text = _inject_or_replace_tempo(mei_text, bpm)

    tk = _create_toolkit(mei_text)
    midi_b64 = tk.renderToMIDI()

    start_sec = start_q * 60.0 / bpm
    # Add a small buffer to avoid cutting off the final note too early
    end_sec = (end_q + 0.25) * 60.0 / bpm

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        full_wav_path = tmpdir_path / "full.wav"
        excerpt_wav_path = tmpdir_path / "excerpt.wav"

        _render_midi_b64_to_wav_file(midi_b64, full_wav_path)
        _trim_wav_file(full_wav_path, excerpt_wav_path, start_sec, end_sec)
        audio_b64 = _wav_file_to_b64(excerpt_wav_path)

    payload = {
        "filename": filename,
        "audio_base64": audio_b64,
        "mime_type": "audio/wav",
        "start_q": start_q,
        "end_q": end_q,
        "bpm": bpm,
    }

    return ToolResult(
        content=[TextContent(type="text", text="Prepared audio excerpt")],
        structured_content=payload,
    )