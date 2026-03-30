# Changelog

Player-facing release notes for Indie Ninja Adventures.

For full technical details, see the [game repository changelog](https://github.com/VainAsher/indie-ninja-adventures/blob/main/docs/CHANGELOG.md).

---

## v0.8.0 — March 2026

### What's New

- **1–4 player multiplayer**: Full authoritative server. Host a game from the launcher and invite up to 3 friends.
- **Launcher v1.1.0**: New Report tab (submit bugs and feedback directly from the launcher) and Dev Tools tab (profiler, log viewer, replay launcher).
- **Entity sync**: Pickup collection and enemy kills now sync across all players in multiplayer.
- **Max players setting**: Choose 1–4 players when hosting.
- **New art assets**: Building, cave, and dungeon biome tilesets; shuriken projectile sprite.

### Fixed

- Remote players now render as ninja sprites with per-player colour tinting
- Lobby correctly shows the configured max players (was hardcoded to 4)
- Network logs now appear in the game's rotating log file

### Known Issues

- Boss AI not yet implemented (rooms generate but bosses don't attack)
- BGM/music not yet implemented
- Gamepad not supported

---

## v0.7.x — February–March 2026

### Highlights

- **Campaign mode**: 30 missions across 6 regions with story, dialogue, and ability gates
- **Enemy AI**: 5 enemy types with patrol, chase, ranged, and flying behaviours
- **Story system**: Multiple endings (Redemption / Hollow / Balance), NPC dialogue, cutscenes
- **Trading**: 3-tier shops, inventory, loot with rarity tiers
- **Save system**: JSON persistence with integrity checking
- **Audio SFX**: 12 SFX events (combat, movement, pickups, UI)
- **Multiplayer foundation**: Input relay, entity event sync, 4-player lobby, colored sprites
- **Replay system**: Input recording and deterministic playback

---

## v0.3.0 — December 2025

Initial public build.

- Modular event-driven engine
- Player mechanics: movement, jump (all types), dash, crouch, combat
- Procedural world generation (7 biomes, seed-based)
- Physics and collision system (AABB, 11+ edge case fixes)
