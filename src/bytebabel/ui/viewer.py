"""TranscriptView — vertical layout: completed text on top, live text below."""

from __future__ import annotations

import customtkinter as ctk

from . import theme as T


class TranscriptView(ctk.CTkFrame):
    """Vertical transcript viewer with finalized pane + live pane."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs: object) -> None:
        kwargs.setdefault("fg_color", T.BG_ROOT)
        super().__init__(master, corner_radius=0, **kwargs)

        self._is_live_mode = True
        self._last_final_orig = ""
        self._last_final_trans = ""
        self._last_live_orig = ""
        self._last_live_trans = ""
        self._segments_cache: list[tuple[str, str]] = []

        self._build_ui()
        self.show_placeholder()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=4)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        # ── Completed pane ────────────────────────────────────────────────
        completed = ctk.CTkFrame(
            self,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_MD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
        )
        completed.grid(
            row=0, column=0, sticky="nsew", padx=T.PAD_SM, pady=(T.PAD_SM, 3)
        )
        completed.grid_rowconfigure(1, weight=1)
        completed.grid_columnconfigure(0, weight=1)
        self._completed_pane = completed

        # Header
        hdr = ctk.CTkFrame(
            completed, fg_color=T.BG_ELEVATED, corner_radius=T.RADIUS_SM, height=32
        )
        hdr.grid(row=0, column=0, sticky="ew", padx=T.PAD_SM, pady=(T.PAD_SM, 0))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)
        hdr.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="TRANSCRIPT",
            height=28,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            text_color=T.TEXT_SECONDARY,
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_MD)

        self._copy_trans_btn = ctk.CTkButton(
            hdr,
            text="Copy Translation",
            width=110,
            height=24,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            fg_color="transparent",
            hover_color=T.BORDER_MUTED,
            text_color=T.TEXT_TERTIARY,
            command=self._copy_translation,
        )
        self._copy_trans_btn.grid(row=0, column=1, padx=(0, 2))

        self._copy_orig_btn = ctk.CTkButton(
            hdr,
            text="Copy Original",
            width=100,
            height=24,
            corner_radius=T.RADIUS_SM,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11),
            fg_color="transparent",
            hover_color=T.BORDER_MUTED,
            text_color=T.TEXT_TERTIARY,
            command=self._copy_transcript,
        )
        self._copy_orig_btn.grid(row=0, column=2, padx=(0, T.PAD_XS))

        self._completed_text = ctk.CTkTextbox(
            completed,
            fg_color="transparent",
            wrap="word",
            activate_scrollbars=True,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=15),
            text_color=T.ORIG_TEXT,
            scrollbar_button_color=T.SCROLLBAR,
            scrollbar_button_hover_color=T.SCROLLBAR_HOV,
        )
        self._completed_text.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_SM, pady=(T.PAD_XS, T.PAD_SM)
        )
        self._completed_text.configure(state="disabled")

        # ── Divider ──────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=T.BORDER_SUBTLE, corner_radius=0).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=T.PAD_LG,
        )

        # ── Live pane ─────────────────────────────────────────────────────
        live = ctk.CTkFrame(
            self,
            fg_color=T.BG_INSET,
            corner_radius=T.RADIUS_MD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
        )
        live.grid(row=2, column=0, sticky="nsew", padx=T.PAD_SM, pady=(3, T.PAD_SM))
        live.grid_rowconfigure(1, weight=1)
        live.grid_columnconfigure(0, weight=1)
        self._live_pane = live

        self._live_dot = ctk.CTkLabel(
            live,
            text="● LIVE",
            height=20,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=11, weight="bold"),
            text_color=T.DANGER,
            fg_color="transparent",
        )
        self._live_dot.grid(
            row=0, column=0, sticky="w", padx=T.PAD_MD, pady=(T.PAD_SM, 0)
        )

        self._live_text = ctk.CTkTextbox(
            live,
            fg_color="transparent",
            wrap="word",
            activate_scrollbars=False,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=15),
            text_color=T.LIVE_ORIG,
        )
        self._live_text.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_SM, pady=(0, T.PAD_SM)
        )
        self._live_text.configure(state="disabled")

        # ── Placeholder ──────────────────────────────────────────────────
        self._placeholder = ctk.CTkLabel(
            self,
            text="Press Start to begin transcribing",
            text_color=T.TEXT_TERTIARY,
            font=ctk.CTkFont(family=T.FONT_FAMILY, size=15, slant="italic"),
        )

    # ── Public API ────────────────────────────────────────────────────────

    def show_placeholder(self) -> None:
        self._clear_all()
        self._completed_pane.grid_remove()
        self._live_pane.grid_remove()
        self._placeholder.place(relx=0.5, rely=0.45, anchor="center")

    def set_live_mode(self) -> None:
        self._is_live_mode = True
        self._clear_all()
        self._placeholder.place_forget()
        self.grid_rowconfigure(0, weight=4)
        self.grid_rowconfigure(2, weight=1)
        self._completed_pane.grid(
            row=0, column=0, sticky="nsew", padx=T.PAD_SM, pady=(T.PAD_SM, 3)
        )
        self._live_pane.grid(
            row=2, column=0, sticky="nsew", padx=T.PAD_SM, pady=(3, T.PAD_SM)
        )

    def show_file(self, original: str, translation: str) -> None:
        """Show a saved transcript file (no live pane needed)."""
        self._is_live_mode = False
        self._placeholder.place_forget()
        self._completed_pane.grid(
            row=0, column=0, sticky="nsew", padx=T.PAD_SM, pady=(T.PAD_SM, 3)
        )
        self._live_pane.grid_remove()
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=0)

        content = original.strip()
        if translation.strip():
            content += f"\n\n── Translation ──\n{translation.strip()}"
        self._set_text(self._completed_text, content)

    def update_transcript(
        self,
        final_text: str,
        non_final_text: str,
        translated_final_text: str = "",
        translated_non_final_text: str = "",
        segments: list[tuple[str, str]] | None = None,
    ) -> None:
        if not self._is_live_mode:
            self.set_live_mode()

        self._placeholder.place_forget()

        # ── Completed pane: sentence-by-sentence pairing ──────────────────
        if segments:
            if segments != self._segments_cache:
                self._segments_cache = list(segments)
                self._last_final_orig = "\n".join(
                    s[0] for s in segments if s[0].strip()
                )
                self._last_final_trans = "\n".join(
                    s[1] for s in segments if s[1].strip()
                )
                self._render_segments(segments)
        else:
            # Fallback for no-translation or pre-segment state
            final_orig = final_text.strip()
            final_trans = translated_final_text.strip()
            completed = final_orig
            if final_trans:
                completed += f"\n\n── Translation ──\n{final_trans}"
            if completed != self._last_final_orig + self._last_final_trans:
                self._last_final_orig = final_orig
                self._last_final_trans = final_trans
                self._set_text(self._completed_text, completed, auto_scroll=True)

        # ── Live pane: current recognition ────────────────────────────────
        live_orig = non_final_text.strip()
        live_trans = translated_non_final_text.strip()
        live = live_orig
        if live_trans:
            live += f"\n{live_trans}"

        if live != self._last_live_orig + self._last_live_trans:
            self._last_live_orig = live_orig
            self._last_live_trans = live_trans
            self._set_text(self._live_text, live)

    def clear(self) -> None:
        self._clear_all()
        self.show_placeholder()

    # ── Segment rendering ──────────────────────────────────────

    def _render_segments(self, segments: list[tuple[str, str]]) -> None:
        """Render (orig, trans) pairs with color tags in the completed textbox."""
        tb = self._completed_text
        inner = tb._textbox  # underlying tk.Text widget

        mode = ctk.get_appearance_mode()
        idx = 0 if mode == "Light" else 1

        inner.tag_configure("orig", foreground=T.ORIG_TEXT[idx])
        inner.tag_configure(
            "trans",
            foreground=T.TRANS_TEXT[idx],
            font=(T.FONT_FAMILY, 13, "italic"),
        )

        tb.configure(state="normal")
        tb.delete("1.0", "end")

        for i, (orig, trans) in enumerate(segments):
            if i > 0:
                inner.insert("end", "\n")
            if orig.strip():
                inner.insert("end", orig.strip() + "\n", "orig")
            if trans.strip():
                inner.insert("end", trans.strip() + "\n", "trans")

        inner.see("end")
        tb.configure(state="disabled")

    # ── Copy to clipboard ─────────────────────────────────────────────────

    def _copy_transcript(self) -> None:
        text = self._last_final_orig
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._flash_btn(self._copy_orig_btn, "✓ Copied!")

    def _copy_translation(self) -> None:
        text = self._last_final_trans
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._flash_btn(self._copy_trans_btn, "✓ Copied!")

    def _flash_btn(self, btn: ctk.CTkButton, msg: str) -> None:
        original = btn.cget("text")
        btn.configure(text=msg)
        self.after(1200, lambda: btn.configure(text=original))

    # ── Text helpers ──────────────────────────────────────────────────────

    def _set_text(
        self, textbox: ctk.CTkTextbox, content: str, auto_scroll: bool = False
    ) -> None:
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        if content:
            textbox.insert("1.0", content)
        if auto_scroll:
            textbox.see("end")
        textbox.configure(state="disabled")

    def _clear_all(self) -> None:
        self._last_final_orig = ""
        self._last_final_trans = ""
        self._last_live_orig = ""
        self._last_live_trans = ""
        self._segments_cache = []
        self._set_text(self._completed_text, "")
        self._set_text(self._live_text, "")
