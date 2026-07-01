from __future__ import annotations

import shutil
import subprocess
from typing import Literal


def detect() -> Literal["openresolv", "systemd-resolved", "none"]:
    if shutil.which("resolvconf"):
        try:
            r = subprocess.run(
                ["resolvconf", "--version"],
                capture_output=True, text=True
            )
            if "openresolv" in r.stdout.lower() or "openresolv" in r.stderr.lower():
                return "openresolv"
        except Exception:
            pass
        # Check if systemd-resolved backs it
        try:
            r = subprocess.run(
                ["systemctl", "is-active", "systemd-resolved"],
                capture_output=True, text=True
            )
            if r.stdout.strip() == "active":
                return "systemd-resolved"
        except Exception:
            pass
        return "openresolv"
    return "none"


def install_hint() -> str:
    return "sudo pacman -S --needed openresolv"


def is_dns_error(stderr: str) -> bool:
    keywords = ["resolvconf", "resolve1", "DNS configuration", "systemd-resolved"]
    return any(k.lower() in stderr.lower() for k in keywords)
