from __future__ import annotations

import re
import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Static

WG_DIR = Path("/etc/wireguard")
KILL_MARK = "# protonwg-killswitch"
CHAIN = "protonwg_ks"  # named chain — survives connect/disconnect cycles


# ---------- helpers -----------------------------------------------------------

def _read_conf(iface: str) -> str:
    r = subprocess.run(
        ["sudo", "-n", "cat", str(WG_DIR / f"{iface}.conf")],
        capture_output=True, text=True,
    )
    return r.stdout if r.returncode == 0 else ""


def _get_endpoint(iface: str) -> tuple[str, str] | None:
    """Parse first [Peer] Endpoint = ip:port from config."""
    for line in _read_conf(iface).splitlines():
        line = line.strip()
        if not line.lower().startswith("endpoint"):
            continue
        val = line.split("=", 1)[1].strip()
        try:
            if val.startswith("["):                   # IPv6 endpoint
                ip = val[1:val.index("]")]
                port = val.split("]")[1].lstrip(":")
            else:
                ip, port = val.rsplit(":", 1)
            return ip.strip(), port.strip()
        except ValueError:
            pass
    return None


def _chain_exists(table: str = "iptables") -> bool:
    r = subprocess.run(
        ["sudo", "-n", table, "-n", "-L", CHAIN],
        capture_output=True,
    )
    return r.returncode == 0


def is_active(iface: str) -> bool:
    """Kill switch is active if our chain is in OUTPUT and has rules."""
    return _chain_exists("iptables")


# ---------- rule management ---------------------------------------------------

