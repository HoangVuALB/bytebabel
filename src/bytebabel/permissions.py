"""OS-level permission checks for microphone and audio access."""

from __future__ import annotations

import sys
from enum import Enum


class PermissionStatus(Enum):
    GRANTED        = "granted"
    DENIED         = "denied"
    NOT_DETERMINED = "not_determined"
    UNKNOWN        = "unknown"


def check_microphone_permission() -> PermissionStatus:
    if sys.platform == "darwin":
        return _check_macos_mic()
    elif sys.platform == "win32":
        return _check_windows_mic()
    else:
        return _check_linux_audio()


def request_microphone_permission() -> PermissionStatus:
    """Request mic permission (macOS only — other platforms just return status)."""
    if sys.platform == "darwin":
        return _request_macos_mic()
    return check_microphone_permission()


def get_permission_instructions(status: PermissionStatus) -> str:
    if status == PermissionStatus.GRANTED:
        return ""
    if sys.platform == "darwin":
        return (
            "Microphone access is required.\n\n"
            "Go to: System Settings → Privacy & Security → Microphone\n"
            "Enable access for this app, then restart."
        )
    elif sys.platform == "win32":
        return (
            "Microphone access is required.\n\n"
            "Go to: Settings → Privacy & Security → Microphone\n"
            'Enable "Let apps access your microphone".'
        )
    else:
        return (
            "Microphone access is required.\n\n"
            "Make sure your user is in the 'audio' group:\n"
            "  sudo usermod -aG audio $USER\n"
            "Then log out and log back in."
        )


# ── macOS ─────────────────────────────────────────────────────────────────────


def _check_macos_mic() -> PermissionStatus:
    try:
        import AVFoundation  # type: ignore[import]

        media_type = AVFoundation.AVMediaTypeAudio
        status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(media_type)
        mapping = {
            0: PermissionStatus.NOT_DETERMINED,
            1: PermissionStatus.DENIED,
            2: PermissionStatus.DENIED,
            3: PermissionStatus.GRANTED,
        }
        return mapping.get(status, PermissionStatus.UNKNOWN)
    except ImportError:
        return PermissionStatus.UNKNOWN


def _request_macos_mic() -> PermissionStatus:
    try:
        import AVFoundation  # type: ignore[import]
        import threading

        result: list[PermissionStatus] = [PermissionStatus.NOT_DETERMINED]
        event = threading.Event()

        def handler(granted: bool) -> None:
            result[0] = PermissionStatus.GRANTED if granted else PermissionStatus.DENIED
            event.set()

        media_type = AVFoundation.AVMediaTypeAudio
        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            media_type, handler
        )
        event.wait(timeout=30)
        return result[0]
    except ImportError:
        return PermissionStatus.UNKNOWN


# ── Windows ───────────────────────────────────────────────────────────────────


def _check_windows_mic() -> PermissionStatus:
    try:
        import winreg  # type: ignore[import]

        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Value")
            return PermissionStatus.GRANTED if value == "Allow" else PermissionStatus.DENIED
    except Exception:
        return PermissionStatus.UNKNOWN


# ── Linux ─────────────────────────────────────────────────────────────────────


def _check_linux_audio() -> PermissionStatus:
    import grp
    import os

    try:
        audio_group = grp.getgrnam("audio")
        import pwd
        username = pwd.getpwuid(os.getuid()).pw_name
        if username in audio_group.gr_mem:
            return PermissionStatus.GRANTED
        return PermissionStatus.UNKNOWN
    except Exception:
        return PermissionStatus.UNKNOWN
