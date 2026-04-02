import base64
import hashlib
import re
import secrets
import shutil
import subprocess
import tempfile
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from threading import Lock
from typing import Any

from fastmcp.tools.tool import ToolResult
from music21 import converter, tempo
from mcp.types import TextContent

from .helpers import get_mei_filepath

# A SoundFont is needed by FluidSynth to turn MIDI into actual audio.
_SOUNDFONT_PATH = Path(__file__).resolve().parent.parent / "resources" / "GeneralUser-GS.sf2"
_AUDIO_CACHE_DIR = Path(tempfile.gettempdir()) / "encoding_music_mcp_audio"
_AUDIO_CACHE_VERSION = "v3"

# Defines a fallback location for the FluidSynth executable on Windows. (e.g. use `where.exe fluidsynth`)
_FALLBACK_FLUIDSYNTH_EXE = Path(r"C:\ProgramData\chocolatey\bin\fluidsynth.exe")
_FALLBACK_FFMPEG_EXE = Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe")

_AUDIO_REGISTRY: dict[str, dict[str, Any]] = {}
_AUDIO_REGISTRY_LOCK = Lock()

__all__ = ["play_excerpt", "load_audio_resource", "get_registered_audio"]
_DEFAULT_PLAYBACK_VELOCITY = 64
_MEI_NS = "http://www.music-encoding.org/ns/mei"
_MEI_TAG = "{" + _MEI_NS + "}"

ET.register_namespace("", _MEI_NS)
ET.register_namespace("xml", "http://www.w3.org/XML/1998/namespace")


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


def _normalize_zero_velocities(mei_text: str, default_velocity: int = _DEFAULT_PLAYBACK_VELOCITY) -> str:
    """Replace silent note/chord velocities with a practical playback default.

    Some source MEI files encode notes with ``vel="0"``. That value is fine as
    source data, but once converted to MIDI it effectively produces silent note
    events. To make playback audible, these zero-velocity note and chord events
    are rewritten to a moderate default velocity before rendering to MIDI.
    """
    return re.sub(
        r'(<(?:note|chord)\b[^>]*\bvel=")0(")',
        rf"\g<1>{default_velocity}\2",
        mei_text,
    )


def _clone_xml_element(element: ET.Element) -> ET.Element:
    """Return a deep copy of an XML element."""
    return ET.fromstring(ET.tostring(element, encoding="unicode"))


def _is_mei_measure(element: ET.Element) -> bool:
    """Return True when the element is an MEI measure."""
    return element.tag == f"{_MEI_TAG}measure"


def _is_mei_ending(element: ET.Element) -> bool:
    """Return True when the element is an MEI ending wrapper."""
    return element.tag == f"{_MEI_TAG}ending"


def _strip_repeat_markers(measure: ET.Element) -> ET.Element:
    """Remove repeat barline markers from a cloned measure."""
    cloned = _clone_xml_element(measure)

    left = cloned.get("left")
    right = cloned.get("right")

    if left and "rpt" in left:
        cloned.attrib.pop("left", None)
    if right and "rpt" in right:
        cloned.attrib.pop("right", None)

    return cloned


def _parse_ending_passes(ending: ET.Element) -> set[int]:
    """Parse the numbered passes to which an MEI ending applies."""
    value = " ".join(filter(None, [ending.get("n"), ending.get("label")]))
    return {int(token) for token in re.findall(r"\d+", value)}


def _expand_region_element(element: ET.Element, pass_number: int) -> list[ET.Element]:
    """Expand one region element for a requested repeat pass."""
    if _is_mei_measure(element):
        return [_strip_repeat_markers(element)]

    if not _is_mei_ending(element):
        return []

    ending_passes = _parse_ending_passes(element)
    if ending_passes and pass_number not in ending_passes:
        return []

    return [
        _strip_repeat_markers(child)
        for child in list(element)
        if _is_mei_measure(child)
    ]


def _contains_numbered_endings(region: list[ET.Element]) -> bool:
    """Return True when a repeat region contains numbered ending wrappers."""
    return any(_is_mei_ending(element) and _parse_ending_passes(element) for element in region)


def _expand_region_with_numbered_endings(region: list[ET.Element]) -> list[ET.Element]:
    """Expand a repeat region that uses numbered endings.

    This handles the MEI pattern seen in the Morley files where the first
    ending begins with an ``<ending n="1">`` wrapper, continues through
    subsequent plain measures, and the second ending is wrapped later as
    ``<ending n="2">``.
    """
    prefix: list[ET.Element] = []
    first_ending: list[ET.Element] = []
    second_ending: list[ET.Element] = []
    current_ending_pass: int | None = None

    for element in region:
        if _is_mei_measure(element):
            target = prefix
            if current_ending_pass == 1:
                target = first_ending
            elif current_ending_pass == 2:
                target = second_ending
            target.append(_strip_repeat_markers(element))
            continue

        if not _is_mei_ending(element):
            continue

        ending_passes = _parse_ending_passes(element)
        if 1 in ending_passes:
            current_ending_pass = 1
            first_ending.extend(_expand_region_element(element, 1))
        elif 2 in ending_passes:
            current_ending_pass = 2
            second_ending.extend(_expand_region_element(element, 2))

    return prefix + first_ending + prefix + second_ending


