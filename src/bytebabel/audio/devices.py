"""Audio device enumeration and selection helpers."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import sounddevice as sd


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_loopback: bool = False
    hostapi_name: str = ""

    def __str__(self) -> str:
        return self.name


def list_input_devices() -> list[AudioDevice]:
    """Return all devices that have at least one input channel."""
    devices = []
    hostapis = sd.query_hostapis()
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] < 1:
            continue
        hostapi_name = hostapis[dev["hostapi"]]["name"] if hostapis else ""
        devices.append(
            AudioDevice(
                index=idx,
                name=dev["name"],
                max_input_channels=dev["max_input_channels"],
                default_sample_rate=dev["default_samplerate"],
                hostapi_name=hostapi_name,
            )
        )
    return devices


def list_mic_devices() -> list[AudioDevice]:
    """Input devices suitable for microphone capture."""
    return [d for d in list_input_devices() if not _is_loopback_device(d)]


def list_system_audio_devices() -> list[AudioDevice]:
    """Devices suitable for system/loopback audio capture."""
    if sys.platform == "win32":
        return _windows_loopback_devices()
    elif sys.platform == "darwin":
        return _macos_loopback_devices()
    else:
        return _linux_monitor_devices()


def get_default_input_device() -> AudioDevice | None:
    try:
        idx = sd.default.device[0]
        if idx is None or idx < 0:
            return None
        dev = sd.query_devices(idx)
        return AudioDevice(
            index=idx,
            name=dev["name"],
            max_input_channels=dev["max_input_channels"],
            default_sample_rate=dev["default_samplerate"],
        )
    except Exception:
        return None


# ── Platform helpers ──────────────────────────────────────────────────────────


def _is_loopback_device(d: AudioDevice) -> bool:
    name_lower = d.name.lower()
    return any(
        kw in name_lower
        for kw in ("monitor", "loopback", "blackhole", "soundflower", "stereo mix", "what u hear")
    )


_MACOS_SCK_DEVICE = AudioDevice(
    index=-1,
    name="System Audio",
    max_input_channels=1,
    default_sample_rate=16000.0,
    is_loopback=True,
    hostapi_name="ScreenCaptureKit",
)


def _macos_loopback_devices() -> list[AudioDevice]:
    """macOS 13+: system audio via ScreenCaptureKit — no virtual driver needed."""
    return [_MACOS_SCK_DEVICE]


def _linux_monitor_devices() -> list[AudioDevice]:
    """PulseAudio/PipeWire monitor sources show up as input devices."""
    candidates = []
    for d in list_input_devices():
        if "monitor" in d.name.lower():
            d.is_loopback = True
            candidates.append(d)
    return candidates


def _windows_loopback_devices() -> list[AudioDevice]:
    """Try pyaudiowpatch WASAPI loopback first, fall back to sounddevice."""
    try:
        import pyaudiowpatch as pyaudio  # type: ignore[import]

        pa = pyaudio.PyAudio()
        devices = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("isLoopbackDevice", False):
                devices.append(
                    AudioDevice(
                        index=i,
                        name=info["name"],
                        max_input_channels=info["maxInputChannels"],
                        default_sample_rate=info["defaultSampleRate"],
                        is_loopback=True,
                        hostapi_name="WASAPI",
                    )
                )
        pa.terminate()
        return devices
    except ImportError:
        candidates = []
        for d in list_input_devices():
            name_lower = d.name.lower()
            if any(kw in name_lower for kw in ("stereo mix", "what u hear", "loopback")):
                d.is_loopback = True
                candidates.append(d)
        return candidates
