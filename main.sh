#!/usr/bin/env bash
# ProtonWG launcher — runs the Python TUI
exec python3 "$(cd "$(dirname "$0")" && pwd)/protonwg.py" "$@"
