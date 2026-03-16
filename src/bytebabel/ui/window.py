"""ByteBabel main application window."""

from __future__ import annotations

import queue
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..config import settings
from ..logger import get_logger
from ..transcription.soniox import TranscriptUpdate
from .logs import LogPanel
from .session_bar import SessionBar
from .settings import SettingsDialog
from .sidebar import HistoryPanel
from .toolbar import Toolbar
from .viewer import TranscriptView

if TYPE_CHECKING:
    from ..app import App

log = get_logger("ui.window")

_TRANSCRIPTS_DIR = Path.home() / ".bytebabel" / "transcripts"
_STATUS_BG       = ("gray84", "#08080F")


class AppWindow(ctk.CTk):
    """Root window for ByteBabel."""

    def __init__(self) -> None:
        ctk.set_appearance_mode(settings.theme)
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("ByteBabel")
        w = settings.get("window_width") or 1100
        h = settings.get("window_height") or 700
        self.geometry(f"{w}x{h}")
        self.minsize(720, 500)

        # Set app icon
        _set_window_icon(self)

        self._update_queue: queue.Queue[TranscriptUpdate] = queue.Queue()
        self._autosave_path: Path | None = None
        self._history_visible = False
        self._log_visible = False

        self._build_ui()
        self._bind_shortcuts()
        self._poll_updates()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Grid: col 0 = sidebar (hidden by default), col 1 = main content
        self.grid_rowconfigure(2, weight=1)   # viewer row expands
        self.grid_columnconfigure(0, minsize=0, weight=0)   # sidebar
        self.grid_columnconfigure(1, weight=1)               # content

        # ── Toolbar ──────────────────────────────────────────────────────
        self._toolbar = Toolbar(
            self,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_toggle_history=self._toggle_history,
            on_settings=self._open_settings,
        )
        self._toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        # ── Session bar ───────────────────────────────────────────────────
        self._session_bar = SessionBar(self)
        self._session_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        # ── Sidebar (history panel) ───────────────────────────────────────
        self._sidebar = HistoryPanel(
            self,
            on_select=self._on_history_select,
            on_delete=self._on_history_delete,
            width=200,
        )
        # NOT gridded yet — shown on demand

        # ── Transcript viewer ─────────────────────────────────────────────
        self._viewer = TranscriptView(self)
        self._viewer.grid(row=2, column=1, sticky="nsew", padx=(0, 8), pady=(6, 0))

        # ── Status bar ────────────────────────────────────────────────────
        status_bar = ctk.CTkFrame(
            self, fg_color=_STATUS_BG, height=26, corner_radius=0
        )
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

        self._status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(
            status_bar,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
        ).pack(side="left", padx=10)

        self._save_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            status_bar,
            textvariable=self._save_var,
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "#56C26E"),
        ).pack(side="left", padx=0)

        self._log_toggle_btn = ctk.CTkButton(
            status_bar, text="Logs ▼",
            width=70, height=20,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray75", "gray30"),
            text_color=("gray40", "gray60"),
            command=self._toggle_logs,
        )
        self._log_toggle_btn.pack(side="right", padx=6, pady=2)

        # ── Log panel (hidden by default) ─────────────────────────────────
        self._log_panel = LogPanel(self, fg_color=("gray88", "#07070E"))

    def _bind_shortcuts(self) -> None:
        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind(f"<{mod}-r>",     lambda _e: self._shortcut_startstop())
        self.bind(f"<{mod}-comma>", lambda _e: self._open_settings())
        self.bind(f"<{mod}-b>",     lambda _e: self._toggle_history())

    # ── App orchestration hooks ───────────────────────────────────────────

    def set_app(self, app: "App") -> None:
        self._app = app

    def _on_start(self) -> None:
        log.info("User pressed Start")
        self._viewer.set_live_mode()
        self._set_status("Connecting…")
        self._save_var.set("")
        self.title("● ByteBabel")
        self._toolbar.set_recording(True)
        self._session_bar.set_recording(True)
        self._sidebar.set_live(True)

        # Prepare auto-save file
        _TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._autosave_path = _TRANSCRIPTS_DIR / f"{ts}.txt"
        log.info("Auto-save: %s", self._autosave_path)

        self._session_bar.persist()
        if hasattr(self, "_app"):
            self._app.start_transcription(
                mode=self._session_bar.mode,
                device=self._session_bar.selected_device,
                language=self._session_bar.source_language,
                translation_target=self._session_bar.target_language,
            )

    def _on_stop(self) -> None:
        log.info("User pressed Stop")
        self._set_status("Stopping…")
        self._toolbar.set_recording(False)
        self._session_bar.set_recording(False)
        self._sidebar.set_live(False)
        self.title("ByteBabel")
        if hasattr(self, "_app"):
            self._app.stop_transcription()

    def _shortcut_startstop(self) -> None:
        if self._toolbar._recording:
            self._on_stop()
        else:
            self._on_start()

    # ── Transcript updates ────────────────────────────────────────────────

    def post_update(self, update: TranscriptUpdate) -> None:
        self._update_queue.put_nowait(update)

    def _poll_updates(self) -> None:
        try:
            while True:
                update = self._update_queue.get_nowait()
                self._apply_update(update)
        except queue.Empty:
            pass
        self.after(50, self._poll_updates)

    def _apply_update(self, update: TranscriptUpdate) -> None:
        if update.error:
            log.error("Transcription error: %s", update.error)
            self._toolbar.set_recording(False)
            self._session_bar.set_recording(False)
            self._sidebar.set_live(False)
            self.title("ByteBabel")
            self._set_status("Error")
            self._show_error_dialog(update.error)
            return

        if update.finished:
            self._set_status("Done.")
            self._toolbar.set_recording(False)
            self._session_bar.set_recording(False)
            self._sidebar.set_live(False)
            self.title("ByteBabel")
            self._do_autosave(update.final_text, update.translated_final_text)
            self._sidebar.refresh()
            return

        self._viewer.update_transcript(
            final_text=update.final_text,
            non_final_text=update.non_final_text,
            translated_final_text=update.translated_final_text,
            translated_non_final_text=update.translated_non_final_text,
        )
        self._set_status("● Recording…")
        self._do_autosave(update.final_text, update.translated_final_text)

    # ── Auto-save ─────────────────────────────────────────────────────────

    def _do_autosave(self, original: str, translation: str) -> None:
        if not self._autosave_path or (not original and not translation):
            return
        try:
            with open(self._autosave_path, "w", encoding="utf-8") as f:
                if original:
                    f.write("=== Original ===\n")
                    f.write(original.strip())
                    f.write("\n\n")
                if translation:
                    f.write("=== Translation ===\n")
                    f.write(translation.strip())
                    f.write("\n")
            self._save_var.set(f"💾 {self._autosave_path.name}")
        except OSError as exc:
            log.warning("Auto-save failed: %s", exc)

    # ── History panel ─────────────────────────────────────────────────────

    def _toggle_history(self) -> None:
        self._history_visible = not self._history_visible
        if self._history_visible:
            self.grid_columnconfigure(0, minsize=200, weight=0)
            self._sidebar.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=(6, 0))
            self._viewer.grid_configure(padx=(4, 8))
        else:
            self._sidebar.grid_remove()
            self.grid_columnconfigure(0, minsize=0, weight=0)
            self._viewer.grid_configure(padx=(0, 8))

    def _on_history_select(self, path: Path) -> None:
        log.info("Opening transcript: %s", path)
        try:
            text = path.read_text(encoding="utf-8")
            original, translation = _parse_transcript_file(text)
            self._viewer.show_file(original, translation)
            self._set_status(f"Viewing {path.name}")
        except Exception as exc:
            log.error("Failed to open transcript: %s", exc)

    def _on_history_delete(self, path: Path) -> None:
        log.info("Deleted transcript: %s", path)

    # ── Log panel toggle ──────────────────────────────────────────────────

    def _toggle_logs(self) -> None:
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.grid_rowconfigure(4, weight=1, minsize=160)
            self._log_panel.grid(row=4, column=0, columnspan=2, sticky="nsew")
            self._log_toggle_btn.configure(text="Logs ▲")
        else:
            self._log_panel.grid_remove()
            self.grid_rowconfigure(4, weight=0, minsize=0)
            self._log_toggle_btn.configure(text="Logs ▼")

    # ── Settings & dialogs ────────────────────────────────────────────────

    def _open_settings(self) -> None:
        SettingsDialog(self)

    def _show_error_dialog(self, message: str) -> None:
        is_permission_error = "Screen Recording" in message

        dialog = ctk.CTkToplevel(self)
        dialog.title("Permission Required" if is_permission_error else "Error")
        dialog.geometry("480x230" if is_permission_error else "480x200")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()
        ctk.CTkLabel(
            dialog, text=message,
            wraplength=440, justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(padx=20, pady=20, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        if is_permission_error:
            def _open_settings() -> None:
                import subprocess
                subprocess.Popen([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
                ])
                dialog.destroy()

            ctk.CTkButton(
                btn_frame, text="Open Settings",
                fg_color=("#4F46E5", "#4F46E5"),
                hover_color=("#3730A3", "#3730A3"),
                command=_open_settings,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_frame, text="OK", command=dialog.destroy).pack(side="left")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _on_close(self) -> None:
        settings.set("window_width", self.winfo_width())
        settings.set("window_height", self.winfo_height())
        if hasattr(self, "_app"):
            self._app.stop_transcription()
        self.destroy()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_transcript_file(text: str) -> tuple[str, str]:
    """Parse saved transcript into (original, translation) sections."""
    original = ""
    translation = ""
    current_section = None
    lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("=== Original ==="):
            if current_section == "translation":
                translation = "\n".join(lines).strip()
            current_section = "original"
            lines = []
        elif line.startswith("=== Translation ==="):
            if current_section == "original":
                original = "\n".join(lines).strip()
            current_section = "translation"
            lines = []
        else:
            lines.append(line)

    if current_section == "original":
        original = "\n".join(lines).strip()
    elif current_section == "translation":
        translation = "\n".join(lines).strip()

    return original, translation


def _set_window_icon(window: ctk.CTk) -> None:
    """Set the window icon from assets/icon.png if available."""
    try:
        icon_path = Path(__file__).parents[4] / "assets" / "icon.png"
        if not icon_path.exists():
            return
        from PIL import Image, ImageTk
        img = Image.open(icon_path).resize((64, 64))
        photo = ImageTk.PhotoImage(img)
        window.wm_iconphoto(True, photo)
        window._icon_ref = photo  # prevent GC
    except Exception:
        pass  # icon is cosmetic — never crash on this
