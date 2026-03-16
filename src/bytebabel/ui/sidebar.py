"""History sidebar — file manager for saved transcripts."""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from ..logger import get_logger
from . import theme as T

log = get_logger("ui.sidebar")

_TRANSCRIPTS_DIR = Path.home() / ".bytebabel" / "transcripts"


class HistoryPanel(ctk.CTkFrame):
    """Left-side history panel with saved transcripts grouped by date."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select: Callable[[Path], None] | None = None,
        on_delete: Callable[[Path], None] | None = None,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("fg_color", T.BG_INSET)
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
        header = ctk.CTkFrame(self, fg_color=T.BG_OVERLAY, corner_radius=0, height=44)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        ctk.CTkLabel(
            header,
            text="HISTORY",
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=T.PAD_LG, pady=T.PAD_SM)

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.SCROLLBAR,
            scrollbar_button_hover_color=T.SCROLLBAR_HOV,
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
                    text_color=T.TEXT_TERTIARY,
                    font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, slant="italic"),
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
                font=ctk.CTkFont(family=T.FONT_FAMILY, size=10, weight="bold"),
                text_color=T.TEXT_TERTIARY,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 2))
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
            self._scroll,
            fg_color=T.DANGER_BG,
            corner_radius=T.RADIUS_SM,
            border_width=1,
            border_color=T.DANGER,
        )
        frame.grid(
            row=row_idx, column=0, sticky="ew", padx=T.PAD_SM, pady=(T.PAD_SM, 2)
        )
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="●",
            text_color=T.DANGER,
            font=ctk.CTkFont(size=10),
        ).grid(row=0, column=0, padx=(T.PAD_MD, T.PAD_XS), pady=T.PAD_SM)

        ctk.CTkLabel(
            frame,
            text="LIVE",
            text_color=T.DANGER,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=T.PAD_SM)

    def _make_separator(self, row_idx: int) -> None:
        ctk.CTkFrame(
            self._scroll,
            height=1,
            fg_color=T.BORDER_SUBTLE,
            corner_radius=0,
        ).grid(row=row_idx, column=0, sticky="ew", padx=T.PAD_SM, pady=2)

    def _make_file_row(self, row_idx: int, path: Path) -> ctk.CTkFrame:
        try:
            dt = datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
            time_str = dt.strftime("%H:%M")
        except ValueError:
            time_str = path.stem[:8]

        is_selected = path == self._selected_path
        bg = T.ACCENT_SUBTLE if is_selected else T.BG_SURFACE

        frame = ctk.CTkFrame(
            self._scroll,
            fg_color=bg,
            corner_radius=T.RADIUS_SM,
        )
        frame.grid(row=row_idx, column=0, sticky="ew", padx=T.PAD_SM, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        inner.grid_columnconfigure(0, weight=1)

        time_lbl = ctk.CTkLabel(
            inner,
            text=time_str,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=13),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        )
        time_lbl.grid(
            row=0, column=0, sticky="w", padx=(T.PAD_MD, T.PAD_XS), pady=T.PAD_SM
        )

        del_btn = ctk.CTkButton(
            inner,
            text="✕",
            width=26,
            height=22,
            corner_radius=T.RADIUS_SM,
            fg_color="transparent",
            hover_color=T.DANGER_BG,
            text_color=T.TEXT_TERTIARY,
            font=ctk.CTkFont(size=12),
            command=lambda p=path: self._on_delete_click(p),
        )
        del_btn.grid(row=0, column=1, padx=(0, T.PAD_SM), pady=T.PAD_XS)

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
