# Known Issues

Current known issues in the latest release. This page is updated with each release.

---

## v0.8.0 Known Issues

### Boss AI Not Implemented

**Severity:** Medium (feature gap, not a crash)

Boss rooms generate and bosses spawn, but they have no attack patterns or phase transitions. Boss missions can be "completed" by destroying the boss entity, but there is no actual boss encounter.

**Status:** Planned for a future update (Phase 8).

---

### Multiplayer: Minor Entity Desync

**Severity:** Low (cosmetic / non-blocking)

In multiplayer, enemy AI runs independently on each client, which can cause slight positional differences for enemies between clients. Pickup collection and enemy kills are now synced (v0.8.0), but AI movement divergence remains.

**Workaround:** LAN play minimises observable desync. Full server-authoritative AI is planned for Phase 3b.

---

### BGM / Music Not Implemented

**Severity:** Low

The game has SFX (12 events) but no background music. AudioManager supports BGM; music files and loop wiring are planned.

**Workaround:** Play your own music in the background.

---

### Gamepad Not Supported

**Severity:** Low

Keyboard only in v0.8.0. Gamepad support (pygame.joystick) is planned.

**Workaround:** Use a keyboard-to-gamepad mapper (e.g. JoyToKey, Steam Input).

---

## Reporting New Issues

If you find a bug not listed here, please report it at
[indie-ninja-feedback](https://github.com/VainAsher/indie-ninja-feedback/issues/new/choose).

Include your game version, OS, and steps to reproduce.
