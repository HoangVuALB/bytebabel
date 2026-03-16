"""Design tokens — single source of truth for the entire UI.

Every colour is a (light, dark) tuple consumed directly by customtkinter.
"""

from __future__ import annotations

# ── Surface & Background ──────────────────────────────────────────────────────
BG_ROOT = ("#F2F2F7", "#0C0C14")  # app window
BG_SURFACE = ("#FFFFFF", "#161620")  # cards, panels
BG_ELEVATED = ("#F8F8FC", "#1C1C2A")  # toolbar, header rows
BG_INSET = ("#F0F0F5", "#111119")  # input fields, sidebar
BG_OVERLAY = ("#EEEEF3", "#0A0A10")  # status bar, log header

# ── Borders ───────────────────────────────────────────────────────────────────
BORDER_SUBTLE = ("#E5E5EA", "#1F1F2E")  # card outlines
BORDER_MUTED = ("#D1D1D6", "#2A2A3C")  # dividers
BORDER_FOCUS = ("#6366F1", "#818CF8")  # focused input ring

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY = ("#1C1C1E", "#E5E5EA")  # body text
TEXT_SECONDARY = ("#6E6E73", "#8E8E93")  # muted labels
TEXT_TERTIARY = ("#AEAEB2", "#48484A")  # placeholders, hints
TEXT_INVERSE = ("#FFFFFF", "#FFFFFF")  # text on accent buttons

# ── Accent ────────────────────────────────────────────────────────────────────
ACCENT = ("#6366F1", "#818CF8")  # indigo — primary action
ACCENT_HOVER = ("#4F46E5", "#6366F1")  # darker on hover
ACCENT_SUBTLE = ("#EEF2FF", "#1E1B4B")  # chip / badge bg

# ── Semantic ──────────────────────────────────────────────────────────────────
SUCCESS = ("#16A34A", "#4ADE80")  # green — recording / ok
SUCCESS_BG = ("#F0FDF4", "#052E16")
DANGER = ("#DC2626", "#F87171")  # red — stop / error
DANGER_BG = ("#FEF2F2", "#450A0A")
WARNING = ("#D97706", "#FBBF24")  # amber
INFO = ("#2563EB", "#60A5FA")  # blue

# ── Transcript Colours ────────────────────────────────────────────────────────
ORIG_TEXT = ("#1E293B", "#CBD5E1")  # original — slate
TRANS_TEXT = ("#059669", "#34D399")  # translation — emerald
LIVE_ORIG = ("#64748B", "#94A3B8")  # live orig — lighter slate
LIVE_TRANS = ("#6EE7B7", "#6EE7B7")  # live trans — emerald/light

# ── Scrollbar ─────────────────────────────────────────────────────────────────
SCROLLBAR = ("#C7C7CC", "#2C2C3A")
SCROLLBAR_HOV = ("#A1A1AA", "#3F3F50")

# ── Radius & Spacing (px) ────────────────────────────────────────────────────
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24

# ── Typography helpers ────────────────────────────────────────────────────────
FONT_FAMILY = "Helvetica Neue"
FONT_MONO = "Menlo"
