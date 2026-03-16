"""PyInstaller build script — run with: python scripts/build.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENTRY = ROOT / "src" / "bytebabel" / "main.py"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
ICON_MAC = ROOT / "assets" / "icon.icns"
ICON_WIN = ROOT / "assets" / "icon.ico"
ICON_LINUX = ROOT / "assets" / "icon.png"
SYSTEM_AUDIO_HELPER = ROOT / "helpers" / "system_audio_capture"

COMMON_ARGS = [
    str(ENTRY),
    "--name=ByteBabel",
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
    "--hidden-import=PIL",
    "--hidden-import=numpy",
    # Collect full packages (data files)
    "--collect-all=customtkinter",
    "--collect-all=soniox",
    # Add source path
    f"--paths={ROOT / 'src'}",
]


def build_macos() -> None:
    args = [
        *COMMON_ARGS,
        "--windowed",
        "--onedir",
    ]
    if ICON_MAC.exists():
        args.append(f"--icon={ICON_MAC}")
    if SYSTEM_AUDIO_HELPER.exists():
        args.append(f"--add-data={SYSTEM_AUDIO_HELPER}:helpers/")
    icon_png = ROOT / "assets" / "icon.png"
    if icon_png.exists():
        args.append(f"--add-data={icon_png}:assets/")
    _run(args)
    _patch_macos_plist()


def build_linux() -> None:
    args = [*COMMON_ARGS, "--onedir"]
    if ICON_LINUX.exists():
        args.append(f"--icon={ICON_LINUX}")
    _run(args)
    _build_appimage()


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

    app_bundle = DIST / "ByteBabel.app"
    plist_path = app_bundle / "Contents" / "Info.plist"
    if not plist_path.exists():
        return
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)
    plist["NSMicrophoneUsageDescription"] = (
        "ByteBabel needs microphone access to transcribe your speech in real time."
    )
    plist["NSAppleEventsUsageDescription"] = (
        "ByteBabel needs accessibility access for system audio capture."
    )
    plist["CFBundleDisplayName"] = "ByteBabel"
    plist["CFBundleIdentifier"] = "com.bytebabel.app"
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
    print(f"Patched {plist_path}")


def _build_appimage() -> None:
    """Package the PyInstaller onedir output into an AppImage."""
    import os
    import shutil
    import stat

    app_dir = BUILD / "ByteBabel.AppDir"
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True)

    # Copy PyInstaller onedir output into AppDir/ByteBabel/
    onedir = DIST / "ByteBabel"
    if not onedir.exists():
        print("WARNING: PyInstaller onedir output not found, skipping AppImage.")
        return
    shutil.copytree(onedir, app_dir / "ByteBabel")

    # AppRun — entry point executed by the AppImage runtime
    apprun = app_dir / "AppRun"
    apprun.write_text(
        "#!/bin/bash\n"
        'SELF=$(readlink -f "$0")\n'
        "HERE=${SELF%/*}\n"
        'exec "$HERE/ByteBabel/ByteBabel" "$@"\n'
    )
    apprun.chmod(apprun.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # .desktop file (AppImage spec requires it at AppDir root)
    desktop = app_dir / "ByteBabel.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Name=ByteBabel\n"
        "Exec=ByteBabel\n"
        "Icon=ByteBabel\n"
        "Type=Application\n"
        "Categories=Utility;Audio;\n"
    )

    # Icon at AppDir root (without extension — appimagetool convention)
    if ICON_LINUX.exists():
        shutil.copy(ICON_LINUX, app_dir / "ByteBabel.png")

    # Run appimagetool
    appimagetool = _find_appimagetool()
    if appimagetool is None:
        print(
            "WARNING: appimagetool not found — skipping AppImage packaging.\n"
            "Install it from: https://github.com/AppImage/AppImageKit/releases\n"
            f"Standalone binary is available at: {DIST / 'ByteBabel'}"
        )
        return

    output = DIST / "ByteBabel.AppImage"
    env = {**os.environ, "ARCH": "x86_64"}
    subprocess.run([appimagetool, str(app_dir), str(output)], check=True, env=env)
    output.chmod(output.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Created {output}")


def _find_appimagetool() -> str | None:
    """Return path to appimagetool if available, else None."""
    import shutil as sh

    # 1. In PATH
    found = sh.which("appimagetool")
    if found:
        return found
    # 2. Next to this build script
    local = Path(__file__).parent / "appimagetool"
    if local.exists():
        return str(local)
    return None


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
