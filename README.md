# ProtonWG

A terminal UI for managing ProtonVPN WireGuard connections on Arch Linux.

```
╔══════════════════════════════════════════════════════════════════╗
║  ProtonWG · WireGuard Manager for Arch Linux          12:34:56  ║
╠═══════════════════════╦══════════════════════════════════════════╣
║  TUNNELS              ║  STATUS                                  ║
║                       ║                                          ║
║  ● Linux_21-MY-21     ║  Public IP    185.159.157.3              ║
║    10.2.0.2/32        ║  Tunnel       Linux_21-MY-21             ║
║    boot:on            ║  Address      10.2.0.2/32                ║
║                       ║  Uptime       00:14:32                   ║
║  ○ ProtonVPN-NL       ║  Handshake    14 seconds ago             ║
║    boot:off           ║  Endpoint     4.x.x.x:51820              ║
║                       ║                                          ║
║                       ║  ↑ Sent       1.24 MiB                   ║
║                       ║  ↓ Recv       4.58 MiB                   ║
║                       ║  Autostart    enabled (press B to toggle) ║
╠═══════════════════════╩══════════════════════════════════════════╣
║  I Import  B Boot  K Kill switch  D Delete  R Refresh  Q Quit   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Requirements

- Arch Linux (uses `pacman`)
- Python 3.9+
- [`uv`](https://github.com/astral-sh/uv) (Python package/tool manager)
- `wireguard-tools`
- `openresolv` or `systemd-resolvconf` + `systemd-resolved`
- `iptables` (for kill switch)
- `curl` (for public IP display)

---

## Install

```bash
git clone https://github.com/youruser/protonwg
cd protonwg
bash install.sh
```

`install.sh` does:
1. `pacman -S wireguard-tools` — WireGuard kernel module + tools
2. DNS resolver — detects which is installed:
   - `systemd-resolvconf` present + `systemd-resolved` inactive → enables `systemd-resolved`
   - Neither present → installs `openresolv`
3. `pacman -S curl python uv`
4. `uv tool install --editable .` — installs `protonwg` (and its `textual` dependency) as an isolated tool, creates `~/.local/bin/protonwg`

After install, run from anywhere:
```bash
protonwg
```

Or from the project directory directly:
```bash
./main.sh
uv run protonwg.py
```

> **PATH note:** `~/.local/bin` must be in `$PATH`. If `install.sh` warns about this, add the line it prints to your `~/.bashrc` or `~/.zshrc`, then restart your shell.

## Uninstall

```bash
bash uninstall.sh
```

Removes the `protonwg` command. WireGuard configs in `/etc/wireguard/` are not touched.

---

## Getting a ProtonVPN WireGuard config

1. Log in at **account.protonvpn.com**
2. Go to **Downloads → WireGuard configuration**
3. Select server, download the `.conf` file
4. In the TUI press `I`, enter the path to the file

> Config name must be ≤ 15 characters (Linux interface name limit).  
> The app will prompt for a shorter name if needed.

---

## Usage

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate tunnel list |
| `Enter` | Connect (if down) / Disconnect (if up) |
| `I` | Import a `.conf` file |
| `B` | Toggle autostart on boot |
| `K` | Toggle kill switch |
| `D` | Delete selected config |
| `R` | Refresh tunnel list and status |
| `Q` | Quit (VPN stays connected) |

### Connect / Disconnect

Select a tunnel with `↑`/`↓` and press `Enter`. The status panel on the right updates with public IP, uptime, and traffic stats (refreshes every 5 seconds).

Closing the app does **not** disconnect the VPN — WireGuard runs as a kernel network interface.

### Autostart on boot

Press `B` to toggle `systemctl enable/disable wg-quick@<name>`.  
The status panel shows current boot state and hints to press `B` if disabled.

### Kill switch

Press `K` to open the kill switch panel.

**What it does:**
- Applies `iptables` rules **immediately** — internet is blocked as soon as you enable it, even if the VPN is not connected
- Only allows traffic through the WireGuard tunnel interface
- Whitelists the ProtonVPN endpoint IP so the tunnel can connect/reconnect
- Rules **persist** through connect/disconnect cycles — only removed when you explicitly disable
- Adds `PostUp` hooks to the config so rules reactivate on boot (when autostart is on)

**What it does NOT do:**
- It does not block internet after you manually disable it
- It does not survive a reboot unless autostart (`B`) is also enabled

**Test kill switch:**
```bash
# After enabling kill switch in TUI:
ping 8.8.8.8          # should fail (REJECT)

