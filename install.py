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
    else:
        print("   .venv already exists, skipping.")

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

    print()
    print("Install complete! Run the game with:")
    print("    run.bat" if IS_WINDOWS else "    ./run.sh")


if __name__ == "__main__":
    main()
