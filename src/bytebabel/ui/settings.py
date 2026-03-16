"""Settings dialog — API key, language, translation, diarization, theme."""

from __future__ import annotations

import customtkinter as ctk

from ..config import settings
from . import theme as T

# Supported languages: ja, vi, en only
LANGUAGES = [
    ("Auto-detect", "auto"),
    ("日本語", "ja"),
    ("Tiếng Việt", "vi"),
    ("English", "en"),
]

TRANSLATIONS = [
    ("Off", ""),
    ("日本語", "ja"),
    ("Tiếng Việt", "vi"),
    ("English", "en"),
]


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.geometry("520x460")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus()
        self.configure(fg_color=T.BG_ROOT)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        pad = {"padx": T.PAD_XL, "pady": T.PAD_MD}

        # Header
        ctk.CTkLabel(
            self,
            text="Settings",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=18, weight="bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            padx=T.PAD_XL,
            pady=(T.PAD_XL, T.PAD_LG),
        )

        # API Key
        ctk.CTkLabel(
            self,
            text="Soniox API Key",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", **pad)
        self._api_key_var = ctk.StringVar()
        self._api_key_entry = ctk.CTkEntry(
            self,
            textvariable=self._api_key_var,
            show="•",
            width=240,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
        )
        self._api_key_entry.grid(row=1, column=1, sticky="ew", **pad)
        self._show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Show",
            variable=self._show_key_var,
            command=self._toggle_key_visibility,
            width=60,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12),
        ).grid(row=1, column=2, padx=(0, T.PAD_XL), pady=T.PAD_MD)

        ctk.CTkLabel(
            self,
            text="Get your key at console.soniox.com",
            text_color=T.TEXT_TERTIARY,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            anchor="w",
        ).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=T.PAD_XL, pady=(0, T.PAD_SM)
        )

        # Source Language
        ctk.CTkLabel(
            self,
            text="Transcribe",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=3, column=0, sticky="w", **pad)
        lang_labels = [l[0] for l in LANGUAGES]
        self._lang_var = ctk.StringVar()
        ctk.CTkComboBox(
            self,
            variable=self._lang_var,
            values=lang_labels,
            width=240,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", **pad)

        # Translation Target
        ctk.CTkLabel(
            self,
            text="Translate to",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=4, column=0, sticky="w", **pad)
        trans_labels = [t[0] for t in TRANSLATIONS]
        self._trans_var = ctk.StringVar()
        ctk.CTkComboBox(
            self,
            variable=self._trans_var,
            values=trans_labels,
            width=240,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", **pad)

        # Speaker Labels
        ctk.CTkLabel(
            self,
            text="Speaker Labels",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=5, column=0, sticky="w", **pad)
        self._diarization_var = ctk.BooleanVar()
        ctk.CTkSwitch(
            self,
            text="Identify speakers",
            variable=self._diarization_var,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
        ).grid(row=5, column=1, sticky="w", **pad)

        # Theme
        ctk.CTkLabel(
            self,
            text="Theme",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=6, column=0, sticky="w", **pad)
        self._theme_var = ctk.StringVar()
        ctk.CTkSegmentedButton(
            self,
            values=["Dark", "Light"],
            variable=self._theme_var,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
        ).grid(row=6, column=1, sticky="w", **pad)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=3, pady=(T.PAD_XL, T.PAD_XL))
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color=T.BORDER_MUTED,
            hover_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            command=self.destroy,
        ).pack(side="left", padx=T.PAD_SM)
        ctk.CTkButton(
            btn_frame,
            text="Save",
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_INVERSE,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13, weight="bold"),
            command=self._save,
        ).pack(side="left", padx=T.PAD_SM)

    def _load_values(self) -> None:
        self._api_key_var.set(settings.api_key)

        lang_code = settings.language
        label = next((l[0] for l in LANGUAGES if l[1] == lang_code), "Auto-detect")
        self._lang_var.set(label)

        trans_code = settings.translation_target or ""
        tlabel = next((t[0] for t in TRANSLATIONS if t[1] == trans_code), "Off")
        self._trans_var.set(tlabel)

        self._diarization_var.set(settings.enable_diarization)
        self._theme_var.set(settings.theme.capitalize())

    def _toggle_key_visibility(self) -> None:
        self._api_key_entry.configure(show="" if self._show_key_var.get() else "•")

    def _save(self) -> None:
        api_key = self._api_key_var.get().strip()
        if api_key:
            settings.api_key = api_key

        lang_label = self._lang_var.get()
        lang_code = next((l[1] for l in LANGUAGES if l[0] == lang_label), "auto")
        settings.language = lang_code

        trans_label = self._trans_var.get()
        trans_code = next((t[1] for t in TRANSLATIONS if t[0] == trans_label), "")
        settings.translation_target = trans_code or None

        settings.enable_diarization = self._diarization_var.get()

        theme = self._theme_var.get().lower()
        settings.theme = theme
        ctk.set_appearance_mode(theme)

        self.destroy()
