"""Top toolbar — app name, history toggle, theme switch, settings, start/stop."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..config import settings
from ..logger import get_logger

log = get_logger("ui.toolbar")

_ACCENT    = "#4F46E5"   # indigo
_STOP_RED  = "#B91C1C"
_START_GRN = "#15803D"


class Toolbar(ctk.CTkFrame):
    """
    Single-row toolbar:
      [ByteBabel]  ···  [📂]  [☾/☀]  [⚙]  [▶ Start / ■ Stop]
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_start: Callable[[], None],
        on_stop:  Callable[[], None],
        on_toggle_history: Callable[[], None],
        on_settings: Callable[[], None],
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("fg_color", ("gray90", "#0E0E16"))
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._on_start = on_start
        self._on_stop  = on_stop
        self._on_toggle_history = on_toggle_history
        self._on_settings = on_settings
        self._recording = False

        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)  # spacer
        pad = {"padx": 6, "pady": 8}

        # App name / logo
        ctk.CTkLabel(
            self,
            text="ByteBabel",
            font=ctk.CTkFont(family="Helvetica Neue", size=17, weight="bold"),
            text_color=_ACCENT,
        ).grid(row=0, column=0, padx=(14, 8), pady=8)

        # Spacer
        ctk.CTkFrame(self, fg_color="transparent").grid(row=0, column=1, sticky="ew")

        # 📂 History toggle
        self._history_btn = ctk.CTkButton(
            self, text="📂",
            width=36, height=30,
            fg_color="transparent",
            hover_color=("gray80", "#222230"),
            font=ctk.CTkFont(size=15),
            command=self._on_toggle_history,
        )
        self._history_btn.grid(row=0, column=2, **pad)

        # ☾/☀ Theme toggle
        self._theme_btn = ctk.CTkButton(
            self,
            text=self._theme_icon(),
            width=36, height=30,
            fg_color="transparent",
            hover_color=("gray80", "#222230"),
            font=ctk.CTkFont(size=15),
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=3, **pad)

        # ⚙ Settings
        ctk.CTkButton(
            self, text="⚙",
            width=36, height=30,
            fg_color="transparent",
            hover_color=("gray80", "#222230"),
            font=ctk.CTkFont(size=16),
            command=self._on_settings,
        ).grid(row=0, column=4, **pad)

        # ▶ Start / ■ Stop
        self._action_btn = ctk.CTkButton(
            self, text="▶  Start",
            width=110, height=30,
            fg_color=_START_GRN,
            hover_color="#166534",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._toggle,
        )
        self._action_btn.grid(row=0, column=5, padx=(4, 12), pady=8)

    # ── State ─────────────────────────────────────────────────────────────

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if recording:
            self._action_btn.configure(
                text="■  Stop", fg_color=_STOP_RED, hover_color="#991B1B"
            )
        else:
            self._action_btn.configure(
                text="▶  Start", fg_color=_START_GRN, hover_color="#166534"
            )

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _toggle(self) -> None:
        if self._recording:
            self._on_stop()
        else:
            self._on_start()

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode().lower()
        new_theme = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new_theme)
        settings.theme = new_theme
        self._theme_btn.configure(text=self._theme_icon())

    @staticmethod
    def _theme_icon() -> str:
        return "☀" if ctk.get_appearance_mode().lower() == "dark" else "☾"
