"""Collapsible log viewer panel — drains ui_log_queue via after() polling."""

from __future__ import annotations

import logging
import subprocess
import sys

import customtkinter as ctk

from ..logger import LOG_FILE, ui_log_queue

# Level name → (light-mode colour, dark-mode colour)
_TAG_COLORS: dict[str, tuple[str, str]] = {
    "DEBUG":    ("#888888", "#666666"),
    "INFO":     ("#111111", "#cccccc"),
    "WARNING":  ("#b85c00", "#f0a500"),
    "ERROR":    ("#cc0000", "#ff5555"),
    "CRITICAL": ("#990000", "#ff2222"),
}

_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

MAX_LINES = 2000


class LogPanel(ctk.CTkFrame):
    """Scrollable log viewer that polls ui_log_queue every 100 ms."""

    def __init__(self, master: ctk.CTk, **kwargs: object) -> None:
        super().__init__(master, corner_radius=0, **kwargs)  # type: ignore[arg-type]
        self._min_level = logging.DEBUG
        self._line_count = 0
        self._build()
        self._configure_tags()
        self._poll()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, height=28, fg_color=("gray80", "gray20"), corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="LOGS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray30", "gray70"),
        ).grid(row=0, column=0, padx=(10, 6), pady=2)

        self._level_var = ctk.StringVar(value="DEBUG")
        ctk.CTkOptionMenu(
            header,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self._level_var,
            command=self._on_level_change,
            width=95, height=22,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=4, pady=3)

        ctk.CTkButton(
            header, text="Clear", width=55, height=22,
            font=ctk.CTkFont(size=11), command=self._clear,
        ).grid(row=0, column=3, padx=4, pady=3)

        ctk.CTkButton(
            header, text="Open File", width=75, height=22,
            font=ctk.CTkFont(size=11), command=self._open_file,
        ).grid(row=0, column=4, padx=(0, 10), pady=3)

        self._text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(
                family="Menlo" if sys.platform == "darwin" else "Consolas", size=11
            ),
            corner_radius=0,
            activate_scrollbars=True,
            state="disabled",
            wrap="none",
        )
        self._text.grid(row=1, column=0, sticky="nsew")

    def _configure_tags(self) -> None:
        tw = self._text._textbox  # type: ignore[attr-defined]
        is_dark = ctk.get_appearance_mode() == "Dark"
        for level, (light, dark) in _TAG_COLORS.items():
            tw.tag_configure(level, foreground=dark if is_dark else light)

    def _on_level_change(self, value: str) -> None:
        self._min_level = getattr(logging, value, logging.DEBUG)

    def _clear(self) -> None:
        tw = self._text._textbox  # type: ignore[attr-defined]
        tw.configure(state="normal")
        tw.delete("1.0", "end")
        tw.configure(state="disabled")
        self._line_count = 0

    def _open_file(self) -> None:
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(LOG_FILE)], check=False)
            elif sys.platform == "win32":
                subprocess.run(["notepad", str(LOG_FILE)], check=False)
            else:
                subprocess.run(["xdg-open", str(LOG_FILE)], check=False)
        except Exception:
            pass

    def _poll(self) -> None:
        try:
            while True:
                record: logging.LogRecord = ui_log_queue.get_nowait()
                if record.levelno >= self._min_level:
                    self._append(record)
        except Exception:
            pass
        self.after(100, self._poll)

    def _append(self, record: logging.LogRecord) -> None:
        line = _FORMATTER.format(record) + "\n"
        tw = self._text._textbox  # type: ignore[attr-defined]
        tw.configure(state="normal")
        if self._line_count >= MAX_LINES:
            tw.delete("1.0", "201.0")
            self._line_count -= 200
        tw.insert("end", line, record.levelname)
        tw.see("end")
        tw.configure(state="disabled")
        self._line_count += 1
