"""Settings management — persists to ~/.bytebabel/config.json.
API key is stored in OS-native credential store via keyring.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import keyring
from dotenv import load_dotenv

load_dotenv()

_APP_NAME        = "bytebabel"
_CONFIG_DIR      = Path.home() / ".bytebabel"
_CONFIG_FILE     = _CONFIG_DIR / "config.json"
_KEYRING_SERVICE = "bytebabel-soniox"
_KEYRING_USERNAME = "api_key"

_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "language": "auto",
    "translation_target": "vi",
    "enable_diarization": False,
    "last_device_mic": None,
    "last_device_system": None,
    "last_mode": "microphone",
    "window_width": 1100,
    "window_height": 700,
}


def _load_raw() -> dict[str, Any]:
    if _CONFIG_FILE.exists():
        try:
            with _CONFIG_FILE.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_raw(data: dict[str, Any]) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with _CONFIG_FILE.open("w") as f:
        json.dump(data, f, indent=2)


class Settings:
    def __init__(self) -> None:
        raw = _load_raw()
        self._data: dict[str, Any] = {**_DEFAULTS, **raw}

    # ── API key (keyring + env fallback) ──────────────────────────────────

    @property
    def api_key(self) -> str:
        env_key = os.environ.get("SONIOX_API_KEY", "")
        if env_key:
            return env_key
        stored = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        return stored or ""

    @api_key.setter
    def api_key(self, value: str) -> None:
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, value)

    # ── Generic prefs ─────────────────────────────────────────────────────

    def get(self, key: str) -> Any:
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._persist()

    def _persist(self) -> None:
        _save_raw(self._data)

    # ── Convenience properties ────────────────────────────────────────────

    @property
    def theme(self) -> str:
        v = self._data.get("theme", "dark")
        return v if v in ("dark", "light") else "dark"

    @theme.setter
    def theme(self, v: str) -> None:
        self.set("theme", v)

    @property
    def language(self) -> str:
        return self._data.get("language", "auto")

    @language.setter
    def language(self, v: str) -> None:
        self.set("language", v)

    @property
    def translation_target(self) -> str | None:
        val = self._data.get("translation_target", "vi")
        return val if val else None

    @translation_target.setter
    def translation_target(self, v: str | None) -> None:
        self.set("translation_target", v or "")

    @property
    def enable_diarization(self) -> bool:
        return bool(self._data.get("enable_diarization", False))

    @enable_diarization.setter
    def enable_diarization(self, v: bool) -> None:
        self.set("enable_diarization", v)

    @property
    def last_mode(self) -> str:
        return self._data.get("last_mode", "microphone")

    @last_mode.setter
    def last_mode(self, v: str) -> None:
        self.set("last_mode", v)


# Module-level singleton
settings = Settings()
