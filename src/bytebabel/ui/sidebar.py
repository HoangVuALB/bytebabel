"""History sidebar — file manager for saved transcripts."""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from ..logger import get_logger

log = get_logger("ui.sidebar")

_TRANSCRIPTS_DIR = Path.home() / ".bytebabel" / "transcripts"

# Palette
_PANEL_BG    = ("#E8E8EE", "#0A0A12")
_SECTION_FG  = ("#AAAAAA", "#444455")
_ITEM_BG     = ("#FFFFFF", "#16161E")
_ITEM_HOV    = ("#F0F0F6", "#1E1E2A")
_ITEM_SEL    = ("#D8EAFF", "#1A2A3A")
_LIVE_COLOR  = "#E05050"
_TIME_COLOR  = ("#333333", "#DDDDDD")
_DEL_COLOR   = ("#BBBBBB", "#555566")


class HistoryPanel(ctk.CTkFrame):
    """
    Left-side history panel.
    Shows saved transcripts grouped by date, plus a LIVE indicator when recording.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select: Callable[[Path], None] | None = None,
        on_delete: Callable[[Path], None] | None = None,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("fg_color", _PANEL_BG)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._on_select = on_select
        self._on_delete = on_delete
        self._is_live = False
        self._selected_path: Path | None = None
        self._rows: list[tuple[Path, ctk.CTkFrame]] = []

        self._build_ui()
        self._refresh()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(
            self, fg_color=("gray80", "#050509"), corner_radius=0, height=36
        )
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            text="HISTORY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_SECTION_FG,
        ).pack(side="left", padx=12, pady=8)

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("gray70", "#2A2A3A"),
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

    # ── Public API ────────────────────────────────────────────────────────

    def set_live(self, active: bool) -> None:
        """Show/hide the LIVE indicator at top of list."""
        self._is_live = active
        self._refresh()

    def refresh(self) -> None:
        """Public refresh — called by window on transcription save."""
        self._refresh()

    # ── Internal ──────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        # Clear existing rows
        for widget in self._scroll.winfo_children():
            widget.destroy()
        self._rows.clear()

        row_idx = 0

        # LIVE row
        if self._is_live:
            self._make_live_row(row_idx)
            row_idx += 1
            self._make_separator(row_idx)
            row_idx += 1

        # Load files
        files = self._load_files()
        if not files:
            if not self._is_live:
                ctk.CTkLabel(
                    self._scroll,
                    text="No saved sessions yet",
                    text_color=_SECTION_FG,
                    font=ctk.CTkFont(size=11, slant="italic"),
                ).grid(row=row_idx, column=0, pady=20)
            # Schedule next refresh
            self.after(5000, self._refresh)
            return

        # Group by date
        grouped: dict[str, list[Path]] = {}
        for f in files:
            try:
                dt = datetime.strptime(f.stem, "%Y-%m-%d_%H-%M-%S")
                key = _date_label(dt.date())
            except ValueError:
                key = "Other"
            grouped.setdefault(key, []).append(f)

        for group_label, group_files in grouped.items():
            # Section header
            ctk.CTkLabel(
                self._scroll,
                text=group_label.upper(),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=_SECTION_FG,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="w", padx=10, pady=(8, 2))
            row_idx += 1

            for path in group_files:
                item = self._make_file_row(row_idx, path)
                self._rows.append((path, item))
                row_idx += 1

        self.after(5000, self._refresh)

    def _load_files(self) -> list[Path]:
        if not _TRANSCRIPTS_DIR.exists():
            return []
        files = sorted(
            _TRANSCRIPTS_DIR.glob("*.txt"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        return files

    def _make_live_row(self, row_idx: int) -> None:
        frame = ctk.CTkFrame(
            self._scroll, fg_color=("white", "#1C1022"),
            corner_radius=6, border_width=1, border_color=("#FFCCCC", "#4A1A1A"),
        )
        frame.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=(6, 2))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="●",
            text_color=_LIVE_COLOR,
            font=ctk.CTkFont(size=10),
        ).grid(row=0, column=0, padx=(10, 4), pady=8)

        ctk.CTkLabel(
            frame, text="LIVE",
            text_color=_LIVE_COLOR,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=8)

    def _make_separator(self, row_idx: int) -> None:
        ctk.CTkFrame(
            self._scroll, height=1, fg_color=("gray80", "#222230"), corner_radius=0
        ).grid(row=row_idx, column=0, sticky="ew", padx=8, pady=2)

    def _make_file_row(self, row_idx: int, path: Path) -> ctk.CTkFrame:
        try:
            dt = datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
            time_str = dt.strftime("%H:%M")
        except ValueError:
            time_str = path.stem[:8]

        is_selected = path == self._selected_path
        bg = _ITEM_SEL if is_selected else _ITEM_BG

        frame = ctk.CTkFrame(
            self._scroll, fg_color=bg, corner_radius=6,
        )
        frame.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        inner.grid_columnconfigure(0, weight=1)

        time_lbl = ctk.CTkLabel(
            inner, text=time_str,
            font=ctk.CTkFont(size=13),
            text_color=_TIME_COLOR,
            anchor="w",
        )
        time_lbl.grid(row=0, column=0, sticky="w", padx=(10, 4), pady=6)

        del_btn = ctk.CTkButton(
            inner, text="🗑",
            width=28, height=22,
            fg_color="transparent",
            hover_color=("gray80", "#2A2A3A"),
            text_color=_DEL_COLOR,
            font=ctk.CTkFont(size=12),
            command=lambda p=path: self._on_delete_click(p),
        )
        del_btn.grid(row=0, column=1, padx=(0, 6), pady=4)

        # Click to select
        for widget in (frame, inner, time_lbl):
            widget.bind("<Button-1>", lambda e, p=path: self._on_select_click(p))

        return frame

    def _on_select_click(self, path: Path) -> None:
        self._selected_path = path
        if self._on_select:
            self._on_select(path)
        self._refresh()

    def _on_delete_click(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            log.warning("Failed to delete %s: %s", path, exc)
        if path == self._selected_path:
            self._selected_path = None
        if self._on_delete:
            self._on_delete(path)
        self._refresh()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_label(d: date) -> str:
    today = date.today()
    delta = (today - d).days
    if delta == 0:
        return "Today"
    elif delta == 1:
        return "Yesterday"
    else:
        return d.strftime("%B %d")
