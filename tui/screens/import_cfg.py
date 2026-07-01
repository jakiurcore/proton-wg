from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from wg import manager


class ImportScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
    ]

    DEFAULT_CSS = """
    ImportScreen {
        align: center middle;
    }
    ImportScreen #import-box {
        width: 70;
        height: auto;
        border: double $primary;
        padding: 1 2;
        background: $surface;
    }
    ImportScreen #import-box Label {
        margin-bottom: 1;
        color: $text-muted;
    }
    ImportScreen #import-box Input {
        margin-bottom: 1;
    }
    ImportScreen #name-row {
        display: none;
        margin-bottom: 1;
    }
    ImportScreen #name-row.visible {
        display: block;
    }
    ImportScreen #status {
        margin-top: 1;
        min-height: 2;
    }
    ImportScreen #btn-row {
        margin-top: 1;
        layout: horizontal;
        align: right middle;
        height: 3;
    }
    ImportScreen #btn-row Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Static(id="import-box"):
            yield Static(
                "[bold $primary]Import WireGuard Config[/bold $primary]\n"
                "[dim]Download from account.protonvpn.com → Downloads → WireGuard[/dim]\n",
            )
            yield Label("Path to .conf file:")
            yield Input(placeholder="/home/user/Downloads/ProtonVPN.conf", id="path-input")
            with Static(id="name-row"):
                yield Label("Custom name (≤15 chars, no spaces):", id="name-label")
                yield Input(placeholder="ProtonVPN-US", id="name-input")
            yield Static("", id="status")
            with Static(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Import", variant="primary", id="btn-import")
        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "path-input":
            self._check_name(event.value)

    def _check_name(self, path_str: str) -> None:
        path = Path(path_str.replace("~", str(Path.home())))
        stem = path.stem
        name_row = self.query_one("#name-row")
        if stem and len(stem) > 15:
            name_row.add_class("visible")
        else:
            name_row.remove_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
        elif event.button.id == "btn-import":
            self._do_import()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_import()

    def _do_import(self) -> None:
        status = self.query_one("#status", Static)
        path_str = self.query_one("#path-input", Input).value.strip()
        if not path_str:
            status.update("[red]Enter a file path.[/red]")
            return

        src = Path(path_str.replace("~", str(Path.home())))
        if not src.exists():
            status.update(f"[red]File not found: {src}[/red]")
            return
        if src.suffix != ".conf":
            status.update("[yellow]Warning: file doesn't end in .conf[/yellow]")

        name = src.stem
        name_row = self.query_one("#name-row")
        if "visible" in name_row.classes:
            name = self.query_one("#name-input", Input).value.strip().replace(" ", "")
            if not name or len(name) > 15:
                status.update("[red]Name must be 1–15 chars with no spaces.[/red]")
                return

        status.update("[dim]Copying…[/dim]")
        ok, msg = manager.import_config(src, name)
        if ok:
            self.app.notify(f"Imported as [bold]{name}[/bold]", title="Success", severity="information")
            self.app.pop_screen()
            self.app.refresh_tunnel_list()
        else:
            status.update(f"[red]{msg}[/red]")
