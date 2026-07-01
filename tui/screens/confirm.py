from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel"),
        Binding("n", "dismiss(False)", "No"),
        Binding("y", "dismiss(True)", "Yes"),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen #box {
        width: 60;
        height: auto;
        border: double $error;
        padding: 1 2;
        background: $surface;
    }
    ConfirmScreen #message {
        margin-bottom: 2;
        text-align: center;
    }
    ConfirmScreen #btn-row {
        layout: horizontal;
        align: center middle;
        height: 3;
    }
    ConfirmScreen #btn-row Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Static(id="box"):
            yield Static(self._message, id="message")
            with Static(id="btn-row"):
                yield Button("No  [dim](N)[/dim]", variant="default", id="btn-no")
                yield Button("Yes [dim](Y)[/dim]", variant="error", id="btn-yes")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")
