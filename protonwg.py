#!/usr/bin/env python3
"""ProtonWG — WireGuard TUI manager for Arch Linux."""

from __future__ import annotations

import shutil
import subprocess
import sys


def _check_deps() -> None:
    errors: list[str] = []

    if sys.version_info < (3, 9):
        errors.append(f"Python 3.9+ required (got {sys.version.split()[0]})")

    try:
        import textual  # noqa: F401
    except ImportError:
        errors.append("textual not installed — run: uv sync (dev) or bash install.sh")

    if not shutil.which("wg-quick"):
        errors.append("wg-quick not found — run: sudo pacman -S wireguard-tools")

    if errors:
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        print("\nRun  bash install.sh  to fix these automatically.", file=sys.stderr)
        sys.exit(1)


def _sudo_auth() -> None:
    """Authenticate sudo before Textual takes over stdin."""
    result = subprocess.run(["sudo", "-n", "true"], capture_output=True)
    if result.returncode != 0:
        # Token expired or never set — prompt now, in normal terminal mode
        print("ProtonWG needs sudo for WireGuard operations.")
        auth = subprocess.run(["sudo", "-v"])
        if auth.returncode != 0:
            print("sudo authentication failed.", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    _check_deps()
    _sudo_auth()
    from tui.app import ProtonWGApp
    ProtonWGApp().run()


if __name__ == "__main__":
    import os
    # Resolve symlinks so direct execution finds tui/ and wg/ packages
    _here = os.path.dirname(os.path.realpath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    main()
