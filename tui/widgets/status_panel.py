from __future__ import annotations

import asyncio
import urllib.request
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from wg import manager, service


_PUBLIC_IP_URLS = [
    "https://ifconfig.me",
    "https://api.ipify.org",
    "https://icanhazip.com",
]


async def _fetch_public_ip() -> str:
    loop = asyncio.get_event_loop()
    for url in _PUBLIC_IP_URLS:
        try:
            ip = await loop.run_in_executor(
                None,
                lambda u=url: urllib.request.urlopen(u, timeout=6).read().decode().strip()
            )
            if ip:
                return ip
        except Exception:
            continue
    return "unavailable"


class StatusPanel(Widget):
    DEFAULT_CSS = """
    StatusPanel {
        width: 2fr;
        height: 100%;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    _iface: str | None = None
    _public_ip: str = "fetching…"
    _connected_at: datetime | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="sp-content")

    def on_mount(self) -> None:
        self._redraw()
        self.set_interval(5, self._tick)
        self.run_worker(self._load_ip(), exclusive=True, name="ip-fetch")

    async def _load_ip(self) -> None:
        self._public_ip = await _fetch_public_ip()
        self._redraw()

    def set_tunnel(self, iface: str | None) -> None:
        self._iface = iface
        self._connected_at = datetime.now() if iface else None
        self._redraw()
        self.run_worker(self._load_ip(), exclusive=True, name="ip-fetch")

    def _tick(self) -> None:
        self._redraw()

    def _redraw(self) -> None:
        content = self.query_one("#sp-content", Static)

        lines: list[str] = []
        lines.append("[bold $primary]STATUS[/bold $primary]\n")
        lines.append(f"[dim]Public IP  [/dim] [bold]{self._public_ip}[/bold]")
        lines.append("")

        if self._iface:
            up = manager.is_up(self._iface)
            boot = service.is_enabled(self._iface)
            boot_txt = "[cyan]enabled[/cyan]" if boot else "[red]disabled[/red]"
            boot_hint = "" if boot else "  [dim](press B to enable)[/dim]"

            lines.append(f"[dim]Tunnel    [/dim]  [bold]{self._iface}[/bold]")
            lines.append(f"[dim]Autostart [/dim]  {boot_txt}{boot_hint}")

            if up:
                stats = manager.get_stats(self._iface)
                addr = manager.get_address(self._iface)

                if addr:
                    lines.append(f"[dim]Address   [/dim]  {addr}")
                if self._connected_at:
                    elapsed = datetime.now() - self._connected_at
                    h, rem = divmod(int(elapsed.total_seconds()), 3600)
                    m, s = divmod(rem, 60)
                    lines.append(f"[dim]Uptime    [/dim]  {h:02d}:{m:02d}:{s:02d}")
                if stats["handshake"]:
                    lines.append(f"[dim]Handshake [/dim]  {stats['handshake']}")
                if stats["endpoint"]:
                    lines.append(f"[dim]Endpoint  [/dim]  {stats['endpoint']}")
                lines.append("")
                lines.append(f"[green]↑ Sent    [/green]  {manager.fmt_bytes(stats['tx'])}")
                lines.append(f"[cyan]↓ Recv    [/cyan]  {manager.fmt_bytes(stats['rx'])}")
            else:
                lines.append("")
                lines.append("[dim]Tunnel is down.[/dim]")
                lines.append("[dim]Press [bold]Enter[/bold] to connect.[/dim]")
        else:
            lines.append("[dim]Select a tunnel and press [bold]Enter[/bold] to connect.[/dim]")

        content.update("\n".join(lines))
