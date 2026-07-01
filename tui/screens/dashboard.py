from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header

from tui.widgets.status_panel import StatusPanel
from tui.widgets.tunnel_list import TunnelList, TunnelSelected
from wg import dns, manager, service


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("i", "import_config", "Import"),
        Binding("b", "boot_toggle", "Boot toggle"),
        Binding("k", "killswitch", "Kill switch"),
        Binding("d", "delete_config", "Delete"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "app.quit", "Quit"),
    ]

    DEFAULT_CSS = """
    DashboardScreen #main-row {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-row"):
            yield TunnelList(id="tunnel-list")
            yield StatusPanel(id="status-panel")
        yield Footer()

    def on_mount(self) -> None:
        tl = self.query_one("#tunnel-list", TunnelList)
        tl.focus()
        iface = tl.current_iface()
        if iface:
            self.query_one("#status-panel", StatusPanel).set_tunnel(iface)

    def on_tunnel_selected(self, event: TunnelSelected) -> None:
        self._toggle(event.iface)

    def _toggle(self, iface: str) -> None:
        sp = self.query_one("#status-panel", StatusPanel)
        if manager.is_up(iface):
            self.app.notify(f"Disconnecting {iface}…", severity="information")
            ok, msg = manager.down(iface)
            if ok:
                self.app.notify(f"[bold]{iface}[/bold] disconnected", severity="information")
                sp.set_tunnel(None)
            else:
                self.app.notify(f"Failed: {msg}", severity="error")
        else:
            self.app.notify(f"Connecting {iface}…", severity="information")
            ok, msg = manager.up(iface)
            if ok:
                self.app.notify(f"[bold]{iface}[/bold] connected", severity="information")
                sp.set_tunnel(iface)
            else:
                hint = ""
                if dns.is_dns_error(msg):
                    hint = f"\n[yellow]DNS fix:[/yellow] {dns.install_hint()}"
                self.app.notify(f"Failed: {msg}{hint}", severity="error", timeout=10)
        self.query_one("#tunnel-list", TunnelList).refresh_list()

    def action_import_config(self) -> None:
        from tui.screens.import_cfg import ImportScreen
        self.app.push_screen(ImportScreen())

    def action_boot_toggle(self) -> None:
        tl = self.query_one("#tunnel-list", TunnelList)
        iface = tl.current_iface()
        if not iface:
            self.app.notify("Select a tunnel first", severity="warning")
            return
        if service.is_enabled(iface):
            ok, msg = service.disable(iface)
            verb = "disabled"
        else:
            ok, msg = service.enable(iface)
            verb = "enabled"
        if ok:
            self.app.notify(f"Autostart {verb} for [bold]{iface}[/bold]")
        else:
            self.app.notify(f"Failed: {msg}", severity="error")
        tl.refresh_list()

    def action_killswitch(self) -> None:
        from tui.screens.killswitch import KillswitchScreen
        iface = self.query_one("#tunnel-list", TunnelList).current_iface()
        if not iface:
            self.app.notify("Select a tunnel first", severity="warning")
            return
        self.app.push_screen(KillswitchScreen(iface))

    def action_delete_config(self) -> None:
        from tui.screens.confirm import ConfirmScreen
        iface = self.query_one("#tunnel-list", TunnelList).current_iface()
        if not iface:
            self.app.notify("Select a tunnel first", severity="warning")
            return

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            ok, msg = manager.delete_config(iface)
            if ok:
                self.app.notify(f"Deleted [bold]{iface}[/bold]")
            else:
                self.app.notify(f"Failed: {msg}", severity="error")
            self.query_one("#tunnel-list", TunnelList).refresh_list()
            self.query_one("#status-panel", StatusPanel).set_tunnel(None)

        self.app.push_screen(
            ConfirmScreen(f"Permanently delete [bold]{iface}[/bold]?"),
            _on_confirm,
        )

    def action_refresh(self) -> None:
        tl = self.query_one("#tunnel-list", TunnelList)
        tl.refresh_list()
        iface = tl.current_iface()
        self.query_one("#status-panel", StatusPanel).set_tunnel(iface)

    def refresh_tunnel_list(self) -> None:
        self.query_one("#tunnel-list", TunnelList).refresh_list()
