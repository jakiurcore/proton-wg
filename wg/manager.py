from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

WG_DIR = Path("/etc/wireguard")


def list_configs() -> list[str]:
    try:
        result = subprocess.run(
            ["sudo", "-n", "bash", "-c", f"ls -1 {WG_DIR}/*.conf 2>/dev/null"],
            capture_output=True, text=True
        )
        names = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                names.append(Path(line).stem)
        return names
    except Exception:
        return []


def is_up(iface: str) -> bool:
    try:
        result = subprocess.run(
            ["sudo", "-n", "wg", "show", "interfaces"],
            capture_output=True, text=True
        )
        return iface in result.stdout.split()
    except Exception:
        return False


def up(iface: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "-n", "wg-quick", "up", iface],
            capture_output=True, text=True
        )
        ok = result.returncode == 0
        msg = result.stderr if not ok else result.stdout
        return ok, msg
    except Exception as e:
        return False, str(e)


def down(iface: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "-n", "wg-quick", "down", iface],
            capture_output=True, text=True
        )
        ok = result.returncode == 0
        msg = result.stderr if not ok else result.stdout
        return ok, msg
    except Exception as e:
        return False, str(e)


def get_stats(iface: str) -> dict:
    try:
        result = subprocess.run(
            ["sudo", "-n", "wg", "show", iface],
            capture_output=True, text=True
        )
        data = {"tx": 0, "rx": 0, "endpoint": "", "handshake": ""}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("transfer:"):
                parts = line.split()
                # "transfer: X.XX MiB received, Y.YY MiB sent"
                try:
                    # format: "transfer: RX unit received, TX unit sent"
                    rx_val = float(parts[1])
                    rx_unit = parts[2].rstrip(",")
                    tx_val = float(parts[4])   # parts[3] == "received,"
                    tx_unit = parts[5]
                    data["rx"] = _to_bytes(rx_val, rx_unit)
                    data["tx"] = _to_bytes(tx_val, tx_unit)
                except (IndexError, ValueError):
                    pass
            elif line.startswith("endpoint:"):
                data["endpoint"] = line.split(":", 1)[1].strip()
            elif line.startswith("latest handshake:"):
                data["handshake"] = line.split(":", 1)[1].strip()
        return data
    except Exception:
        return {"tx": 0, "rx": 0, "endpoint": "", "handshake": ""}


def _to_bytes(val: float, unit: str) -> int:
    unit = unit.lower()
    mult = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3,
            "kb": 1000, "mb": 1000**2, "gb": 1000**3}
    return int(val * mult.get(unit, 1))


def fmt_bytes(n: int) -> str:
    for unit, threshold in [("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)]:
        if n >= threshold:
            return f"{n/threshold:.2f} {unit}"
    return f"{n} B"


def get_address(iface: str) -> str:
    try:
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", iface],
            capture_output=True, text=True
        )
        m = re.search(r"inet (\S+)", result.stdout)
        return m.group(1) if m else ""
    except Exception:
        return ""


def import_config(src: Path, name: str) -> tuple[bool, str]:
    if len(name) > 15:
        return False, f"Name '{name}' exceeds 15 chars (WireGuard limit)"
    dest = WG_DIR / f"{name}.conf"
    try:
        result = subprocess.run(
            ["sudo", "-n", "install", "-m", "600", str(src), str(dest)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, str(dest)
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def delete_config(iface: str) -> tuple[bool, str]:
    try:
        if is_up(iface):
            ok, msg = down(iface)
            if not ok:
                return False, f"Could not bring down tunnel: {msg}"
        subprocess.run(
            ["sudo", "-n", "rm", "-f", str(WG_DIR / f"{iface}.conf")],
            capture_output=True
        )
        return True, ""
    except Exception as e:
        return False, str(e)


def wg_quick_available() -> bool:
    return shutil.which("wg-quick") is not None
