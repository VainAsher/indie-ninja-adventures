# Indie Ninja Adventures — Launcher

**Vain Asher Gaming** | Download, launch, and stay updated automatically.

---

## Download

Get the latest launcher from [Releases](https://github.com/VainAsher/indie-ninja-launcher/releases/latest).

**`ninja_dash_launcher.exe`** — Windows standalone, no install required.

---

## What the Launcher Does

- Checks for game updates on startup and downloads the latest version
- Verifies the downloaded `.exe` with SHA256 before running
- Launch modes: Solo Play, Host a multiplayer game, Join a game
- Submit bug reports and feedback directly from the launcher
- Dev Tools: profiler benchmark, log viewer, replay launcher

---

## System Requirements

- Windows 10 or 11 (64-bit)
- No Python or additional software required
- Internet connection for update checks

---

## Quick Start

1. Download `ninja_dash_launcher.exe` from [Releases](https://github.com/VainAsher/indie-ninja-launcher/releases/latest)
2. Run it — Windows may show a SmartScreen warning (click "More info" → "Run anyway")
3. The launcher will download the game automatically on first run

See the **[Player Guide](docs/installation.md)** for full setup instructions.

---

## Player Guides

- [Installation Guide](docs/installation.md)
- [Controls Reference](docs/controls.md)
- [Gameplay Guide](docs/gameplay-guide.md)
- [Multiplayer Guide](docs/multiplayer.md)
- [FAQ](docs/faq.md)
- [Known Issues](docs/known-issues.md)
- [Changelog](docs/changelog.md)

---

## Reporting Issues

Found a bug? Use the **Report** tab in the launcher, or go to
[indie-ninja-feedback](https://github.com/VainAsher/indie-ninja-feedback/issues/new/choose).

---

## For Developers

The launcher source lives in the private game repo: `VainAsher/indie-ninja-adventures/launcher/launcher.py`.
This public repo distributes the compiled `.exe` only.

See [SETUP.md](SETUP.md) for one-time repo configuration.
