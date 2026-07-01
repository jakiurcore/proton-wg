from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from wg import manager, service


class TunnelSelected(Message):
    def __init__(self, iface: str) -> None:
        super().__init__()
        self.iface = iface


class TunnelList(Widget):
    DEFAULT_CSS = """
    TunnelList {
        width: 1fr;
        height: 100%;
        border-right: solid $primary-darken-2;
        overflow-y: auto;
        padding: 0 1;
    }
    """

    COMPONENT_CLASSES = {"tunnel-list--selected"}

    selected_index: reactive[int] = reactive(0)
    _configs: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="tl-body")

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        self._configs = manager.list_configs()
        self._redraw()

    def _redraw(self) -> None:
        body = self.query_one("#tl-body", Static)
        lines: list[str] = ["[bold $primary]  TUNNELS[/bold $primary]\n"]

        if not self._configs:
            lines.append("  [dim]No configs — press [bold]I[/bold] to import[/dim]")
            body.update("\n".join(lines))
            return

        for i, iface in enumerate(self._configs):
            up = manager.is_up(iface)
            boot = service.is_enabled(iface)
            addr = manager.get_address(iface) if up else ""

            dot = "[bold green]●[/bold green]" if up else "[dim]○[/dim]"
            boot_txt = "[cyan]boot:on[/cyan]" if boot else "[dim]boot:off[/dim]"

            if i == self.selected_index:
                prefix = "[reverse] "
                suffix = " [/reverse]"
            else:
                prefix = "  "
                suffix = ""

            name_line = f"{prefix}{dot}  [bold]{iface}[/bold]{suffix}"
            lines.append(name_line)
            if addr:
                lines.append(f"     [dim]{addr}[/dim]")
            lines.append(f"     {boot_txt}")
            lines.append("")

        body.update("\n".join(lines))

    def on_key(self, event) -> None:
        if not self._configs:
            return
        n = len(self._configs)
        if event.key == "up":
            self.selected_index = (self.selected_index - 1) % n
            self._redraw()
            event.stop()
        elif event.key == "down":
            self.selected_index = (self.selected_index + 1) % n
            self._redraw()
            event.stop()
        elif event.key == "enter":
            iface = self._configs[self.selected_index]
            self.post_message(TunnelSelected(iface))
            event.stop()

    def current_iface(self) -> str | None:
        if self._configs and 0 <= self.selected_index < len(self._configs):
            return self._configs[self.selected_index]
        return None

    def can_focus(self) -> bool:
        return True
