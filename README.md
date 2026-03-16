# Live Transcript App

Real-time speech-to-text desktop app using **Soniox STT** (WebSocket), **Python**, and **CustomTkinter**.

## Features

- Live transcription via Soniox `stt-rt-v4` WebSocket API
- Two audio modes: **Microphone** and **System Audio** (loopback)
- Cross-platform: macOS, Linux, Windows
- Export transcript as `.txt` or `.srt` (with timestamps)
- Secure API key storage via OS keyring (Keychain / libsecret / Credential Locker)
- Speaker diarization and language selection

## Setup

### 1. Install dependencies

```bash
# Requires uv (https://docs.astral.sh/uv/)
uv sync
```

### 2. Configure API key

Either set environment variable (dev):

```bash
cp .env.example .env
# Edit .env and add your SONIOX_API_KEY
```

Or launch the app and enter your key in **Settings (⚙)** — it will be stored securely in the OS keyring.

Get your API key at: https://console.soniox.com/

### 3. Run

```bash
uv run python -m transcript_app.main
```

## System Audio Notes

### macOS

System audio capture requires a virtual audio driver (no native loopback API):

- **BlackHole** (free): https://existential.audio/blackhole/
- **Loopback** (paid): https://rogueamoeba.com/loopback/

The app will show setup instructions if no loopback device is detected.

### Linux

Uses PulseAudio/PipeWire monitor sources automatically. Select "Monitor of ..." in the device dropdown.

### Windows

Uses WASAPI loopback natively — no extra driver needed.

Optional: install `pyaudiowpatch` for extended loopback support:

```bash
uv add pyaudiowpatch
```

## Build Standalone Binary

```bash
uv run python scripts/build.py
```

Output in `dist/`. Supports macOS (`.app`), Linux (AppImage/binary), Windows (`.exe`).

## Project Structure

```
src/transcript_app/
├── main.py                      # Entry point
├── app.py                       # Orchestrator
├── config.py                    # Settings + keyring
├── permissions.py               # OS permission checks
├── audio/
│   ├── capture.py               # MicCapture (sounddevice)
│   ├── system_audio.py          # SystemAudioCapture (per-OS)
│   └── devices.py               # Device enumeration
├── transcription/
│   └── soniox_client.py         # Soniox WebSocket wrapper
└── ui/
    ├── main_window.py           # Root CTk window
    ├── transcript_view.py       # Live transcript display
    ├── controls.py              # Mode/device/start controls
    └── settings_dialog.py       # Settings modal
```