def _expand_section_repeats(section: ET.Element) -> None:
    """Flatten simple MEI repeats and numbered endings into performed order."""
    children = list(section)
    flattened: list[ET.Element] = []
    index = 0

    while index < len(children):
        child = children[index]

        if not (_is_mei_measure(child) and child.get("left") and "rptstart" in child.get("left", "")):
            if _is_mei_measure(child):
                flattened.append(_strip_repeat_markers(child))
            index += 1
            continue

        region_end = index
        repeat_found = False
        while region_end < len(children):
            region_child = children[region_end]
            if _is_mei_measure(region_child) and "rptend" in region_child.get("right", ""):
                repeat_found = True
                region_end += 1
                while region_end < len(children) and _is_mei_ending(children[region_end]):
                    region_end += 1
                break
            region_end += 1

        if not repeat_found:
            flattened.append(_strip_repeat_markers(child))
            index += 1
            continue

        region = children[index:region_end]
        if _contains_numbered_endings(region):
            flattened.extend(_expand_region_with_numbered_endings(region))
        else:
            for pass_number in (1, 2):
                for region_child in region:
                    flattened.extend(_expand_region_element(region_child, pass_number))
        index = region_end

    for child in list(section):
        section.remove(child)
    for measure in flattened:
        section.append(measure)


def _expand_mei_repeats_for_playback(mei_text: str) -> str:
    """Return MEI with simple repeats and numbered endings flattened."""
    root = ET.fromstring(mei_text)
    for section in root.findall(f".//{_MEI_TAG}section"):
        _expand_section_repeats(section)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _render_mei_to_midi_b64(filepath: Path, mei_text: str, bpm: int) -> str:
    """Render MEI to base64 MIDI via music21 after flattening playback repeats."""
    _AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        expanded_mei_text = _expand_mei_repeats_for_playback(mei_text)
    except Exception:
        expanded_mei_text = mei_text

    with tempfile.TemporaryDirectory(dir=_AUDIO_CACHE_DIR) as tmpdir:
        tmpdir_path = Path(tmpdir)
        mei_path = tmpdir_path / filepath.name
        midi_path = tmpdir_path / "full.mid"

        mei_path.write_text(expanded_mei_text, encoding="utf-8")
        score = converter.parse(str(mei_path))
        score.insert(0, tempo.MetronomeMark(number=bpm))
        score.write("midi", fp=str(midi_path))
        return base64.b64encode(midi_path.read_bytes()).decode("ascii")


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


