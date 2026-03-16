"""App orchestrator — ties audio capture, Soniox transcriber, and UI together."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .logger import get_logger

log = get_logger("app")

from .audio.base import MicCapture
from .audio.devices import AudioDevice
from .audio.system import NoLoopbackDeviceError, SystemAudioCapture
from .config import settings
from .permissions import (
    PermissionStatus,
    check_microphone_permission,
    get_permission_instructions,
    request_microphone_permission,
)
from .transcription.soniox import SonioxTranscriber, TranscriptUpdate

if TYPE_CHECKING:
    from .ui.window import AppWindow


class App:
    def __init__(self, window: "AppWindow") -> None:
        self._window = window
        self._capture = None
        self._transcriber: SonioxTranscriber | None = None

    def start_transcription(
        self,
        mode: str,
        device: AudioDevice | None,
        language: str,
        translation_target: str | None = None,
    ) -> None:
        log.info(
            "start_transcription: mode=%s device=%s language=%s translation=%s",
            mode, device, language, translation_target,
        )

        api_key = settings.api_key
        if not api_key:
            self._window.post_update(
                TranscriptUpdate(
                    final_text="", non_final_text="",
                    error=(
                        "No Soniox API key configured.\n"
                        "Open Settings (⚙) and enter your API key."
                    ),
                )
            )
            return

        if mode == "microphone":
            status = check_microphone_permission()
            if status == PermissionStatus.DENIED:
                self._window.post_update(
                    TranscriptUpdate(final_text="", non_final_text="",
                                     error=get_permission_instructions(status))
                )
                return
            elif status == PermissionStatus.NOT_DETERMINED:
                status = request_microphone_permission()
                if status == PermissionStatus.DENIED:
                    self._window.post_update(
                        TranscriptUpdate(final_text="", non_final_text="",
                                         error=get_permission_instructions(status))
                    )
                    return

        device_index = device.index if device else None
        if device_index == -1:  # SCK virtual device sentinel
            device_index = None

        try:
            if mode == "microphone":
                self._capture = MicCapture(device_index=device_index)
            else:
                self._capture = SystemAudioCapture(
                    device_index=device_index,
                    on_error=lambda err: self._window.post_update(
                        TranscriptUpdate(final_text="", non_final_text="", error=err)
                    ),
                    on_ready=self._on_capture_ready,
                )
        except NoLoopbackDeviceError as exc:
            self._window.post_update(
                TranscriptUpdate(final_text="", non_final_text="", error=str(exc))
            )
            return

        log.info("Starting capture (%s)", type(self._capture).__name__)
        self._transcriber = SonioxTranscriber(
            api_key=api_key,
            on_update=self._window.post_update,
            language=language,
            enable_diarization=settings.enable_diarization,
            translation_target=translation_target,
        )

        self._capture.start()
        if mode == "microphone":
            log.info("Starting Soniox transcriber")
            self._transcriber.start(self._capture.get_stream())

    def _on_capture_ready(self) -> None:
        """Called from capture thread when system audio is confirmed streaming."""
        if self._transcriber is not None and self._capture is not None:
            log.info("System audio ready — starting Soniox transcriber")
            self._transcriber.start(self._capture.get_stream())

    def stop_transcription(self) -> None:
        log.info("Stopping transcription")
        if self._transcriber is not None:
            self._transcriber.stop()
            self._transcriber = None
        if self._capture is not None:
            self._capture.stop()
            self._capture = None
