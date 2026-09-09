#!/usr/bin/env bash
# Launches Kinder Type (Linux / macOS). Runs the installer automatically on
# first use if the virtual environment hasn't been set up yet.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d .venv ]; then
    echo "No .venv found — running the installer first..."
    python3 install.py
fi

exec .venv/bin/python game.py
