"""Top toolbar — app name, history toggle, theme switch, settings, start/stop."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..config import settings
from ..logger import get_logger
from . import theme as T

log = get_logger("ui.toolbar")


class Toolbar(ctk.CTkFrame):
    """
    Single-row toolbar:
      [ByteBabel]  ···  [📂]  [☾/☀]  [⚙]  [▶ Start / ■ Stop]
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_toggle_history: Callable[[], None],
        on_settings: Callable[[], None],
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("fg_color", T.BG_ELEVATED)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("height", 44)
        super().__init__(master, **kwargs)
        self.grid_propagate(False)

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_toggle_history = on_toggle_history
        self._on_settings = on_settings
        self._recording = False

        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # App name
        ctk.CTkLabel(
            self,
            text="ByteBabel",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=15, weight="bold"),
            text_color=T.ACCENT,
        ).grid(row=0, column=0, padx=(T.PAD_LG, T.PAD_SM))

        # Spacer
        ctk.CTkFrame(self, fg_color="transparent").grid(row=0, column=1, sticky="ew")

        icon_kw = dict(
            width=32,
            height=28,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent",
            hover_color=T.BORDER_SUBTLE,
            font=ctk.CTkFont(size=15),
            text_color=T.TEXT_SECONDARY,
        )

        self._history_btn = ctk.CTkButton(
            self,
            text="📂",
            command=self._on_toggle_history,
            **icon_kw,  # type: ignore[arg-type]
        )
        self._history_btn.grid(row=0, column=2, padx=2)

        self._theme_btn = ctk.CTkButton(
            self,
            text=self._theme_icon(),
            command=self._toggle_theme,
            **icon_kw,  # type: ignore[arg-type]
        )
        self._theme_btn.grid(row=0, column=3, padx=2)

        ctk.CTkButton(
            self,
            text="⚙",
            command=self._on_settings,
            **icon_kw,  # type: ignore[arg-type]
        ).grid(row=0, column=4, padx=2)

        self._action_btn = ctk.CTkButton(
            self,
            text="▶  Start",
            width=100,
            height=30,
            corner_radius=T.RADIUS_LG,
            fg_color=T.SUCCESS,
            hover_color=("#138A3E", "#38C96E"),
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            text_color=T.TEXT_INVERSE,
            command=self._toggle,
        )
        self._action_btn.grid(row=0, column=5, padx=(T.PAD_SM, T.PAD_LG))

    # ── State ─────────────────────────────────────────────────────────────

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if recording:
            self._action_btn.configure(
                text="■  Stop",
                fg_color=T.DANGER,
                hover_color=("#B91C1C", "#EF4444"),
            )
        else:
            self._action_btn.configure(
                text="▶  Start",
                fg_color=T.SUCCESS,
                hover_color=("#138A3E", "#38C96E"),
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
