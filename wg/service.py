from __future__ import annotations

import subprocess


def _unit(iface: str) -> str:
    return f"wg-quick@{iface}"


def is_enabled(iface: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "is-enabled", _unit(iface)],
            capture_output=True, text=True
        )
        return r.stdout.strip() == "enabled"
    except Exception:
        return False


def enable(iface: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["sudo", "-n", "systemctl", "enable", _unit(iface)],
            capture_output=True, text=True
        )
        return r.returncode == 0, r.stderr.strip()
    except Exception as e:
        return False, str(e)


def disable(iface: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["sudo", "-n", "systemctl", "disable", _unit(iface)],
            capture_output=True, text=True
        )
        return r.returncode == 0, r.stderr.strip()
    except Exception as e:
        return False, str(e)
