#!/usr/bin/env python3
"""
Kinder Type installer — cross-platform (Linux, macOS, Windows).

Sets up a local virtual environment, installs Python dependencies, downloads
the TTS voice model, and generates the game's sound effects/music. Safe to
re-run: steps that are already done are skipped.

Run with:
    python3 install.py      (Linux / macOS)
    python install.py       (Windows)
"""

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_DIR = SCRIPT_DIR / ".venv"
IS_WINDOWS = os.name == "nt"

VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
VENV_PIP = VENV_DIR / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")


def run(cmd, **kwargs):
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def step(title):
    print(f"-- {title} --")


def create_desktop_launcher():
    """Write a .desktop file so the game shows up in the app menu and can be
    pinned to the taskbar (Linux only — Windows/macOS have their own,
    different shortcut mechanisms this doesn't attempt to cover).

    Always rewritten with the current SCRIPT_DIR, so it stays correct even
    if the repo gets moved. WM_CLASS is "game.py" — confirmed via xprop
    against a running instance, not guessed; it's however pygame/SDL names
    the window by default when run as `python game.py`, not tied to any
    one machine's path.
    """
    apps_dir = Path.home() / ".local/share/applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = apps_dir / "kinder-type.desktop"
    desktop_file.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Kinder Type\n"
        "Comment=Asteroids-style typing game for beginners\n"
        f"Exec={SCRIPT_DIR / 'run.sh'}\n"
        f"Icon={SCRIPT_DIR / 'images' / 'logo.png'}\n"
        "Terminal=false\n"
        "Categories=Game;Education;\n"
        "StartupWMClass=game.py\n"
    )
    desktop_file.chmod(0o755)
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # not on this system; the launcher still works, just may take
              # a moment to show up in the app menu


def bootstrap_pip():
    """Install pip into the venv via PyPA's get-pip.py, bypassing ensurepip.

    Some systems (commonly Debian/Ubuntu) ship a python3-venv package that
    creates a working venv *shell* but can't bootstrap pip into it without
    a separate OS package — normally fixed with `sudo apt install
    python3-venv`, but that needs root, which isn't guaranteed. get-pip.py
    needs only network access, which install.py already requires anyway.
    """
    get_pip = SCRIPT_DIR / ".get-pip.py"
    urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", str(get_pip))
    try:
        run([str(VENV_PYTHON), str(get_pip)])
    finally:
        get_pip.unlink(missing_ok=True)


def main():
    os.chdir(SCRIPT_DIR)
    print("== Kinder Type installer ==")

    if sys.version_info < (3, 9):
        print("Python 3.9+ is required.", file=sys.stderr)
        sys.exit(1)

    step("Setting up virtual environment (.venv)")
    if not VENV_PYTHON.exists():
        try:
            run([sys.executable, "-m", "venv", str(VENV_DIR)])
        except subprocess.CalledProcessError:
            if not VENV_PYTHON.exists():
                print("Failed to create the virtual environment.", file=sys.stderr)
                if sys.platform.startswith("linux"):
                    print(
                        "On Debian/Ubuntu you likely need: sudo apt install python3-venv",
                        file=sys.stderr,
                    )
                elif sys.platform == "darwin":
                    print(
                        "Try installing Python from https://python.org or with: brew install python",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "Make sure Python was installed with the 'venv' / 'pip' components enabled.",
                        file=sys.stderr,
                    )
                sys.exit(1)
            # The venv shell (python binary) exists; only its own pip
            # bootstrap failed. Handled below regardless of this branch.
    else:
        print("   .venv already exists, skipping.")

    if not VENV_PIP.exists():
        step("Bootstrapping pip inside the venv (no system ensurepip available)")
        bootstrap_pip()

    step("Installing Python dependencies")
    run([str(VENV_PIP), "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
    requirements_file = SCRIPT_DIR / "requirements.txt"
    try:
        run([str(VENV_PIP), "install", "-r", str(requirements_file)])
    except subprocess.CalledProcessError:
        print("   pygame-ce install failed, falling back to pygame...")
        other_reqs = [
            line.strip() for line in requirements_file.read_text().splitlines()
            if line.strip() and not line.startswith("pygame-ce")
        ]
        run([str(VENV_PIP), "install", "pygame"] + other_reqs)

    step("Downloading voice model (en_US-amy-medium, ~63MB, one-time)")
    voices_dir = SCRIPT_DIR / "voices"
    voices_dir.mkdir(exist_ok=True)
    voice_file = voices_dir / "en_US-amy-medium.onnx"
    if not voice_file.exists():
        run([
            str(VENV_PYTHON), "-m", "piper.download_voices",
            "--download-dir", str(voices_dir), "en_US-amy-medium",
        ])
    else:
        print("   voice model already present, skipping.")

    step("Generating game audio (sound effects + music)")
    sounds_dir = SCRIPT_DIR / "sounds"
    needed = ["music_loop.wav", "laser.wav", "fail.wav"]
    if not all((sounds_dir / f).exists() for f in needed):
        run([str(VENV_PYTHON), str(SCRIPT_DIR / "generate_audio.py")])
    else:
        print("   audio already generated, skipping.")

    if sys.platform.startswith("linux"):
        step("Adding an app-menu launcher")
        create_desktop_launcher()
        print("   Find \"Kinder Type\" in your app menu — most desktops let you")
        print("   right-click it there to pin it to the taskbar.")

    print()
    print("Install complete! Run the game with:")
    print("    run.bat" if IS_WINDOWS else "    ./run.sh")


if __name__ == "__main__":
    main()
