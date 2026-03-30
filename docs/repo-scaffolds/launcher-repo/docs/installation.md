# Installation Guide

## Download

1. Go to [Releases](https://github.com/VainAsher/indie-ninja-launcher/releases/latest)
2. Download `ninja_dash_launcher.exe`
3. Run it — no installation required

The launcher will automatically download the game on first run.

---

## Windows SmartScreen Warning

Windows may show a warning when you first run the launcher:

> "Windows protected your PC"

This is normal for unsigned executables. To proceed:

1. Click **More info**
2. Click **Run anyway**

The launcher and game are open-source and verified with SHA256 checksums.

---

## Verifying the Download (Optional)

For security-conscious users, you can verify the SHA256 checksum:

1. Download `ninja_dash_launcher.exe` and `ninja_dash.exe.sha256` from the release
2. Open PowerShell and run:

```powershell
$hash = (Get-FileHash ninja_dash.exe -Algorithm SHA256).Hash.ToLower()
$expected = (Get-Content ninja_dash.exe.sha256).Split(' ')[0]
if ($hash -eq $expected) { "Verified OK" } else { "MISMATCH - do not run" }
```

---

## Firewall / Antivirus

For **multiplayer**, the game needs network access:

- Allow `ninja_dash.exe` through Windows Firewall when prompted
- If playing over the internet (not LAN), the host needs to forward port **7777 TCP** on their router

---

## System Requirements

| Component | Minimum |
|-----------|---------|
| OS | Windows 10 (64-bit) |
| CPU | Intel i3 / AMD equivalent |
| RAM | 4 GB |
| Storage | 200 MB |
| Network | Required for multiplayer only |

---

## Updating

The launcher checks for updates automatically on startup. Click **Update** when prompted.

If the launcher itself needs updating, download the latest `ninja_dash_launcher.exe` from the releases page.

---

## File Locations

| File | Location |
|------|----------|
| Game saves | `%APPDATA%\indie_ninja_adventures\saves\` or next to the .exe in `user_data\saves\` |
| Logs | `user_data\logs\` |
| Replays | `user_data\replays\` |
| Settings | `user_data\settings\` |