def _find_ffmpeg_executable() -> Path:
    """Locate the FFmpeg executable used for MP3 conversion."""
    exe = shutil.which("ffmpeg")
    if exe:
        return Path(exe)

    if _FALLBACK_FFMPEG_EXE.exists():
        return _FALLBACK_FFMPEG_EXE

    raise FileNotFoundError(
        "FFmpeg executable not found. "
        "Install it on Windows and make sure it is on PATH, "
        f"or place it at {_FALLBACK_FFMPEG_EXE}."
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


def _get_wav_duration_sec(wav_path: Path) -> float:
    """Return the duration of a WAV file in seconds."""
    with wave.open(str(wav_path), "rb") as src:
        return src.getnframes() / src.getframerate()


def _convert_wav_to_mp3(input_wav: Path, output_mp3: Path) -> None:
    """Convert WAV audio to MP3 using FFmpeg."""
    ffmpeg_exe = _find_ffmpeg_executable()

    cmd = [
        str(ffmpeg_exe),
        "-y",
        "-i",
        str(input_wav),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "4",
        str(output_mp3),
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
            f"FFmpeg failed with exit code {result.returncode}"
            + (f". stderr: {stderr}" if stderr else "")
        )

    if not output_mp3.exists():
        raise RuntimeError("FFmpeg did not produce an MP3 file.")


def _build_audio_cache_key(filename: str, start_q: float, end_q: float | None, bpm: int) -> str:
    """Create a stable cache key for a rendered audio request.

    The cache key is derived from the musical request. That means repeated requests 
    for the same file, tempo, and quarter-note range can reuse the same MP3 instead 
    of re-rendering it.
    """
    payload = (
        f"{_AUDIO_CACHE_VERSION}|{filename}|{start_q:.6f}|"
        f"{end_q if end_q is None else f'{end_q:.6f}'}|{bpm}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _register_audio_file(audio_path: Path, mime_type: str, duration_sec: float) -> str:
    """Register a prepared audio file and return a lookup token."""
    token = secrets.token_urlsafe(16)
    with _AUDIO_REGISTRY_LOCK:
        _AUDIO_REGISTRY[token] = {
            "path": audio_path,
            "mime_type": mime_type,
            "duration_sec": duration_sec,
        }
    return token


def get_registered_audio(token: str) -> dict[str, Any] | None:
    """Look up a registered prepared audio file by token."""
    with _AUDIO_REGISTRY_LOCK:
        return _AUDIO_REGISTRY.get(token)


def _parse_audio_resource_uri(resource_uri: str) -> str:
    """Extract the token from an ``audio://`` resource URI."""
    prefix = "audio://files/"
    if not resource_uri.startswith(prefix):
        raise ValueError(f"Invalid audio resource URI: {resource_uri}")
    return resource_uri[len(prefix):]


def play_excerpt(
    filename: str, start_q: float = 0.0, end_q: float | None = None, bpm: int = 60,
) -> ToolResult:
    """Render an MEI file to MP3 and return an MCP audio resource reference.

    The function reads the MEI file, injects or replaces its tempo, renders it
    to MIDI with music21, synthesises the MIDI to WAV with FluidSynth, trims
    the requested time interval if provided, converts the audio to MP3, and
    returns a small tool payload with an ``audio://`` resource URI.

    The end time is extended slightly before trimming so that the rendered audio
    does not cut off the final note too early.

    Parameters:
        filename : str
            Name of the MEI file to load.
        start_q : float
            Start position of the excerpt in zero-based quarter-note units.
            ``0.0`` means the beginning of the piece.
        end_q : float | None
            Optional end position of the excerpt in quarter-note units.
        bpm : int, default=60
            Playback tempo in beats per minute.

    Returns:
        ToolResult
            A tool result containing a text message and structured payload with the
            MCP audio resource URI and related metadata.

    Raises:
        ValueError
            If ``end_q`` is not greater than ``start_q`` when provided, or if
            ``start_q`` is negative, or if ``bpm`` is not positive.
        FileNotFoundError
            If the MEI file does not exist.
    """
    if start_q < 0:
        raise ValueError("start_q must be greater than or equal to 0")
    if end_q is not None and end_q <= start_q:
        raise ValueError("end_q must be greater than start_q")
    if bpm <= 0:
        raise ValueError("bpm must be positive")

    filepath = get_mei_filepath(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    mei_text = filepath.read_text(encoding="utf-8")
    mei_text = _inject_or_replace_tempo(mei_text, bpm)
    mei_text = _normalize_zero_velocities(mei_text)

    _AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    midi_b64 = _render_mei_to_midi_b64(filepath, mei_text, bpm)
    cache_key = _build_audio_cache_key(filename, start_q, end_q, bpm)
    output_mp3_path = _AUDIO_CACHE_DIR / f"{cache_key}.mp3"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        full_wav_path = tmpdir_path / "full.wav"
        working_wav_path = tmpdir_path / "working.wav"

        _render_midi_b64_to_wav_file(midi_b64, full_wav_path)

        if end_q is None:
            shutil.copyfile(full_wav_path, working_wav_path)
        else:
            start_sec = start_q * 60.0 / bpm
            # Add a small buffer to avoid cutting off the final note too early.
            end_sec = (end_q + 0.25) * 60.0 / bpm
            _trim_wav_file(full_wav_path, working_wav_path, start_sec, end_sec)

        if not output_mp3_path.exists():
            _convert_wav_to_mp3(working_wav_path, output_mp3_path)

        duration_sec = _get_wav_duration_sec(working_wav_path)

    audio_token = _register_audio_file(output_mp3_path, "audio/mpeg", duration_sec)
    audio_resource_uri = f"audio://files/{audio_token}"

    payload = {
        "filename": filename,
        "audio_resource_uri": audio_resource_uri,
        "mime_type": "audio/mpeg",
        "start_q": start_q,
        "end_q": end_q,
        "bpm": bpm,
        "duration_sec": duration_sec,
    }

    return ToolResult(
        content=[TextContent(type="text", text="Prepared streaming audio")],
        structured_content=payload,
    )


def load_audio_resource(resource_uri: str) -> ToolResult:
    """Load a prepared audio MCP resource for use inside the playback widget.

    This helper acts as a bridge between the app and the server-side audio 
    registry. It accepts an ``audio://files/{token}`` resource URI, resolves 
    the token to a previously prepared MP3 file, reads the file bytes, and 
    returns them as base64 along with MIME metadata.

    Parameters:
        resource_uri : str
            MCP audio resource URI produced earlier by ``play_excerpt``.

    Returns:
        ToolResult
            A tool result whose structured payload contains the original
            resource URI, MIME type, duration, and base64-encoded audio bytes.

    Raises:
        ValueError
            If the resource URI does not match the expected ``audio://`` format.
        FileNotFoundError
            If the token is unknown or the prepared audio file has been removed.
    """
    token = _parse_audio_resource_uri(resource_uri)
    audio_entry = get_registered_audio(token)
    if not audio_entry:
        raise FileNotFoundError(f"Audio resource not found: {resource_uri}")

    audio_path = audio_entry["path"]
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file no longer exists for resource: {resource_uri}")

    payload = {
        "resource_uri": resource_uri,
        "mime_type": audio_entry["mime_type"],
        "audio_base64": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
        "duration_sec": audio_entry["duration_sec"],
    }

    return ToolResult(
        content=[TextContent(type="text", text="Loaded audio resource")],
        structured_content=payload,
    )
