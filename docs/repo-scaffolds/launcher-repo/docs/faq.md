# FAQ

## Installation

**The launcher won't run — Windows says it's unsafe.**

This is Windows SmartScreen for unsigned executables. Click **More info** → **Run anyway**. The launcher is safe.

**The game doesn't download automatically.**

Check your internet connection. If the launcher shows an error, try running it as administrator. If it still fails, download `ninja_dash.exe` directly from the [releases page](https://github.com/VainAsher/indie-ninja-launcher/releases/latest) and place it in the same folder as the launcher.

**My antivirus flags the exe.**

PyInstaller-packaged executables sometimes trigger false positives. The source code is available in the game repository. If you're unsure, download the SHA256 checksum from the releases page and verify it manually.

---

## Gameplay

**How do I save my progress?**

Progress saves automatically after completing each mission. There is no manual save.

**Where is my save file?**

In the `user_data\saves\` folder next to the game exe. Or check `%APPDATA%\indie_ninja_adventures\saves\`.

**I'm stuck in a mission — how do I exit?**

Press `ESC` to pause, then select **Quit to Menu**. You'll restart the mission from the beginning next time.

**How do I unlock abilities?**

Complete missions in the Campaign to earn abilities. Some abilities are required to access later regions (ability gates on the hub portals).

**The boss room is empty.**

Boss AI is not yet implemented in v0.8.0. Boss rooms generate and the framework exists, but bosses don't have attack patterns yet. This is a known gap — see the [Known Issues](known-issues.md) page.

---

## Multiplayer

**How do I play with friends?**

Use the launcher's **Host Game** or **Join Game** buttons. See the [Multiplayer Guide](multiplayer.md).

**My friend can't connect to my hosted game.**

For LAN: make sure you're both on the same network and sharing the correct local IP.
For internet: you need to forward port 7777 TCP on your router.

**The game desyncs in multiplayer.**

Desync issues are known at this stage (Phase 3 networking). LAN play is recommended. Report persistent issues at [indie-ninja-feedback](https://github.com/VainAsher/indie-ninja-feedback).

---

## Performance

**The game runs at low FPS.**

The game targets 60 FPS. If you're seeing consistently low FPS, check the [Known Issues](known-issues.md) page. You can also report performance issues at [indie-ninja-feedback](https://github.com/VainAsher/indie-ninja-feedback).

**The game stutters in certain zones.**

Large zones with many enemies can cause brief stutters. This is being monitored. Report with your system specs and zone name.

---

## Replays

**Where are replays saved?**

`user_data\replays\` next to the game exe.

**How do I watch a replay?**

Use the **Dev Tools** tab in the launcher → **Launch Replay**, or run:
```
ninja_dash.exe --replay path\to\session.json
```
