# macOS Playback Requirements

The main installation guide covers `uv`, which is enough for the core MCP server. Audio playback needs two extra command-line programs on macOS:

- `fluidsynth` - turns rendered MIDI into WAV audio using the bundled SoundFont
- `ffmpeg` - converts the WAV audio into MP3 for the inline player

The SoundFont used by playback, `GeneralUser-GS.sf2`, is already bundled with encoding-music-mcp. You do not need to install a separate SoundFont.

## Install with Homebrew

If you already have Homebrew installed, run:

```bash
brew install fluidsynth ffmpeg
```

If `brew` is not available, install Homebrew first from the official Homebrew website:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After Homebrew finishes, follow the "Next steps" it prints in the terminal so that `brew` is available in your shell, then install the playback tools:

```bash
brew install fluidsynth ffmpeg
```

## Verify the Tools

Check that both commands are available:

```bash
fluidsynth --version
ffmpeg -version
```

Both commands should print version information. If either command is not found, restart your terminal and try again.

## Restart Claude Desktop

After installing the playback tools, restart Claude Desktop completely. Once restarted, try a playback request such as:

```text
Play Bach_BWV_0772.mei
```

