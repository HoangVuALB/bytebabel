"""TranscriptView — scrollable sentence bubble cards with original + translation."""

from __future__ import annotations

import re

import customtkinter as ctk

# ── Palette ───────────────────────────────────────────────────────────────────
_ORIG_COLOR  = "#5B9BD5"   # muted blue — original text
_TRANS_COLOR = "#56C26E"   # fresh green — translation
_PANEL_BG    = ("#F0F0F4", "#0E0E16")
_CARD_BG     = ("#FFFFFF",  "#1A1A24")
_CARD_BDR    = ("#E2E2E8",  "#2A2A38")
_DIV_COLOR   = ("#D8D8E0",  "#252530")
_LIVE_BG     = ("#F6F6FA",  "#111120")
_LIVE_TEXT   = ("#AAAAAA",  "#55556A")
_PLACEHOLDER = ("#BBBBBB",  "#444455")


class TranscriptView(ctk.CTkFrame):
    """
    Single-column scrollable panel.
    Each finalized sentence is shown as a card:
      original text (blue)
      ─── divider ───
      translation (green)   ← only if translation is present
    """

    def __init__(self, master: ctk.CTkBaseClass, **kwargs: object) -> None:
        kwargs.setdefault("fg_color", _PANEL_BG)
        super().__init__(master, corner_radius=12, **kwargs)

        self._sentences: list[str]      = []
        self._translations: list[str]   = []
        self._cards: list[ctk.CTkFrame] = []
        self._live_frame: ctk.CTkFrame | None = None
        self._live_orig_lbl:  ctk.CTkLabel | None = None
        self._live_trans_lbl: ctk.CTkLabel | None = None
        self._placeholder: ctk.CTkLabel | None = None
        self._is_live_mode = True

        self._build_ui()
        self.show_placeholder()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("gray70", "#2A2A3A"),
            scrollbar_button_hover_color=("gray55", "#3A3A52"),
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)
        self._scroll.bind("<Configure>", self._on_resize)

    # ── Public API ────────────────────────────────────────────────────────

    def show_placeholder(self) -> None:
        """Display empty-state hint."""
        self._clear_cards()
        if self._placeholder is None:
            self._placeholder = ctk.CTkLabel(
                self._scroll,
                text="Press ▶ Start to begin recording",
                text_color=_PLACEHOLDER,
                font=ctk.CTkFont(family="Helvetica Neue", size=15, slant="italic"),
            )
        self._placeholder.grid(row=0, column=0, pady=60)

    def set_live_mode(self) -> None:
        """Switch to live capture mode and clear all cards."""
        self._is_live_mode = True
        self._clear_cards()
        if self._placeholder:
            self._placeholder.grid_forget()

    def show_file(self, original: str, translation: str) -> None:
        """Display a saved transcript file (read-only)."""
        self._is_live_mode = False
        self._clear_cards()
        if self._placeholder:
            self._placeholder.grid_forget()

        orig_sents  = _split_sentences(original)
        trans_sents = _split_sentences(translation)
        wrap = self._wrap_width()
        for i, orig in enumerate(orig_sents):
            trans = trans_sents[i] if i < len(trans_sents) else ""
            self._sentences.append(orig)
            self._translations.append(trans)
            self._cards.append(self._make_card(len(self._cards), orig, trans, wrap))
        self.after_idle(self._scroll_bottom)

    def update_transcript(
        self,
        final_text: str,
        non_final_text: str,
        translated_final_text: str = "",
        translated_non_final_text: str = "",
    ) -> None:
        """Update live transcript — reconcile cards, show live preview."""
        if not self._is_live_mode:
            self.set_live_mode()
        if self._placeholder:
            self._placeholder.grid_forget()

        new_sents  = _split_sentences(final_text)
        new_trans  = _split_sentences(translated_final_text)
        wrap = self._wrap_width()

        for i, sent in enumerate(new_sents):
            trans = new_trans[i] if i < len(new_trans) else ""
            if i < len(self._sentences):
                if self._sentences[i] != sent or self._translations[i] != trans:
                    self._sentences[i]    = sent
                    self._translations[i] = trans
                    self._update_card(self._cards[i], sent, trans, wrap)
            else:
                self._sentences.append(sent)
                self._translations.append(trans)
                self._cards.append(self._make_card(len(self._cards), sent, trans, wrap))

        # Live preview card
        live_orig  = non_final_text.strip()
        live_trans = translated_non_final_text.strip()
        if live_orig or live_trans:
            self._ensure_live()
            row = len(self._cards)
            if self._live_orig_lbl:
                self._live_orig_lbl.configure(text=live_orig or "", wraplength=wrap)
            if self._live_trans_lbl:
                self._live_trans_lbl.configure(text=live_trans or "", wraplength=wrap)
            self._live_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 10))
        elif self._live_frame:
            self._live_frame.grid_forget()

        self.after_idle(self._scroll_bottom)

    def clear(self) -> None:
        self._clear_cards()
        self.show_placeholder()

    # ── Card construction ─────────────────────────────────────────────────

    def _make_card(self, idx: int, orig: str, trans: str, wrap: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            self._scroll,
            fg_color=_CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=_CARD_BDR,
        )
        frame.grid(row=idx, column=0, sticky="ew", padx=10, pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text=orig,
            anchor="w", justify="left",
            wraplength=wrap,
            text_color=_ORIG_COLOR,
            font=ctk.CTkFont(family="Helvetica Neue", size=15),
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))

        if trans:
            ctk.CTkFrame(
                frame, height=1,
                fg_color=_DIV_COLOR,
                corner_radius=0,
            ).grid(row=1, column=0, sticky="ew", padx=14, pady=0)
            ctk.CTkLabel(
                frame, text=trans,
                anchor="w", justify="left",
                wraplength=wrap,
                text_color=_TRANS_COLOR,
                font=ctk.CTkFont(family="Helvetica Neue", size=14),
            ).grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 10))
        else:
            # Adjust bottom padding on original label when no translation
            for widget in frame.grid_slaves(row=0):
                widget.grid_configure(pady=(10, 10))

        return frame

    def _update_card(self, frame: ctk.CTkFrame, orig: str, trans: str, wrap: int) -> None:
        """Destroy and recreate card content in-place (simpler than tracking sub-widgets)."""
        idx = frame.grid_info()["row"]
        frame.destroy()
        new_frame = self._make_card(idx, orig, trans, wrap)
        self._cards[idx] = new_frame

    def _ensure_live(self) -> None:
        if self._live_frame is not None:
            return
        self._live_frame = ctk.CTkFrame(
            self._scroll,
            fg_color=_LIVE_BG,
            corner_radius=10,
            border_width=1,
            border_color=_CARD_BDR,
        )
        self._live_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._live_frame, text="▸",
            text_color=_ORIG_COLOR,
            font=ctk.CTkFont(size=12), width=16,
        ).grid(row=0, column=0, sticky="nw", padx=(12, 2), pady=10)

        self._live_orig_lbl = ctk.CTkLabel(
            self._live_frame, text="",
            anchor="w", justify="left",
            wraplength=600,
            text_color=_LIVE_TEXT,
            font=ctk.CTkFont(family="Helvetica Neue", size=14, slant="italic"),
        )
        self._live_orig_lbl.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(10, 4))

        self._live_trans_lbl = ctk.CTkLabel(
            self._live_frame, text="",
            anchor="w", justify="left",
            wraplength=600,
            text_color=_LIVE_TEXT,
            font=ctk.CTkFont(family="Helvetica Neue", size=13, slant="italic"),
        )
        self._live_trans_lbl.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=(0, 10))

    # ── Internal helpers ──────────────────────────────────────────────────

    def _clear_cards(self) -> None:
        self._sentences.clear()
        self._translations.clear()
        for frame in self._cards:
            frame.destroy()
        self._cards.clear()
        if self._live_frame:
            self._live_frame.destroy()
            self._live_frame = None
            self._live_orig_lbl  = None
            self._live_trans_lbl = None

    def _scroll_bottom(self) -> None:
        try:
            self._scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _wrap_width(self) -> int:
        w = self._scroll.winfo_width()
        return max(160, w - 80) if w > 140 else 500

    def _on_resize(self, _: object) -> None:
        wrap = self._wrap_width()
        for frame in self._cards:
            for widget in frame.winfo_children():
                if isinstance(widget, ctk.CTkLabel):
                    widget.configure(wraplength=wrap)
        if self._live_orig_lbl:
            self._live_orig_lbl.configure(wraplength=wrap)
        if self._live_trans_lbl:
            self._live_trans_lbl.configure(wraplength=wrap)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """Split cumulative transcript text into individual sentences."""
    if not text or not text.strip():
        return []
    parts = re.split(r"(?<=[.!?…。！？])\s*", text.strip())
    return [p.strip() for p in parts if p.strip()]
