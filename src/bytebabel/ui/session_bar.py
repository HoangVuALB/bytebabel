"""Session bar — audio source mode, source language, target language."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..audio.devices import AudioDevice, list_mic_devices, list_system_audio_devices
from ..config import settings
from ..logger import get_logger

log = get_logger("ui.session_bar")

# Languages available in the session bar
_SOURCE_LANGUAGES = [
    ("Auto",      "auto"),
    ("日本語",     "ja"),
    ("Tiếng Việt","vi"),
    ("English",   "en"),
]

_TARGET_LANGUAGES = [
    ("No translation", ""),
    ("日本語",          "ja"),
    ("Tiếng Việt",     "vi"),
    ("English",        "en"),
]


class SessionBar(ctk.CTkFrame):
    """
    Single-row controls under the toolbar:
      [🎤 External Mic ▼]  │  [日本語 ▼]  │  [→ Tiếng Việt ▼]
    Disabled while recording.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("fg_color", ("gray85", "#090911"))
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._mic_devices: list[AudioDevice]    = []
        self._sys_devices: list[AudioDevice]    = []

        self._build_ui()
        self._refresh_devices()
        self._restore_saved()

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """'microphone' or 'system'"""
        return "microphone" if self._mode_var.get() == "Microphone" else "system"

    @property
    def selected_device(self) -> AudioDevice | None:
        name = self._device_var.get()
        devices = self._mic_devices if self.mode == "microphone" else self._sys_devices
        return next((d for d in devices if d.name == name), None)

    @property
    def source_language(self) -> str:
        label = self._src_lang_var.get()
        return next((l[1] for l in _SOURCE_LANGUAGES if l[0] == label), "auto")

    @property
    def target_language(self) -> str | None:
        label = self._tgt_lang_var.get()
        code = next((l[1] for l in _TARGET_LANGUAGES if l[0] == label), "")
        return code if code else None

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 7}

        # Mode toggle (Microphone / System Audio)
        self._mode_var = ctk.StringVar(value="Microphone")
        self._mode_seg = ctk.CTkSegmentedButton(
            self,
            values=["Microphone", "System Audio"],
            variable=self._mode_var,
            command=self._on_mode_change,
            width=210,
        )
        self._mode_seg.grid(row=0, column=0, **pad)

        # Divider
        ctk.CTkFrame(
            self, width=1, fg_color=("gray70", "#2A2A3A"), corner_radius=0
        ).grid(row=0, column=1, sticky="ns", padx=0, pady=6)

        # Device dropdown
        self._device_var = ctk.StringVar()
        self._device_combo = ctk.CTkComboBox(
            self,
            variable=self._device_var,
            values=[],
            width=200,
            state="readonly",
        )
        self._device_combo.grid(row=0, column=2, **pad)

        # Refresh devices
        ctk.CTkButton(
            self, text="⟳",
            width=30, height=28,
            fg_color="transparent",
            hover_color=("gray75", "#222230"),
            command=self._refresh_devices,
        ).grid(row=0, column=3, padx=(0, 8), pady=7)

        # Divider
        ctk.CTkFrame(
            self, width=1, fg_color=("gray70", "#2A2A3A"), corner_radius=0
        ).grid(row=0, column=4, sticky="ns", padx=0, pady=6)

        # Source language
        src_labels = [l[0] for l in _SOURCE_LANGUAGES]
        self._src_lang_var = ctk.StringVar()
        ctk.CTkComboBox(
            self,
            variable=self._src_lang_var,
            values=src_labels,
            width=120,
            state="readonly",
        ).grid(row=0, column=5, **pad)

        # Arrow label
        ctk.CTkLabel(
            self, text="→",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray55"),
        ).grid(row=0, column=6, padx=4)

        # Target language
        tgt_labels = [l[0] for l in _TARGET_LANGUAGES]
        self._tgt_lang_var = ctk.StringVar()
        ctk.CTkComboBox(
            self,
            variable=self._tgt_lang_var,
            values=tgt_labels,
            width=140,
            state="readonly",
        ).grid(row=0, column=7, **pad)

        # Spacer
        self.grid_columnconfigure(8, weight=1)

    # ── Interactions ──────────────────────────────────────────────────────

    def _on_mode_change(self, _: str) -> None:
        self._populate_device_list()

    def _refresh_devices(self) -> None:
        self._mic_devices = list_mic_devices()
        self._sys_devices = list_system_audio_devices()
        self._populate_device_list()

    def _populate_device_list(self) -> None:
        devices = self._mic_devices if self.mode == "microphone" else self._sys_devices
        names = [d.name for d in devices]
        if not names:
            names = ["No device found"]
        self._device_combo.configure(values=names)
        # Restore last used device
        key = "last_device_mic" if self.mode == "microphone" else "last_device_system"
        last = settings.get(key)
        if last and last in names:
            self._device_var.set(last)
        elif names:
            self._device_var.set(names[0])

    def _restore_saved(self) -> None:
        """Restore persisted session bar settings."""
        last_mode = settings.last_mode
        self._mode_var.set("Microphone" if last_mode == "microphone" else "System Audio")
        self._populate_device_list()

        lang_code = settings.language
        label = next((l[0] for l in _SOURCE_LANGUAGES if l[1] == lang_code), "Auto")
        self._src_lang_var.set(label)

        trans_code = settings.translation_target or ""
        tlabel = next((t[0] for t in _TARGET_LANGUAGES if t[1] == trans_code), "No translation")
        self._tgt_lang_var.set(tlabel)

    # ── Enable / disable ──────────────────────────────────────────────────

    def set_recording(self, recording: bool) -> None:
        state = "disabled" if recording else "readonly"
        normal = "disabled" if recording else "normal"
        self._mode_seg.configure(state=normal)
        self._device_combo.configure(state=state)
        for col in (5, 7):
            for widget in self.grid_slaves(row=0, column=col):
                widget.configure(state=state)

    def persist(self) -> None:
        """Save current selections to config."""
        settings.last_mode = self.mode
        dev = self.selected_device
        if dev:
            key = "last_device_mic" if self.mode == "microphone" else "last_device_system"
            settings.set(key, dev.name)
        lang_code = self.source_language
        settings.language = lang_code
        trans = self.target_language
        settings.translation_target = trans
