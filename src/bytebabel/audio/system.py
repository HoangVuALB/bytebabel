"""System audio capture — platform-specific loopback/monitor implementations."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

import numpy as np

from .base import CHUNK_FRAMES, SAMPLE_RATE, AudioCapture
from ..logger import get_logger

log = get_logger("audio.system")

# Compiled Swift ScreenCaptureKit helper — macOS only
HELPER_PATH = Path(__file__).parents[3] / "helpers" / "system_audio_capture"

# 100 ms of raw PCM at 16 kHz mono int16
_MACOS_CHUNK_BYTES = int(SAMPLE_RATE * 0.1) * 2  # 3200 bytes


class NoLoopbackDeviceError(RuntimeError):
    pass


class ScreenRecordingPermissionError(RuntimeError):
    pass


class SystemAudioCapture(AudioCapture):
    """
    Captures system/speaker audio.

    - macOS  : Uses ScreenCaptureKit Swift helper binary (no driver install needed).
    - Linux  : Uses PulseAudio/PipeWire monitor source via sounddevice.
    - Windows: Uses pyaudiowpatch WASAPI loopback (no virtual driver needed).
    """

    def __init__(
        self,
        device_index: int | None = None,
        on_error: Callable[[str], None] | None = None,
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._device_index = device_index
        self._on_error = on_error
        self._on_ready = on_ready
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None  # type: ignore[type-arg]

    def _start_capture(self) -> None:
        if sys.platform == "darwin":
            target = self._capture_macos
        elif sys.platform == "win32":
            target = self._capture_wasapi
        else:
            target = self._capture_sounddevice
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def _stop_capture(self) -> None:
        proc = self._proc
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ── macOS: ScreenCaptureKit Swift helper ──────────────────────────────

    def _capture_macos(self) -> None:
        if not HELPER_PATH.exists():
            msg = f"System audio helper not found at:\n  {HELPER_PATH}"
            log.error(msg)
            self._queue.put(None)
            if self._on_error:
                self._on_error(msg)
            return

        # Try up to 4 times — SCK may need several seconds to release after a previous session
        for attempt in range(4):
            if self._stop_event.is_set():
                return
            if attempt > 0:
                import time
                delay = 2.0 + attempt  # 3s, 4s, 5s
                log.info(
                    "Retrying system audio capture in %.0fs (attempt %d/4)…",
                    delay, attempt + 1,
                )
                time.sleep(delay)

            log.info("SystemAudioCapture: spawning %s", HELPER_PATH)
            try:
                proc = subprocess.Popen(
                    [str(HELPER_PATH)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                )
            except OSError as exc:
                msg = f"Failed to launch system audio helper: {exc}"
                log.error(msg)
                self._queue.put(None)
                if self._on_error:
                    self._on_error(msg)
                return

            self._proc = proc

            # Wait for "READY\n" on stderr — binary signals capture has started
            ready = False
            stderr_lines: list[str] = []
            try:
                while True:
                    line = proc.stderr.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    log.debug("helper stderr: %s", text)
                    stderr_lines.append(text)
                    if text == "READY":
                        ready = True
                        break
            except Exception as exc:
                log.warning("Error reading helper stderr: %s", exc)

            stderr_text = "\n".join(stderr_lines)
            needs_permission = "SCREEN_RECORDING_PERMISSION_NEEDED" in stderr_text
            is_transient = (
                not needs_permission
                and (
                    "connection being interrupted" in stderr_text
                    or "application connection" in stderr_text
                )
            )

            if not ready:
                self._proc = None
                proc.wait()
                log.warning(
                    "System audio helper did not start (attempt %d): %s",
                    attempt + 1, stderr_text,
                )
                if is_transient:
                    continue
                if needs_permission or (
                    "Screen Recording" in stderr_text
                    or "permission" in stderr_text.lower()
                    or "TCC" in stderr_text
                ):
                    msg = (
                        "Screen Recording permission is required for system audio.\n\n"
                        "Go to  System Settings → Privacy & Security → Screen Recording\n"
                        "and enable this app, then restart."
                    )
                else:
                    msg = (
                        f"System audio helper failed to start.\n\n"
                        f"{stderr_text or '(no output from helper)'}"
                    )
                self._queue.put(None)
                if self._on_error:
                    self._on_error(msg)
                return

            if is_transient:
                self._proc = None
                proc.terminate()
                proc.wait()
                log.warning(
                    "System audio helper reported stream interruption with READY (attempt %d), retrying…",
                    attempt + 1,
                )
                continue

            break  # genuinely ready
        else:
            log.error("System audio helper failed after retries")
            self._queue.put(None)
            if self._on_error:
                self._on_error(
                    "System audio failed to start.\n\n"
                    "If you haven't yet, grant Screen Recording permission:\n"
                    "System Settings → Privacy & Security → Screen Recording\n"
                    "Enable Terminal (or ByteBabel), then try again."
                )
            return

        log.info("System audio capture ready — streaming PCM")
        if self._on_ready:
            self._on_ready()
        chunks_logged = 0
        try:
            while not self._stop_event.is_set():
                data = proc.stdout.read(_MACOS_CHUNK_BYTES)
                if not data:
                    if not self._stop_event.is_set():
                        log.error("System audio helper exited unexpectedly")
                        self._queue.put(None)
                        if self._on_error:
                            self._on_error("System audio stopped unexpectedly. Try again.")
                    break
                if chunks_logged < 10:
                    samples = np.frombuffer(data, dtype=np.int16)
                    peak = int(np.max(np.abs(samples)))
                    log.debug("PCM chunk %d: %d bytes, peak=%d", chunks_logged + 1, len(data), peak)
                    chunks_logged += 1
                if not self._stop_event.is_set():
                    try:
                        self._queue.put_nowait(data)
                    except queue.Full:
                        pass
        finally:
            log.info("System audio capture stopped")
            self._proc = None
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    # ── sounddevice path (Linux) ──────────────────────────────────────────

    def _capture_sounddevice(self) -> None:
        import sounddevice as sd

        log.info("SystemAudioCapture: opening sounddevice stream (device=%s)", self._device_index)
        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_FRAMES,
                device=self._device_index,
                callback=self._sd_callback,
            ):
                log.info("System audio stream open")
                if self._on_ready:
                    self._on_ready()
                while not self._stop_event.is_set():
                    self._stop_event.wait(timeout=0.1)
                log.info("System audio stream closed")
        except Exception as exc:
            log.error("System audio error: %s", exc, exc_info=True)
            self._queue.put(None)
            raise

    def _sd_callback(self, indata: bytes, frames: int, time_info: object, status: object) -> None:
        if not self._stop_event.is_set():
            try:
                self._queue.put_nowait(bytes(indata))
            except queue.Full:
                pass

    # ── WASAPI loopback (Windows) ─────────────────────────────────────────

    def _capture_wasapi(self) -> None:
        try:
            import pyaudiowpatch as pyaudio  # type: ignore[import]
        except ImportError:
            raise NoLoopbackDeviceError(
                "pyaudiowpatch is required for system audio on Windows.\n"
                "Install it with: pip install pyaudiowpatch"
            )

        pa = pyaudio.PyAudio()
        try:
            device_index = self._device_index
            if device_index is None:
                device_index = self._find_wasapi_loopback(pa)

            info = pa.get_device_info_by_index(device_index)
            channels = min(int(info["maxInputChannels"]), 2)
            sample_rate = int(info["defaultSampleRate"])

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK_FRAMES,
            )
            try:
                if self._on_ready:
                    self._on_ready()
                while not self._stop_event.is_set():
                    raw = stream.read(CHUNK_FRAMES, exception_on_overflow=False)
                    pcm = self._resample_to_16k_mono(raw, channels, sample_rate)
                    if not self._stop_event.is_set():
                        try:
                            self._queue.put_nowait(pcm)
                        except queue.Full:
                            pass
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()

    def _find_wasapi_loopback(self, pa: object) -> int:
        for i in range(pa.get_device_count()):  # type: ignore[attr-defined]
            info = pa.get_device_info_by_index(i)
            if info.get("isLoopbackDevice", False):
                return i
        raise NoLoopbackDeviceError(
            "No WASAPI loopback device found.\n"
            "Make sure your audio driver supports WASAPI loopback."
        )

    def _resample_to_16k_mono(self, raw: bytes, channels: int, src_rate: int) -> bytes:
        arr = np.frombuffer(raw, dtype=np.int16)
        if channels > 1:
            arr = arr.reshape(-1, channels).mean(axis=1).astype(np.int16)
        if src_rate != SAMPLE_RATE:
            ratio = SAMPLE_RATE / src_rate
            new_len = int(len(arr) * ratio)
            indices = np.linspace(0, len(arr) - 1, new_len)
            arr = np.interp(indices, np.arange(len(arr)), arr).astype(np.int16)
        return arr.tobytes()