# Connect VPN (Enter in TUI):
ping 8.8.8.8          # should work through VPN

# Disconnect VPN (Enter again):
ping 8.8.8.8          # should fail again (rules persist)

# Disable kill switch (K → Disable):
ping 8.8.8.8          # works again
```

---

## DNS fix

The error below appears when `systemd-resolvconf` is installed but `systemd-resolved` is not running:

```
Failed to set DNS configuration: Could not activate remote peer
'org.freedesktop.resolve1': activation request failed: unknown unit
```

`install.sh` fixes this automatically. To fix manually:
```bash
sudo systemctl enable --now systemd-resolved
# or replace systemd-resolvconf with openresolv:
sudo pacman -S openresolv
```

---

## File structure

```
protonwg/
├── main.sh              # Launcher (runs protonwg.py from project dir)
├── protonwg.py          # Entry point — dependency check, sudo auth, start TUI
├── install.sh           # Installer (uv tool install -e . → protonwg command)
├── uninstall.sh         # Uninstaller (uv tool uninstall protonwg)
├── pyproject.toml       # Python package metadata + entry point definition
│
├── wg/
│   ├── manager.py       # wg-quick up/down, parse wg show, list/import/delete configs
│   ├── dns.py           # Detect DNS backend (openresolv vs systemd-resolved)
│   └── service.py       # systemctl enable/disable wg-quick@<iface>
│
└── tui/
    ├── app.py           # Textual App class, dark purple theme
    ├── screens/
    │   ├── dashboard.py   # Main screen: tunnel list + status panel + keybindings
    │   ├── import_cfg.py  # Import .conf screen
    │   ├── killswitch.py  # Kill switch toggle modal + iptables rule management
    │   └── confirm.py     # Generic yes/no confirmation modal
    └── widgets/
        ├── tunnel_list.py   # Left panel: config list with ●/○ state indicator
        └── status_panel.py  # Right panel: public IP, uptime, tx/rx (5s refresh)
