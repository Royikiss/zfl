# update

`update` is a one-click system package updater for Arch Linux and Flatpak environments.

---

## 📖 Usage & Examples

```bash
update [options]
```

### Options
- `-h, --help`: Show help information and exit

### Examples
```bash
update         # Update system packages and Flatpak apps
```

---

## ⚙️ How it Works

1. Automatically checks for package managers in priority order:
   - If `yay` is installed, runs `yay -Syu` to update official repositories and AUR packages.
   - Otherwise, falls back to `sudo pacman -Syu`.
2. If `flatpak` is installed and has configured remotes (`flathub`), runs `flatpak update`.
3. Upon successful update, writes today's date (`YYYY-MM-DD`) to `~/.cache/zsh/UpdateFlag.lock`, resetting terminal startup reminders for the rest of the day.
