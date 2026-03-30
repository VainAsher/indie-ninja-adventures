# Multiplayer Guide

Indie Ninja Adventures supports 1–4 players online.

Multiplayer is authoritative-server based: one player hosts, others connect. The host's machine runs the game simulation.

---

## How to Host

1. Open the launcher
2. Click **Host Game**
3. Set the port (default: **7777**)
4. Set the maximum number of players (1–4)
5. Click **Launch**
6. Share your IP address with other players

For LAN games: share your local IP (e.g. `192.168.1.5`).
For internet games: share your public IP and ensure port 7777 is forwarded on your router.

---

## How to Join

1. Open the launcher
2. Click **Join Game**
3. Enter the host's IP address and port: `192.168.1.5:7777`
4. Click **Launch**

---

## Port Forwarding (Internet Play)

For players to connect from the internet (not LAN), the host must forward **port 7777 TCP** on their router to their PC's local IP.

Steps vary by router — search "port forwarding [your router model]" for instructions.

---

## Player Colours

Each player slot gets a unique colour:

| Slot | Colour |
|------|--------|
| 0 (Host) | Default ninja colours |
| 1 | Red |
| 2 | Green |
| 3 | Purple |

---

## Replay System

Sessions are recorded automatically. Replays are saved to `user_data/replays/`.

To replay a session:
1. Open the launcher
2. Go to **Dev Tools** tab
3. Click **Launch Replay** and select a replay file

Or from the command line:
```
ninja_dash.exe --replay path\to\session.json
```

Replays are deterministic — they replay exact inputs, not a video recording.

---

## Known Limitations (v0.8.0)

- Boss AI is not implemented — boss rooms exist but bosses don't attack
- LAN play recommended for best performance — internet play works but may have lag
- All players must use the same game version

---

## Troubleshooting

**Can't connect:**
- Check that the host has port 7777 open in Windows Firewall
- Confirm the IP address is correct
- Try LAN first to rule out routing issues

**Lag or desync:**
- Phase 3b (client prediction + lag compensation) is planned for a future update
- LAN play will always be smoother than internet play at this stage

**Game crashes on connect:**
- Check game version — all players must use the same version
- Check `user_data/logs/` for error details and report at [indie-ninja-feedback](https://github.com/VainAsher/indie-ninja-feedback/issues/new/choose)
