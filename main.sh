#!/usr/bin/env bash
# ProtonWG launcher — runs the Python TUI
cd "$(dirname "$0")" || exit 1
exec uv run protonwg.py "$@"
