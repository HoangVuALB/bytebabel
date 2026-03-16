#!/usr/bin/env python3
"""
Generate ByteBabel app icon.

Outputs:
  assets/icon.png   (1024×1024 master)
  assets/icon.icns  (macOS, via iconutil)
  assets/icon.ico   (Windows, multi-size)

Usage:
  python scripts/make_icon.py
"""

import math
import struct
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Install Pillow first:  pip install Pillow")
    sys.exit(1)

ROOT   = Path(__file__).parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


# ── Design constants ──────────────────────────────────────────────────────────
SIZE       = 1024
BG_COLOR   = (15, 17, 28)        # #0F1117 near-black
RECT_COLOR = (79, 70, 229)       # #4F46E5 indigo
WAVE_COLOR = (255, 255, 255, 230)  # white, slightly translucent
RADIUS     = 230                  # rounded corner radius


def make_icon(size: int = SIZE) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rect
    pad  = int(size * 0.06)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=RADIUS * size // SIZE,
        fill=RECT_COLOR,
    )

    # Waveform bars  — 5 bars with varying heights
    bar_heights = [0.22, 0.46, 0.64, 0.46, 0.22]
    n_bars  = len(bar_heights)
    bar_w   = int(size * 0.09)
    gap     = int(size * 0.04)
    total_w = n_bars * bar_w + (n_bars - 1) * gap
    x_start = (size - total_w) // 2
    cx      = size // 2

    for i, h_ratio in enumerate(bar_heights):
        bar_h = int(size * h_ratio)
        x0 = x_start + i * (bar_w + gap)
        x1 = x0 + bar_w
        y0 = cx - bar_h // 2
        y1 = cx + bar_h // 2
        r  = bar_w // 2
        draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=WAVE_COLOR)

    return img


def save_icns(png_path: Path, icns_path: Path) -> None:
    """Use macOS iconutil to produce .icns from a set of PNGs."""
    iconset = icns_path.with_suffix(".iconset")
    iconset.mkdir(exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    img = Image.open(png_path)
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        resized.save(iconset / f"icon_{s}x{s}.png")
        if s <= 512:
            resized2 = img.resize((s * 2, s * 2), Image.LANCZOS)
            resized2.save(iconset / f"icon_{s}x{s}@2x.png")

    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"iconutil failed: {result.stderr.decode()}")
    else:
        print(f"  ✓ {icns_path}")

    # clean up iconset folder
    import shutil
    shutil.rmtree(iconset, ignore_errors=True)


def save_ico(png_path: Path, ico_path: Path) -> None:
    """Save multi-size .ico via Pillow."""
    img = Image.open(png_path)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = [img.resize(s, Image.LANCZOS).convert("RGBA") for s in sizes]
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        append_images=frames[1:],
    )
    print(f"  ✓ {ico_path}")


def main() -> None:
    print("Generating ByteBabel icon…")

    png_path = ASSETS / "icon.png"
    icon = make_icon()
    icon.save(png_path, "PNG")
    print(f"  ✓ {png_path}")

    # macOS .icns
    if sys.platform == "darwin":
        save_icns(png_path, ASSETS / "icon.icns")
    else:
        print("  (skip .icns — macOS only)")

    # Windows .ico
    save_ico(png_path, ASSETS / "icon.ico")

    print("Done.")


if __name__ == "__main__":
    main()
