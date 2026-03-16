"""Audio capture — base class + MicCapture via sounddevice."""

from __future__ import annotations

import queue
import threading
from abc import ABC, abstractmethod
from typing import Iterator

import numpy as np
import sounddevice as sd

from ..logger import get_logger

log = get_logger("audio.base")

SAMPLE_RATE  = 16000
CHANNELS     = 1
DTYPE        = "int16"
CHUNK_FRAMES = 1024  # ~64 ms at 16 kHz


class AudioCapture(ABC):
    """Abstract audio source — yields raw PCM bytes (pcm_s16le, 16kHz, mono)."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=200)

    def start(self) -> None:
        log.info("%s starting", type(self).__name__)
        self._stop_event.clear()
        self._start_capture()

    def stop(self) -> None:
        log.info("%s stopping", type(self).__name__)
        self._stop_event.set()
        self._stop_capture()
        self._queue.put(None)  # sentinel

    @abstractmethod
    def _start_capture(self) -> None: ...

    @abstractmethod
    def _stop_capture(self) -> None: ...

    def get_stream(self) -> Iterator[bytes]:
        """Yields PCM chunks until stop() is called."""
        while True:
            chunk = self._queue.get()
            if chunk is None:
                break
            yield chunk


class MicCapture(AudioCapture):
    """Captures audio from a microphone using sounddevice."""

    def __init__(self, device_index: int | None = None) -> None:
        super().__init__()
        self._device_index = device_index
        self._stream: sd.RawInputStream | None = None

    def _start_capture(self) -> None:
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_FRAMES,
            device=self._device_index,
            callback=self._callback,
        )
        self._stream.start()

    def _stop_capture(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(
        self,
        indata: bytes,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            log.warning("sounddevice status: %s", status)
        if not self._stop_event.is_set():
            try:
                self._queue.put_nowait(bytes(indata))
            except queue.Full:
                log.warning("Audio queue full — dropping frame")