```

---

## How it works

### Entry point

`uv tool install --editable .` registers `protonwg = "protonwg:main"` (from `pyproject.toml`) in an isolated tool environment and creates `~/.local/bin/protonwg` — a wrapper script that calls `protonwg.main()` against an editable link back to this source directory (so local changes are picked up without reinstalling). This is why the command works from any directory without symlink or PATH hacks.

Running directly (`uv run protonwg.py` or `./main.sh`) also works — `uv run` syncs the dependencies declared in `pyproject.toml` into a project-local `.venv` on first run, and the `__main__` block uses `os.path.realpath(__file__)` to resolve symlinks and inserts the correct directory into `sys.path`.

### sudo authentication

`protonwg.py` calls `sudo -v` before launching the TUI. This caches the sudo token in normal terminal mode. All subsequent `sudo` calls inside the TUI use `-n` (non-interactive) — they fail fast instead of hanging if the token expires, rather than prompting mid-session inside the TUI where input is not possible.

### WireGuard operations (`wg/manager.py`)

All WireGuard operations are thin wrappers around `wg-quick` and `wg` CLI tools:

- `list_configs()` — `sudo ls /etc/wireguard/*.conf`
- `is_up(iface)` — `sudo wg show interfaces`
- `up(iface)` / `down(iface)` — `sudo wg-quick up/down`
- `get_stats(iface)` — `sudo wg show <iface>`, parses transfer/handshake/endpoint lines
- `get_address(iface)` — `ip -o -4 addr show <iface>`
- `import_config(src, name)` — `sudo install -m 600 src /etc/wireguard/name.conf`

### Kill switch (`tui/screens/killswitch.py`)

Uses a named iptables chain `protonwg_ks`:

```
OUTPUT → protonwg_ks chain:
  ACCEPT  lo (loopback)
  ACCEPT  LOCAL destinations
  ACCEPT  <endpoint-ip>:udp:<port>   ← WireGuard server, so VPN can reconnect
  ACCEPT  -o <wg-interface>          ← traffic through VPN
  REJECT  everything else
```

Chain is created/flushed on enable (idempotent), removed on disable.  
Config `PostUp` lines mirror the chain setup so rules apply on boot-time autostart.

### Status refresh

`StatusPanel` uses `textual.widget.set_interval(5, callback)` for live stats.  
Public IP is fetched async via `run_worker` (tries `ifconfig.me`, `api.ipify.org`, `icanhazip.com` in order).

---

## Development

### Setup

```bash
git clone https://github.com/youruser/protonwg
cd protonwg
bash install.sh   # installs deps + registers protonwg command
```

For UI-only development without WireGuard:
```bash
uv sync   # installs textual into a project-local .venv
```

### Project dependencies

| Package | Purpose |
|---------|---------|
| `textual` | TUI framework (async, panels, widgets, CSS styling) |
| `wireguard-tools` | `wg`, `wg-quick` CLI tools |
| `openresolv` or `systemd-resolvconf` | DNS config helper used by wg-quick |
| `iptables` | Kill switch rule management |

No other Python dependencies — `subprocess`, `pathlib`, `urllib.request` are stdlib.

### Adding a new screen

1. Create `tui/screens/myscreen.py` subclassing `textual.screen.Screen` or `ModalScreen`
2. Add a keybinding in `tui/screens/dashboard.py` BINDINGS
3. Add an `action_*` method that calls `self.app.push_screen(MyScreen())`

### Adding a new WireGuard operation

Add a function to `wg/manager.py`. All functions return `tuple[bool, str]` (success, message) for error display in the TUI via `self.app.notify(...)`.

### Running without WireGuard (UI development)

```bash
# Skip dependency check and sudo auth:
uv run python3 -c "
import sys, os
sys.path.insert(0, '.')
from tui.app import ProtonWGApp
ProtonWGApp().run()
"
```

The TUI renders with an empty tunnel list. Mock `wg/manager.py` functions to test UI flows.

### Syntax check

```bash
uv run python3 -m py_compile protonwg.py wg/*.py tui/app.py tui/screens/*.py tui/widgets/*.py
bash -n install.sh main.sh
```

---

## Troubleshooting

**`protonwg: command not found` after install**  
→ `~/.local/bin` not in `$PATH`. Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` or `~/.zshrc`, then restart shell. `install.sh` prints this exact line if it detects the issue.

**TUI hangs on `[sudo] password` at startup**  
→ The app needs to authenticate before launching. If it hangs inside the TUI, kill it (`Ctrl+C`) and re-run — you'll be prompted before the TUI starts.

**`wg-quick: command not found`**  
→ Run `bash install.sh` or `sudo pacman -S wireguard-tools`.

**`DuplicateIds` crash**  
→ Outdated code. Pull latest — fixed by rendering tunnel list as single Static widget.

**Kill switch doesn't block traffic**  
→ Check chain exists: `sudo iptables -L protonwg_ks -n`. If missing, re-enable via `K` in TUI.  
→ Check jump rule: `sudo iptables -L OUTPUT -n | grep protonwg_ks`.

**Kill switch blocks VPN from connecting**  
→ Endpoint IP not parsed. Check config has `Endpoint = <ip>:<port>` under `[Peer]`.  
→ Temporarily disable kill switch (`K`), connect VPN, re-enable.

**Sent/Recv shows 0 B**  
→ No traffic has passed through the tunnel yet, or WireGuard handshake not completed. Wait a few seconds after connecting.

**`ip6tables` errors in kill switch**  
→ Safe to ignore — `|| true` is used so IPv6 failures don't abort the operation.

---

## License

MIT
