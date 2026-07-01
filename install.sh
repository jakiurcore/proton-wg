#!/usr/bin/env bash
# ProtonWG installer — Arch Linux
set -euo pipefail

GREEN=$'\e[32m'; YELLOW=$'\e[33m'; RED=$'\e[31m'; CYAN=$'\e[36m'; RESET=$'\e[0m'; BOLD=$'\e[1m'

ok()   { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}!${RESET} %s\n" "$*"; }
err()  { printf "${RED}✗${RESET} %s\n" "$*"; }
info() { printf "${CYAN}»${RESET} %s\n" "$*"; }

echo
printf "${BOLD}ProtonWG Installer${RESET}\n"
echo "──────────────────────────────────────"

# --- 1. wireguard-tools -------------------------------------------------------
info "Installing wireguard-tools…"
sudo pacman -S --needed --noconfirm wireguard-tools
ok "wireguard-tools"

# --- 2. DNS resolver ----------------------------------------------------------
_has_pkg() { pacman -Q "$1" >/dev/null 2>&1; }

if _has_pkg systemd-resolvconf; then
    # systemd-resolvconf is installed — it needs systemd-resolved running
    if ! systemctl is-active --quiet systemd-resolved 2>/dev/null; then
        info "systemd-resolvconf detected but systemd-resolved inactive — enabling…"
        sudo systemctl enable --now systemd-resolved
        ok "systemd-resolved enabled & started"
    else
        ok "systemd-resolvconf + systemd-resolved already active"
    fi
elif _has_pkg openresolv; then
    ok "openresolv already installed"
else
    info "Installing openresolv…"
    sudo pacman -S --needed --noconfirm openresolv
    ok "openresolv"
fi

# --- 3. curl (for public IP check) -------------------------------------------
sudo pacman -S --needed --noconfirm curl
ok "curl"

# --- 4. python ----------------------------------------------------------------
info "Checking Python…"
if ! command -v python3 >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python $PYVER"

# --- 5. textual ---------------------------------------------------------------
info "Installing textual (TUI framework)…"
if python3 -c "import textual" 2>/dev/null; then
    ok "textual already installed"
else
    pip install --user --quiet --break-system-packages textual
    ok "textual"
fi

# --- 6. install package (editable) -------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Installing protonwg package…"
pip install --user -e "$SCRIPT_DIR" --quiet --break-system-packages
ok "protonwg installed (~/.local/bin/protonwg)"

# --- 7. PATH check ------------------------------------------------------------
LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo
    warn "${LOCAL_BIN} not in PATH — add this to your shell config:"
    printf "    ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}\n"
    printf "  For bash:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc\n"
    printf "  For zsh:   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc\n"
    echo
    warn "Then restart your shell or run:  source ~/.bashrc  (or ~/.zshrc)"
else
    ok "\$HOME/.local/bin already in PATH"
fi

echo
echo "──────────────────────────────────────"
ok "${BOLD}Installation complete!${RESET}"
echo
info "Run:  ${BOLD}protonwg${RESET}"
info "Uninstall:  ${BOLD}bash $SCRIPT_DIR/uninstall.sh${RESET}"
echo
warn "Tip: Import your ProtonVPN WireGuard .conf from the app."
warn "     Download at: account.protonvpn.com → Downloads → WireGuard"
echo