def apply_rules(iface: str) -> tuple[bool, str]:
    """
    Build and immediately apply iptables rules.
    Uses a named chain so rules survive wg-quick connect/disconnect.
    Whitelists the WireGuard endpoint IP so the VPN can (re)connect.
    """
    endpoint = _get_endpoint(iface)
    ep_rule4 = ""
    if endpoint:
        ip, port = endpoint
        # Only whitelist IPv4 endpoints (ProtonVPN always IPv4)
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
            ep_rule4 = f"iptables -A {CHAIN} -d {ip} -p udp --dport {port} -j ACCEPT && "

    # Build one compound bash command.
    # iptables chain is flushed + rebuilt → idempotent on reconnect.
    cmd4 = (
        f"iptables -N {CHAIN} 2>/dev/null || iptables -F {CHAIN} && "
        f"iptables -A {CHAIN} -o lo -j ACCEPT && "
        f"iptables -A {CHAIN} -m addrtype --dst-type LOCAL -j ACCEPT && "
        f"{ep_rule4}"
        f"iptables -A {CHAIN} -o {iface} -j ACCEPT && "
        f"iptables -A {CHAIN} -j REJECT --reject-with icmp-net-unreachable && "
        f"iptables -D OUTPUT -j {CHAIN} 2>/dev/null ; "  # remove stale jump first
        f"iptables -I OUTPUT -j {CHAIN}"
    )

    # IPv6: block all non-VPN (ProtonVPN endpoints are IPv4 only)
    cmd6 = (
        f"ip6tables -N {CHAIN} 2>/dev/null || ip6tables -F {CHAIN} && "
        f"ip6tables -A {CHAIN} -o lo -j ACCEPT && "
        f"ip6tables -A {CHAIN} -o {iface} -j ACCEPT && "
        f"ip6tables -A {CHAIN} -j REJECT --reject-with icmp6-port-unreachable && "
        f"ip6tables -D OUTPUT -j {CHAIN} 2>/dev/null ; "
        f"ip6tables -I OUTPUT -j {CHAIN}"
    )
    # ip6tables may not exist or IPv6 may be disabled — that's fine
    full = f"{cmd4} && ( {cmd6} || true )"

    r = subprocess.run(["sudo", "-n", "bash", "-c", full], capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr.strip()

    # Also write PostUp to config so kill switch re-activates on boot-time
    # autostart (wg-quick up runs before this app). No PreDown — rules persist
    # until the user explicitly disables the kill switch.
    _write_config_hooks(iface, endpoint)
    return True, ""


def remove_rules(iface: str) -> tuple[bool, str]:
    """Remove iptables chain and config PostUp hooks."""
    cmd = (
        f"iptables -D OUTPUT -j {CHAIN} 2>/dev/null ; "
        f"iptables -F {CHAIN} 2>/dev/null ; "
        f"iptables -X {CHAIN} 2>/dev/null ; "
        f"ip6tables -D OUTPUT -j {CHAIN} 2>/dev/null ; "
        f"ip6tables -F {CHAIN} 2>/dev/null ; "
        f"ip6tables -X {CHAIN} 2>/dev/null"
    )
    subprocess.run(["sudo", "-n", "bash", "-c", cmd], capture_output=True)
    _remove_config_hooks(iface)
    return True, ""


# ---------- config file hooks -------------------------------------------------

def _write_config_hooks(iface: str, endpoint: tuple[str, str] | None) -> None:
    """
    Add PostUp lines to config so kill switch survives reboot (when autostart
    is on). No PreDown — we want rules to STAY even after wg-quick down.
    """
    conf = WG_DIR / f"{iface}.conf"
    content = _read_conf(iface)
    if not content:
        return

    # Remove any existing kill switch lines first
    clean = [ln for ln in content.splitlines() if KILL_MARK not in ln]

    ep_rule = ""
    if endpoint:
        ip, port = endpoint
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
            ep_rule = (
                f"PostUp = iptables -A {CHAIN} -d {ip} -p udp --dport {port}"
                f" -j ACCEPT {KILL_MARK}\n"
            )

    hooks = (
        f"PostUp = iptables -N {CHAIN} 2>/dev/null || iptables -F {CHAIN} {KILL_MARK}\n"
        f"PostUp = iptables -A {CHAIN} -o lo -j ACCEPT {KILL_MARK}\n"
        f"PostUp = iptables -A {CHAIN} -m addrtype --dst-type LOCAL -j ACCEPT {KILL_MARK}\n"
        f"{ep_rule}"
        f"PostUp = iptables -A {CHAIN} -o %i -j ACCEPT {KILL_MARK}\n"
        f"PostUp = iptables -A {CHAIN} -j REJECT --reject-with icmp-net-unreachable {KILL_MARK}\n"
        f"PostUp = iptables -D OUTPUT -j {CHAIN} 2>/dev/null {KILL_MARK}\n"
        f"PostUp = iptables -I OUTPUT -j {CHAIN} {KILL_MARK}\n"
    )

    new_lines: list[str] = []
    inserted = False
    for ln in clean:
        new_lines.append(ln)
        if not inserted and ln.strip() == "[Interface]":
            new_lines.append(hooks.rstrip("\n"))
            inserted = True

    new_content = "\n".join(new_lines) + "\n"
    w = subprocess.run(
        ["sudo", "-n", "tee", str(conf)],
        input=new_content, capture_output=True, text=True,
    )
    if w.returncode == 0:
        subprocess.run(["sudo", "-n", "chmod", "600", str(conf)], capture_output=True)


def _remove_config_hooks(iface: str) -> None:
    conf = WG_DIR / f"{iface}.conf"
    subprocess.run(
        ["sudo", "-n", "sed", "-i", f"/{re.escape(KILL_MARK)}/d", str(conf)],
        capture_output=True,
    )


def has_config_hooks(iface: str) -> bool:
    content = _read_conf(iface)
    return KILL_MARK in content


# ---------- screen ------------------------------------------------------------

_HOW_IT_WORKS = """\
[bold]What this does:[/bold]
  • Blocks ALL internet [bold]immediately[/bold] — even while VPN is disconnected
  • Only allows traffic through the VPN tunnel ([bold]{iface}[/bold])
  • Whitelists the ProtonVPN endpoint IP so the tunnel can (re)connect
  • Rules persist until you explicitly disable the kill switch here
  • Config PostUp added so rules reactivate on boot (if autostart is on)\
"""

_REMOVE_DESC = """\
Kill switch rules will be removed from iptables immediately.
Internet will work again regardless of VPN state.\
"""


class KillswitchScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    KillswitchScreen {
        align: center middle;
    }
    KillswitchScreen #box {
        width: 74;
        height: auto;
        border: double $warning;
        padding: 1 2;
        background: $surface;
    }
    KillswitchScreen #desc {
        margin-bottom: 2;
        color: $text-muted;
    }
    KillswitchScreen #btn-row {
        layout: horizontal;
        align: center middle;
        height: 3;
    }
    KillswitchScreen #btn-row Button {
        margin: 0 1;
    }
    """

    def __init__(self, iface: str) -> None:
        super().__init__()
        self._iface = iface
        # Active = iptables chain exists (runtime) OR config has hooks (boot state)
        self._active = is_active(iface) or has_config_hooks(iface)

    def compose(self) -> ComposeResult:
        state = "[green]ON[/green]" if self._active else "[red]OFF[/red]"
        action = "Disable kill switch" if self._active else "Enable kill switch"
        desc = _REMOVE_DESC if self._active else _HOW_IT_WORKS.format(iface=self._iface)
        variant = "warning" if self._active else "error"

        with Static(id="box"):
            yield Static(f"[bold]Kill Switch[/bold] — [bold]{self._iface}[/bold]  {state}\n")
            yield Static(desc, id="desc")
            with Static(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button(action, variant=variant, id="btn-action")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss()
            return

        if self._active:
            ok, msg = remove_rules(self._iface)
            if ok:
                self.app.notify(
                    "Kill switch disabled. Internet unrestricted.",
                    severity="information", timeout=5,
                )
            else:
                self.app.notify(f"Failed: {msg}", severity="error", timeout=10)
        else:
            ok, msg = apply_rules(self._iface)
            if ok:
                ep = _get_endpoint(self._iface)
                ep_note = f" (endpoint {ep[0]} whitelisted)" if ep else ""
                self.app.notify(
                    f"Kill switch active{ep_note}. Internet blocked until VPN connects.",
                    severity="warning", timeout=8,
                )
            else:
                self.app.notify(
                    f"Failed to apply rules: {msg}\n"
                    "Check iptables is installed: sudo pacman -S iptables",
                    severity="error", timeout=12,
                )
        self.dismiss()
