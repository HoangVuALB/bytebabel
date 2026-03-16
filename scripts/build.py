"""PyInstaller build script — run with: python scripts/build.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRY = ROOT / "src" / "transcript_app" / "main.py"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
ICON_MAC = ROOT / "assets" / "icon.icns"
ICON_WIN = ROOT / "assets" / "icon.ico"
ICON_LINUX = ROOT / "assets" / "icon.png"

COMMON_ARGS = [
    str(ENTRY),
    "--name=LiveTranscript",
    f"--distpath={DIST}",
    f"--workpath={BUILD}",
    "--noconfirm",
    "--clean",
    # Hidden imports
    "--hidden-import=customtkinter",
    "--hidden-import=soniox",
    "--hidden-import=sounddevice",
    "--hidden-import=_sounddevice_data",
    "--hidden-import=websockets",
    "--hidden-import=keyring.backends",
    # Collect full packages (data files)
    "--collect-all=customtkinter",
    "--collect-all=soniox",
]


def build_macos() -> None:
    args = [
        *COMMON_ARGS,
        "--windowed",
        "--onedir",
        "--target-arch=universal2",
    ]
    if ICON_MAC.exists():
        args.append(f"--icon={ICON_MAC}")
    # macOS: add NSMicrophoneUsageDescription to Info.plist via post-processing
    _run(args)
    _patch_macos_plist()


def build_linux() -> None:
    args = [*COMMON_ARGS, "--onefile"]
    if ICON_LINUX.exists():
        args.append(f"--icon={ICON_LINUX}")
    _run(args)
    _write_desktop_file()


def build_windows() -> None:
    args = [
        *COMMON_ARGS,
        "--windowed",
        "--onedir",
    ]
    if ICON_WIN.exists():
        args.append(f"--icon={ICON_WIN}")
    _run(args)


def _run(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", *args]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _patch_macos_plist() -> None:
    """Inject microphone usage description into the .app bundle."""
    import plistlib

    app_bundle = DIST / "LiveTranscript.app"
    plist_path = app_bundle / "Contents" / "Info.plist"
    if not plist_path.exists():
        return
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)
    plist["NSMicrophoneUsageDescription"] = (
        "Live Transcript needs microphone access to transcribe your speech in real time."
    )
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
    print(f"Patched {plist_path}")


def _write_desktop_file() -> None:
    desktop = DIST / "LiveTranscript.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Name=Live Transcript\n"
        "Exec=./LiveTranscript\n"
        "Icon=icon\n"
        "Type=Application\n"
        "Categories=Utility;Audio;\n"
    )
    print(f"Created {desktop}")


if __name__ == "__main__":
    platform = sys.platform
    print(f"Building for platform: {platform}")
    if platform == "darwin":
        build_macos()
    elif platform == "win32":
        build_windows()
    else:
        build_linux()
    print("Build complete! Output in:", DIST)
