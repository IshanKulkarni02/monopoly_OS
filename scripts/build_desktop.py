#!/usr/bin/env python3
"""Builds the monopoly_OS desktop host launcher for the current OS.

Produces:
  - macOS:   dist/monopoly_OS.app, wrapped into dist/monopoly_OS.dmg
  - Windows: dist/monopoly_OS.exe (standalone, no installer wrapper needed)
  - Linux:   dist/monopoly_OS (standalone binary; no installer format targeted)

Same script on every platform — PyInstaller can't cross-compile, so building
a Windows .exe still has to run on Windows (see .github/workflows/build-desktop.yml
for the actual macOS+Windows CI matrix; this script is what that workflow, and a
developer's own machine, both run).

Usage: python scripts/build_desktop.py
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
DIST = ROOT / "dist"
APP_NAME = "monopoly_OS"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (in {cwd})")
    subprocess.run(cmd, cwd=cwd, check=True)


def build_frontend() -> None:
    print("\n=== Building frontend ===")
    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm not found on PATH — install Node.js first")
    if not (FRONTEND / "node_modules").exists():
        run([npm, "install"], cwd=FRONTEND)
    run([npm, "run", "build"], cwd=FRONTEND)
    if not (FRONTEND / "dist" / "index.html").exists():
        sys.exit("frontend build did not produce dist/index.html")


def build_backend_bundle() -> None:
    print("\n=== Bundling backend + frontend with PyInstaller ===")
    sep = ";" if platform.system() == "Windows" else ":"
    add_data = f"{FRONTEND / 'dist'}{sep}frontend_dist"

    uv = shutil.which("uv")
    if uv is None:
        sys.exit("uv not found on PATH")
    run([uv, "sync", "--dev"], cwd=BACKEND)

    # macOS: a .app bundle is already a directory container, so PyInstaller's
    # --onefile (a self-extracting single binary) is redundant on top of it —
    # PyInstaller itself deprecates that combination in favor of --onedir,
    # which also starts faster (no self-extraction on every launch).
    # Windows/Linux have no such bundle format, so a single portable
    # executable stays the simpler thing to hand someone.
    mode = "--onedir" if platform.system() == "Darwin" else "--onefile"

    run(
        [
            uv, "run", "pyinstaller",
            "--name", APP_NAME,
            mode,
            "--windowed",
            "--noconfirm",
            "--distpath", str(DIST),
            "--workpath", str(ROOT / "build"),
            "--specpath", str(ROOT / "build"),
            "--add-data", add_data,
            str(BACKEND / "launcher.py"),
        ],
        cwd=BACKEND,
    )


def wrap_macos_dmg() -> None:
    app_path = DIST / f"{APP_NAME}.app"
    if not app_path.exists():
        sys.exit(f"expected {app_path} after PyInstaller build, not found")

    print("\n=== Wrapping .app into a .dmg ===")
    dmg_path = DIST / f"{APP_NAME}.dmg"
    dmg_path.unlink(missing_ok=True)
    staging = DIST / "dmg_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    shutil.copytree(app_path, staging / f"{APP_NAME}.app")
    (staging / "Applications").symlink_to("/Applications")

    run(
        [
            "hdiutil", "create",
            "-volname", APP_NAME,
            "-srcfolder", str(staging),
            "-ov", "-format", "UDZO",
            str(dmg_path),
        ],
        cwd=ROOT,
    )
    shutil.rmtree(staging)
    print(f"\nBuilt {dmg_path}")


def main() -> None:
    DIST.mkdir(exist_ok=True)
    build_frontend()
    build_backend_bundle()

    system = platform.system()
    if system == "Darwin":
        wrap_macos_dmg()
    elif system == "Windows":
        exe_path = DIST / f"{APP_NAME}.exe"
        print(f"\nBuilt {exe_path}" if exe_path.exists() else f"\nExpected {exe_path}, not found")
    else:
        bin_path = DIST / APP_NAME
        print(f"\nBuilt {bin_path}" if bin_path.exists() else f"\nExpected {bin_path}, not found")


if __name__ == "__main__":
    main()
