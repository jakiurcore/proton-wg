#!/usr/bin/env bash
# ProtonWG uninstaller
set -euo pipefail

GREEN=$'\e[32m'; YELLOW=$'\e[33m'; CYAN=$'\e[36m'; RESET=$'\e[0m'; BOLD=$'\e[1m'

ok()   { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}!${RESET} %s\n" "$*"; }
info() { printf "${CYAN}»${RESET} %s\n" "$*"; }

echo
printf "${BOLD}ProtonWG Uninstaller${RESET}\n"
echo "──────────────────────────────────────"

info "Removing protonwg package…"
uv tool uninstall protonwg 2>/dev/null && ok "protonwg removed" || warn "protonwg not installed via uv"

# Clean up any legacy symlink from old install
if [[ -L /usr/local/bin/protonwg ]]; then
    info "Removing legacy symlink /usr/local/bin/protonwg…"
    sudo rm -f /usr/local/bin/protonwg
    ok "legacy symlink removed"
fi

echo
echo "──────────────────────────────────────"
ok "${BOLD}Uninstall complete.${RESET}"
warn "WireGuard configs in /etc/wireguard/ and iptables kill switch rules are NOT removed."
warn "To remove configs: sudo rm /etc/wireguard/<name>.conf"
warn "To remove kill switch: sudo iptables -D OUTPUT -j protonwg_ks 2>/dev/null; sudo iptables -F protonwg_ks 2>/dev/null; sudo iptables -X protonwg_ks 2>/dev/null"
echo
