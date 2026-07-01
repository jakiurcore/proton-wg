from __future__ import annotations

from textual.app import App

from tui.screens.dashboard import DashboardScreen

CSS = """
Screen {
    background: $background;
}

Header {
    background: $primary-darken-3;
    color: $text;
}

Footer {
    background: $primary-darken-3;
}

/* Tunnel list panel */
TunnelList {
    background: $surface;
}

/* Status panel */
StatusPanel {
    background: $background;
}
"""


class ProtonWGApp(App):
    TITLE = "ProtonWG"
    SUB_TITLE = "WireGuard Manager for Arch Linux"
    CSS = CSS

    DARK = True

    # Purple-tinted dark theme overrides
    DEFAULT_CSS = """
    $primary: #7c3aed;
    $primary-darken-1: #6d28d9;
    $primary-darken-2: #5b21b6;
    $primary-darken-3: #1e1033;
    $success: #22c55e;
    $warning: #f59e0b;
    $error: #ef4444;
    $surface: #1e1e2e;
    $background: #13131f;
    $text: #e2e8f0;
    $text-muted: #94a3b8;
    """

    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())

    def refresh_tunnel_list(self) -> None:
        try:
            screen = self.screen
            if hasattr(screen, "refresh_tunnel_list"):
                screen.refresh_tunnel_list()
        except Exception:
            pass
