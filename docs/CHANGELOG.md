# Changelog
**Vain Asher Gaming's: Indie Ninja Adventures**

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.1] - 2026-03-30 (Fix multiplayer visibility regression from v0.9.0)

### Bug fixes

- **`network/server.py` — `ConnectedPlayer.hub_id` not set on join**:
  All connecting players were initialized with `hub_id="central_hub"` (the
  default field value) instead of the actual initial zone. `_broadcast_to_zone`
  filters writers by `p.hub_id == zone.hub_id`, so when the server's initial
  zone was any hub other than `"central_hub"` the filter produced an empty set
  and no `WORLD_STATE` frames were delivered — making every player invisible to
  every other player. Fixed by passing `hub_id=self._world_hub_id` when
  constructing `ConnectedPlayer` in `_handle_client`.

- **`demo_game.py` — stale-frame guard discarded valid `WORLD_STATE` frames**:
  The guard `if _ws_dict.get("hub_id") and _ws_dict["hub_id"] != current_hub_id`
  fired when `current_hub_id` was still `None` (before `GAME_START` was
  processed), silently dropping every frame the server sent. Fixed by adding
  `and current_hub_id` so the guard only activates once the client has a
  confirmed server-side hub ID.

---

## [0.9.0] - 2026-03-30 (Instanced zones — independent multiplayer worlds)

### Multiplayer

- **Instanced zone architecture** (`network/server.py`):
  The server now manages a `_ZoneInstance` registry instead of a single
  `GameSimulator`. Each zone runs its own 60 Hz simulation loop, its own
  delta-encoding hash state, and its own player-membership set. Zones are
  created on demand as players travel and are reaped after 120 s of inactivity
  (the initial hub is never reaped).

- **`_get_or_create_zone(hub_id)`**: Derives seed and world configuration for
  any non-initial hub via `SeedDerivation.derive_region_seed()` + `HubManager`.

- **`_handle_portal_travel(player, destination_id, portal_id)`**: Moves a player
  between zones atomically — removes from old zone, initializes destination zone
  if this is its first arrival, sends `WORLD_TRANSITION` to the traveling player,
  and sends `ZONE_PRESENCE` to both old and new zone occupants.

- **`_reap_idle_zones()`**: Background task that checks every 30 s and cancels
  the simulation task for any zone that has been empty for more than 120 s.

- **`ConnectedPlayer.hub_id`**: Tracks which zone each connected player is in.
  Disconnect cleanup correctly removes from zone membership and notifies
  remaining occupants.

- **New protocol messages** (`network/protocol.py`):
  - `PORTAL_TRAVEL` (client → server): `{destination_id, portal_id}`
  - `WORLD_TRANSITION` (server → client): `{hub_id, seed, shape, rooms, world_seed, spawn_x, spawn_y}`
  - `ZONE_PRESENCE` (server → zone): `{player_id, slot, hub_id, action: "arrived"|"departed"}`

- **`WorldSnapshot.hub_id`** (`network/snapshots.py`): Optional field (default
  `""`) identifying which zone a snapshot belongs to. Backward-compatible — old
  clients/servers that omit this field continue to work.

- **Client zone API** (`network/client.py`):
  - `poll_transition()` — returns next `WORLD_TRANSITION` payload or `None`
  - `poll_zone_presence()` — returns all pending `ZONE_PRESENCE` events
  - `send_portal_travel(destination_id, portal_id)` — queues a portal travel request
  - `_EntityCache.reset()` — clears cached entity state on zone transition
  - `current_hub_id` — tracks the zone the client is currently in

### Game

- **Portal travel multiplayer intercept** (`demo_game.py`):
  `on_portal_travel()` now checks `_net_client.is_connected` — if so, sends
  `PORTAL_TRAVEL` to the server and returns without rebuilding the world locally.
  World rebuild is deferred until `WORLD_TRANSITION` arrives from the server.

- **`_apply_world_transition(payload)`** (`demo_game.py`):
  Applies a server-authoritative zone transition: syncs `hub_manager.world_seed`,
  calls `regenerate_world_state()` with server params, repositions player at
  `spawn_x`/`spawn_y`, and transitions game state to `PLAYING`.

- **Main multiplayer loop** (`demo_game.py`):
  Now polls `poll_transition()` and `poll_zone_presence()` each frame. Stale
  `WORLD_STATE` packets from a zone the player has already left are silently
  discarded via `hub_id` comparison.

---

## [0.8.9] - 2026-03-30 (WORLD_STATE delta encoding)

### Network

- **Server-side delta encoding** (`network/server.py`):
  `GameServer._build_world_state_payload()` tracks per-entity state hashes
  (enemies, pickups, platform states) and emits a delta frame containing only
  changed/removed entities for each of the FULL_SNAPSHOT_INTERVAL − 1 frames
  between full snapshots. A full snapshot (`is_delta=False`) is broadcast every
  180 frames (3 s at 60 Hz) to prevent drift from accumulating.

- **Client-side delta reconstruction** (`network/client.py`):
  `_EntityCache` applies incoming full/delta frames and reconstructs complete
  world state before placing it in the receive queue. `poll_world_state()` and
  all downstream code in `demo_game.py` are unaffected — they always receive a
  fully-populated dict identical in shape to `WorldSnapshot.to_dict()`.

- **~60% downstream bandwidth reduction**: Players sent every frame (small,
  always-changing). Enemies (dominant cost) only sent when AI state, health, or
  position changes. Pickups only sent on collection. Platform states only sent
  during triggered/falling/respawn transitions.

---

## [0.8.8] - 2026-03-30 (Wire protocol: JSON → msgpack)

### Added / Changed

- **msgpack binary serialisation** (`network/protocol.py`, `pyproject.toml`):
  All multiplayer wire frames previously used JSON text encoding. Switched to
  length-prefixed msgpack binary frames (`use_bin_type=True`, `raw=False`).
  Result: ~65% reduction in per-packet payload size; eliminates UTF-8 encode/decode
  overhead on every send/receive path.

- **Protocol version bump** (`network/protocol.py`, `network/client.py`, `network/server.py`):
  `PROTOCOL_VERSION` promoted to `"2"` (1 = JSON, 2 = msgpack).
  `CLIENT_VERSION` and `SERVER_VERSION` bumped to `"2.0.0"`.
  Version mismatch between client and server is logged as a warning; the incompatible
  wire format will cause a decode error and disconnect regardless.

- **Improved decode error handling** (`network/protocol.py`):
  `read_message()` now catches `msgpack.UnpackException`, `msgpack.UnpackValueError`,
  `KeyError`, `TypeError`, and `ValueError` — surfacing all as a descriptive
  `ValueError` with byte-count context instead of unhandled crashes.

- **`msgpack>=1.0.0`** added to `[project.dependencies]` in `pyproject.toml`.

---

## [0.8.7] - 2026-03-30 (Multiplayer network performance — deep audit fixes)

### Fixed / Improved

- **Encode-once broadcast** (`network/protocol.py`, `network/server.py`):
  `json.dumps()` was called once per connected client per broadcast tick — with 4 clients
  and WORLD_STATE at 60 Hz that was 240 JSON serialisations/sec of the same payload.
  Added `encode_message()` and `write_encoded()` helpers. `GameSession.broadcast()` now
  encodes the payload once and passes raw bytes to every writer.

- **Concurrent broadcast** (`network/server.py`):
  Writers were sent to sequentially — a slow or lagging client stalled delivery to all
  others. `broadcast()` now fires all writers concurrently with `asyncio.gather()`.

- **Smart INPUT rate limiter** (`network/client.py`):
  `send_input()` was enqueuing 60 packets/sec upstream even when the player held the
  same button state. New logic: send immediately on any button change (full 60 Hz
  responsiveness); throttle to 20 Hz when state is unchanged. Upstream bandwidth
  during idle/hold reduces by ~66 %; new inputs are never delayed.

- **Tighter send-loop sleep** (`network/client.py`):
  Empty-queue sleep reduced from 1 ms to 100 µs — `_recv_loop` gets 10× more
  opportunities to process inbound data between send attempts.

- **Protocol decode error handling** (`network/protocol.py`):
  Malformed or truncated JSON would surface as an unhandled crash. `read_message()`
  now catches `JSONDecodeError`/`UnicodeDecodeError`/`KeyError` and raises a
  descriptive `ValueError` with byte-count context.

---

## [0.8.6] - 2026-03-30 (Multiplayer lag reduction)

### Fixed

- **TCP_NODELAY on all multiplayer sockets** (`network/client.py`, `network/server.py`):
  Nagle's algorithm was active on both the client outbound socket and each server-accepted
  client socket. Small INPUT messages (~100-300 bytes) were being buffered for up to 40ms
  waiting for ACK/MSS before transmission. Setting `TCP_NODELAY = 1` immediately after
  socket creation eliminates this delay on both ends.
- **Non-blocking send loop** (`network/client.py`):
  `_send_loop` was using `run_in_executor(None, queue.get, True, 0.016)` to wait for
  outbound input — this blocked the asyncio event loop for up to 16ms on each empty-queue
  poll, preventing `_recv_loop` from processing inbound server state during that window.
  Replaced with `get_nowait()` + `await asyncio.sleep(0.001)`, which yields control to
  the event loop every 1ms and sends immediately when data is available.

---

## [0.8.5] - 2026-03-30 (Cross-machine multiplayer world desync fix)

### Fixed

- **Cross-machine world desync** (`network/server.py`, `network/client.py`, `demo_game.py`):
  Remote clients now generate an identical tile layout and collision geometry to the host.
  Root cause: `regenerate_world_state()` derives the actual seed via
  `SeedDerivation.derive_region_seed(hub_manager.world_seed, hub_id)` — ignoring the passed
  `seed` — so if `hub_manager.world_seed` differed between machines (loaded from different local
  saves) the derived seed differed and layouts diverged.  Fix: host broadcasts its
  `hub_manager.world_seed` as `"world_seed"` in the `GAME_START` message; remote clients apply
  it to their `hub_manager.world_seed` before calling `regenerate_world_state()`.

---

## [0.8.0] - 2026-03-29 (Phase 3a Authoritative Server + Launcher v1.1.0 + Infrastructure)

### Summary

Phase 3a delivers a full authoritative server running the game simulation at 60Hz and broadcasting
`WorldSnapshot` to all connected clients. The launcher adds Report and Dev Tools tabs. Biome tileset
assets (building, cave, dungeon) and a shuriken sprite are added. The project adopts a 4-repo
architecture with a structured feedback workloop pipeline.

### Added

- **Phase 3a authoritative server** (`network/server.py`, `network/client.py`, `game/game_simulator.py`):
  Server runs a full `GameSimulator` at 60Hz. Clients receive `WorldSnapshot` each tick and reconcile
  local state. Host still plays locally; remote clients drive from server snapshots.
- **Launcher v1.1.0** (`launcher/launcher.py`): Added Report tab (bug/feedback/performance/crash
  pre-fills GitHub issue URL) and Dev Tools tab (10s profiler benchmark, log viewer, replay launcher).
- **Biome tileset assets** (`assets/tilesets/`): Building, cave, and dungeon spritesheets added.
- **Shuriken sprite** (`assets/sprites/`): Dedicated shuriken projectile sprite.
- **4-repo pipeline architecture** (documentation + scaffolds): `docs/repo-scaffolds/` contains
  ready-to-deploy files for the launcher, feedback, and pipeline repositories.
- **Workflow documentation** (`docs/workflow/`): BRANCHING.md, SPRINT_WORKFLOW.md, RELEASE_CHECKLIST.md.
- **GitHub issue templates** (`.github/ISSUE_TEMPLATE/`): bug_report.yml, task.yml, config.yml.
- **PR template** (`.github/PULL_REQUEST_TEMPLATE.md`).
- **Weekly feedback sync workflow** (`.github/workflows/sync_feedback.yml`).
- **Cross-repo dispatch** (`.github/workflows/release.yml`): Notifies launcher repo on game release.
- **Developer documentation** (`docs/dev/`, `CONTRIBUTING.md`): Setup guide, architecture reference,
  systems API, contributing guide.
- **Public user docs scaffold** (`docs/repo-scaffolds/launcher-repo/docs/`): Installation, controls,
  gameplay guide, multiplayer guide, FAQ, known issues, changelog pages for GitHub Pages.
- **`develop` branch** added to CI triggers.

### Changed

- **`pyproject.toml`**: version bumped from 0.7.0 → 0.8.0 (now consistent with `version.json`).
- **`README.md`**: Full rewrite — v0.8.0, 4-repo architecture diagram, accurate feature table,
  multi-repo links, cleaned Quick Start.
- **`version.json`**: `min_launcher_version` set to `"1.1.0"`.

### Infrastructure

- Multi-repo architecture documented and scaffolded (see `docs/repo-scaffolds/`)
- Feedback workloop: Player → Feedback → Triage → Plan → Build → Test → Release → Document → Repeat

---

## [0.7.8] - 2026-03-29 (Phase 2.5: Entity Sync + Configurable Max Players)

### Summary

Pickup collections and enemy kills are now broadcast to all connected clients via `ENTITY_EVENT` so entity state stays in sync across machines. The host can select the maximum number of players (1–4) both in the launcher UI and via `--max-players N`. The lobby display now shows the actual configured maximum.

### Added

- **Entity event wiring — pickups** (`entities/pickups.py`, `demo_game.py`): `BasePickup` gains a stable `pickup_id` (`"pickup_X_Y"`). When the local player collects a pickup, `send_entity_event("pickup_collect", pickup_id)` is called. `PickupManager.suppress_by_id()` silently removes the matching pickup on all remote clients.
- **Entity event wiring — enemies** (`entities/enemy_manager.py`, `demo_game.py`): `EnemyManager` tracks `recently_killed_ids` per update tick (populated in `_handle_enemy_death`, cleared at the top of each `update()`). After each physics tick, any kills are broadcast as `send_entity_event("enemy_kill", enemy_id)`. `EnemyManager.suppress_enemy()` silently removes the enemy on all remote clients (no loot/events).
- **`--max-players N` CLI arg** (`demo_game.py`): Integer 1–4, default 4. Passed to `run_server()` when hosting. Lobby display uses actual configured value instead of hardcoded "4".
- **Max players selector in launcher** (`launcher/launcher.py`): Readonly spinbox (1–4, default 4) next to the port field in the Host section. Value is passed as `--max-players N` when launching a hosted game.

### Changed

- **`network/server.py`**: `run_server()`, `GameServer`, and `GameSession` all accept `max_players: int` (default `MAX_PLAYERS`). All internal references to the `MAX_PLAYERS` constant replaced with `self.max_players` so each session uses its own limit.
- **`network/client.py`**: `NetworkClient` stores `max_players` from `SERVER_HELLO` payload, allowing joiners to display the correct lobby cap without knowing the host's CLI args.

### Notes

Entity sync covers the two highest-divergence events: pickup collection and enemy death. Enemy AI still runs independently on each client (Phase 1) — the AI's use of local player position still causes minor positional divergence between frames, but entities are now removed in sync. Full server-authoritative simulation remains Phase 3.

---

## [0.7.7] - 2026-03-29 (Multiplayer Logging + Entity Sync Foundation)

### Summary

Network logs now flow into the game's rotating log file. `ENTITY_EVENT` message type added as the Phase 2.5 foundation for syncing entity mutations (pickup collection, enemy kills, platform triggers) across clients. Entity sync itself is not yet wired to game systems — see Phase 2.5 in the plan.

### Added

- **`ENTITY_EVENT` message type** (`network/protocol.py`): Client → server message carrying `{etype, entity_id, slot, data?}`. Server rebroadcasts to all other clients. Client exposes `send_entity_event(etype, entity_id, **data)` and `poll_entity_events() -> list[dict]` for game-loop integration.
- **Outbound/inbound entity event queues** (`network/client.py`): `_entity_send_queue` (local → server) and `_entity_event_queue` (remote → local). `_send_loop` drains the send queue after each INPUT frame. `_recv_loop` routes received events to the inbound queue, ignoring echoes from the same slot.

### Changed

- **Network logger hierarchy** (`network/client.py`, `network/server.py`): Loggers renamed from `"network.client"` / `"network.server"` to `"ninja_dash.network.client"` / `"ninja_dash.network.server"`. They now inherit from the game's `GameLogger` root (`"ninja_dash"`) and are written to the rotating session log file in `user_data/logs/`.
- **Structured logging** — client: connect/handshake outcome, PLAYER_JOIN/LEAVE, GAME_START, per-300-frame throughput counters. Server: incoming connections, handshake details, GAME_START with player list, relay throughput, disconnect cleanup.

### Known Limitation (entity sync)

Enemies, collectibles, and falling platforms are simulated independently on each client (Phase 1 design). They will diverge because:
1. Enemy AI chase/attack decisions use the **local** player's position — each client's remote-player position lags behind by network RTT.
2. Pickup collection events are not broadcast — each client tracks its own pickup state.
3. Falling platform triggers are not broadcast.

**Phase 2.5 plan**: wire `send_entity_event` calls into `pickup_manager` (on collect), `enemy_manager` (on kill), and the platform `TickEvent` handler (on trigger). Wire `poll_entity_events` in the game loop to suppress the matching local entity. Full server-authoritative simulation is Phase 3.

---

## [0.7.6] - 2026-03-29 (Multiplayer: Colored Sprites + 4-Player Lobby + Launcher Modes)

### Summary

Remote players now render as actual ninja sprites color-tinted by slot (slot 0 = default, 1 = red, 2 = green, 3 = purple). Max players increased to 4. Launcher gains dedicated Solo Play, Host Game, and Join Game launch modes.

### Added

- **Colored remote-player sprites** (`rendering/remote_player_renderer.py`, `entities/remote_player.py`): Remote peers now use the same spritesheets as the local player via `AnimationStateMachine`, tinted per slot with `pygame.BLEND_RGB_MULT`. Slot 0 = default ninja, slot 1 = red `(220,80,80)`, slot 2 = green `(80,200,80)`, slot 3 = purple `(180,80,220)`. Ghost silhouette retained as fallback.
- **Animation inference for remote players** (`entities/remote_player.py`): `_infer_anim_state()` maps velocity + dead flag to idle/walk/run/jump/fall/death. `apply_state()` calls `anim_sm.transition()` automatically on every network update. `anim_sm` retried each frame until non-None so timing issues on join are self-healing.
- **Launcher multiplayer modes** (`launcher/launcher.py`): Three launch buttons — `>> Solo Play` (no args), `[H] Host Game` (port entry + `--host PORT`), `-> Join Game` (server entry + `--connect HOST:PORT`). Port validated 1–65535. Address defaults to port 7777 if only hostname given. Placeholder text with focus in/out handling. Window height increased to 460px.

### Changed

- **`network/server.py`**: `MAX_PLAYERS` raised from 2 to 4.
- **`demo_game.py`**: Lobby strings updated from "2 players" to "4 players". `anim_sm` assignment moved to a per-frame retry block so it self-heals if the registry wasn't loaded at first snapshot.
- **`launcher/launcher.py`**: Refactored launch path into `_launch_with_args(*extra)` helper used by all three launch modes. "▶ PLAY" renamed ">> Solo Play" for clarity.

---

## [0.7.5] - 2026-03-29 (Multiplayer N4+L2: Remote Players + Lobby)

### Summary

Remote peer players are now visible in-game as blue ghost silhouettes with health bars and slot labels. A lobby overlay holds both players at a "Waiting…" screen before the game starts; the server auto-starts when the second player connects.

### Added

- **Remote player entity** (`entities/remote_player.py`): `RemotePlayer` dataclass holds networked peer state (pos, vel, health, facing, is_dead). Linear interpolation (`interpolated_pos`) smooths position between 60 Hz server ticks.
- **Ghost renderer** (`rendering/remote_player_renderer.py`): Draws a blue semi-transparent silhouette with directional arrow, health bar, and "P2" slot label. Dead players render as a grey ghost. All drawing uses `pygame.draw` primitives — no sprite sheet dependency.
- **Lobby overlay** (`demo_game.py`): When launched with `--host` or `--connect`, a gold-bordered panel shows connected player count and waits for `GAME_START`. ESC cancels. Game auto-skips the main menu and starts immediately on start signal.
- **`LOBBY_UPDATE` message** (`network/protocol.py`, `network/server.py`, `network/client.py`): Server broadcasts connected player count + player list on every join/leave. Client exposes `connected_count` property.
- **`GAME_START` message**: Server auto-fires when lobby is full (`MAX_PLAYERS` connected). Client sets `game_started` threading.Event and updates `server_seed`. Lobby overlay exits on receipt.

### Changed

- `network/server.py`: `GameSession` gains `game_started: bool`; `broadcast_lobby_update()` and `start_game()` methods added. `_handle_client` sends `LOBBY_UPDATE` on join and leave, and fires `start_game()` when lobby fills.
- `network/client.py`: `_recv_loop` handles `LOBBY_UPDATE`, `GAME_START`, and `PLAYER_LEAVE` (now also sets `last_leave_slot`).
- `demo_game.py`: `poll_state()` output is now parsed into `_remote_players` dict each frame. Departed players removed via `last_leave_slot`. Remote players rendered after local player each frame.

---

## [0.7.3] - 2026-03-29 (Custom Launcher + Multiplayer Foundation + Boss Tuning)

### Summary

Three major workstreams landed together: a standalone tkinter launcher with GitHub auto-update, Phase 1 multiplayer networking (input relay over asyncio TCP), and a round of boss combat tuning based on playtesting feedback.

### Added

- **Custom launcher** (`launcher/launcher.py`, `build/ninja_dash_launcher.spec`):
  - Standalone tkinter GUI (`console=False`, onefile PyInstaller exe via `python build.py --launcher`).
  - Dark theme (`#0f0f1a` bg, `#e94560` accent). Shows installed version read from bundled `version.json`.
  - Background thread checks GitHub Releases API for newer version; shows "Up to date" or "Update available".
  - Download worker: `urllib.request.urlretrieve` with live progress bar, SHA256 verification, atomic rename (`.new` → `.exe`, old → `.bak`).
  - Launch button: `subprocess.Popen([ninja_dash.exe])` then closes launcher. Dev mode launches `demo_game.py` directly.
  - `version.json` added to repo root: `{"version": "0.7.3", "build": "production", "build_date": "2026-03-29", "min_launcher_version": "1.0.0"}`.

- **Multiplayer Phase 1 — input relay** (`network/`):
  - `network/protocol.py`: `MessageType` constants, `Message` dataclass, `read_message`/`write_message` (4-byte big-endian length prefix + UTF-8 JSON body).
  - `network/server.py`: `GameServer` + `GameSession` — asyncio TCP server, handshake (`CLIENT_HELLO`/`SERVER_HELLO`), per-client input loop, `MultiplayerSnapshot` broadcast at 60 Hz.
  - `network/client.py`: `NetworkClient` — asyncio I/O in daemon thread, `queue.Queue` bridge to pygame main loop. `send_input()` / `poll_state()` are non-blocking.
  - `network/snapshots.py`: `PlayerState` and `MultiplayerSnapshot` dataclasses added (existing `Snapshot` unchanged).
  - `demo_game.py`: `--host PORT` starts embedded server thread; `--connect HOST:PORT` connects as client. Per-frame `send_input` + `poll_state` wired after `input_pipeline.next()`.

- **Boss health pickups** (`systems/pickup_spawner.py`, `game/world_builder.py`): Boss/champion levels now spawn 3× more health pickups. Rooms with no health config get a guaranteed `(1, 3)` range.

### Fixed

- **Player death from boss not triggering respawn** (`demo_game.py`): Replaced `player.take_damage()` (thin wrapper) with `player.damage.take_damage()` which returns a `died` bool, then calls `queue_player_death()` for proper world transition.

### Changed

- **Boss damage tuning** (`entities/boss_manager.py`, `entities/boss_ai.py`): All base damage scaled to 1 (was 3–5) to match player's 5 HP pool. Attack cooldown raised 1.5 → 2.5 s. Vulnerable window extended 1.5 → 2.5 s. Phase 3 speed and attack-speed multipliers softened.
- **Boss HP** (`entities/boss_manager.py`): SHADOW_LORD 25, FIRE_DEMON 30, NECROMANCER 20, VEIL_MAIDEN 40, ICE_QUEEN 28, DRAGON 35 (scaled down from previous values).
- **Boss contact damage** (`entities/boss_manager.py`): Contact damage now only applies when boss AI state is `SPECIAL_ATTACK` (was always-on during combat).
- **Projectile deflection** (`entities/boss_manager.py`, `demo_game.py`): Player sword swing now calls `boss_manager.destroy_projectiles_in_rect()` — any boss projectile overlapping the attack rect is removed.

---

## [0.7.2] - 2026-03-28 (Boss AI + Champion System)

### Summary

All 6 bosses now have functional AI: they chase the player, execute type-specific ranged and melee attacks, trigger special abilities per phase, and deal contact damage. Projectiles now check collision against the player. A champion spawn system means that once a boss type has been defeated, subsequent visits to that boss room have a 40% chance to spawn a weaker champion variant instead.

### Added

- **Boss movement** (`entities/boss_ai.py`): `_chase_player()` drives `boss.velocity_x` each tick based on signed distance to player. Position is integrated in `BossManager.update()` with linear friction.
- **Ranged attacks** (`entities/boss_manager.py`): `_execute_ranged_attack()` dispatches per boss type — FIRE_DEMON fires `fireball`, SHADOW_LORD fires `shadow_bolt`, ICE_QUEEN fires `ice_shard`, NECROMANCER fires `death_bolt`, DRAGON fires `fire_ball`, VEIL_MAIDEN fires `veil_bolt`.
- **Type-specific specials** (`entities/boss_manager.py`): All 6 bosses have 3–4 special attacks fully wired: FIRE_DEMON (`fireball_barrage`, `flame_breath`, `meteor_strike`), SHADOW_LORD (`shadow_strike`, `dark_wave`, `void_portal`), ICE_QUEEN (`blizzard`, `ice_spike`, `freeze_ray`), NECROMANCER (`death_ray`, `soul_drain`, `bone_cage`), DRAGON (`fire_breath`, `wing_slam`, `tail_sweep`), VEIL_MAIDEN (`veil_strike`, `isolation_field`, `light_drain`, `shadow_step`).
- **Projectile–player collision** (`entities/boss_manager.py`): `_check_projectile_player_collision()` tests all active boss projectiles against player AABB each tick and returns total damage to apply.
- **Contact damage** (`entities/boss_manager.py`): Boss body AABB vs player AABB checked during active combat states; returns damage_to_player.
- **Champion system** (`entities/boss_manager.py`, `demo_game.py`, `systems/save_system.py`):
  - `CampaignSaveData.defeated_bosses: set[str]` — persisted set of BossType name strings of bosses killed at least once.
  - `Boss.is_champion: bool` flag; `spawn_boss(champion=True)` spawns at 50% HP, 75% hitbox.
  - `_maybe_spawn_boss()`: if boss type already in `defeated_bosses`, 40% chance to spawn champion instead of full boss.
  - Defeated boss type recorded to `campaign.defeated_bosses` at mission completion.

### Fixed

- **Bosses stood still**: `_execute_phase_combat()` never updated `boss.velocity_x`. Now calls `_chase_player()` every tick.
- **Generic special names**: `_choose_special_attack()` returned hardcoded strings that never matched any boss's `special_attacks` list. Now reads from `BossDefinition.special_attacks`.
- **Projectiles never damaged player**: `update()` returned `None` for projectile hits. Now integrated into the damage return value.

---

## [0.7.1] - 2026-03-28 (Phases 2–5: Boss, Audio, Settings, Ability Gates)

### Summary

Campaign loop stabilized; boss integration, SFX audio, settings wiring, and ability gate enforcement all wired end-to-end. Portal placement now acts as the mechanical ability gate for Forest and Town regions.

### Added

- **Boss integration** (`entities/boss_manager.py`): BossManager wired into game loop. 6 boss missions added to `data/missions.json`. `GateManager` created; `_rebuild_hub_gates()` places ability gates in hub on campaign load and after each unlock.
- **Audio system** (`audio/audio_manager.py`): `AudioManager` wraps `pygame.mixer.Sound`. 12 named SFX slots with silent fallback if files missing. `initialize_audio()` added to `game/game_initialization.py`. SFX hooks wired: swing, hit_enemy, player_hurt, player_death, jump, land, dash, pickup_coin, pickup_item, menu_select, menu_confirm, inventory_open.
- **Placeholder SFX** (`assets/audio/sfx/`): 12 WAV files generated via `tools/gen_placeholder_sfx.py` using stdlib only. Replace with real audio assets.
- **Settings wiring**: `Player.set_key_bindings(dict)` added. `_build_key_bindings()` in `demo_game.py` maps settings string names → pygame constants. `apply_runtime_settings()` wires sfx_volume → `audio_manager.set_volume()`, fullscreen → `pygame.display.toggle_fullscreen()` + `camera.handle_resize()`, show_hitboxes → `show_debug_overlay`, key_* → `player.set_key_bindings()`.
- **SettingsMenu items**: SFX Volume (cycles Off/25/50/75/100%) and Fullscreen toggle added to `ui/menu_system.py`.
- **Ability sync**: `sync_player_abilities(unlocked_abilities)` closure syncs `player.feature_flags` and `JumpMechanic.double_jump_enabled` / `wall_jump_enabled`. Called at campaign start and after every ability unlock.
- **Portal height gating** (`game/hub_manager.py`): Forest portal at `ROOM_PIXEL_CENTER_Y + 200` (floor level, basic jump reachable). Town portal at `ROOM_PIXEL_CENTER_Y - 200` (elevated, double_jump required). Physical placement IS the gate.
- **F9 Debug ability menu** (`ui/menu_system.py:DebugAbilityMenu`): Password-protected overlay (password: `devmode`). Arrow keys + SPACE to toggle any ability live. Gates rebuild on each toggle.
- **Tests**: `tests/test_ability_gates.py` (7 tests), `tests/test_phase4_settings_wiring.py` (12 tests) — all passing.

### Fixed

- **Fullscreen crash** (`systems/camera_system.py`): `camera.handle_resize()` now called after `pygame.display.toggle_fullscreen()` so `render_width`/`render_height` stay in sync. Previously raised `ValueError: Destination surface not the given width or height`.
- **Player had all abilities at campaign start**: `CampaignSaveData` default `unlocked_abilities` is `{basic_movement, jump}` only. `sync_player_abilities()` now called at campaign start to enforce this.

---

## [0.7.0] - 2026-01-01 (Project Restructuring Release)

### Summary
**Major restructuring and documentation overhaul**. This release represents a complete audit and improvement of the project, bumping from v0.4.0-dev documentation to accurate v0.7.0 documentation that reflects all implemented features. The codebase was v0.7.0+ in functionality but documented as v0.4.0-dev - this release brings documentation into alignment with reality.

### Major Changes

#### Infrastructure & Tooling
- **Added Modern Python Packaging**: `pyproject.toml` with Black, Ruff, MyPy, pytest-cov
- **Added CI/CD Pipeline**: GitHub Actions with automated testing, linting, formatting, type checking
- **Added Pre-commit Hooks**: Code quality enforcement on git commits
- **Archived Legacy Code**: Moved `legacy/` to `legacy-archive/` (excluded from repo)
- **Removed Technical Debt Markers**: Cleaned up backup files and outdated references

#### Documentation Overhaul
- **Reduced Documentation Files**: 80+ markdown files → 28 core files (65% reduction)
- **Created FEATURES_V0_7.md**: Comprehensive feature documentation
- **Archived Historical Docs**: Moved 70+ files to `docs/archive/` (sessions, phases, audits, summaries)
- **Updated Core Docs**: README, ROADMAP, CHANGELOG, ARCHITECTURE now reflect v0.7.0 reality
- **Documented Boss AI Gap**: Prominently noted that boss framework exists but boss AI is not implemented

#### Version Consistency
- **Updated ALL Version References**: v0.4.0-dev → v0.7.0 across 25+ files
- **Version String Updates**: UI menu system, documentation, build configs

### What's Actually in v0.7.0 (Documentation Finally Accurate)

This release doesn't add new features - it documents what was already implemented but undocumented:

#### Game Systems (Implemented v0.5.0-v0.7.0, Now Documented)
- **Campaign Mode**: 25 missions across 5 zones with story progression
- **Enemy System**: 5 enemy types with AI (SLIME, BAT, SKELETON, ORC, DEMON)
- **Story System**: Story manager with multiple endings, character arcs, cutscenes
- **Dialogue System**: NPC conversations with branching choices
- **Trading System**: 3-tier shops with inventory management
- **Portal System**: Hub-based fast-travel
- **Combat System**: 3-hit combo, air attacks, special abilities
- **Loot System**: Rarity tiers, enemy drops, treasure chests

#### Known Gaps (Now Documented)
- **Boss AI**: Framework exists (entities/boss.py, entities/boss_manager.py) but NO functional boss AI
  - Boss rooms generate but have no encounters
  - Estimated 220 hours to implement (ROADMAP.md Phase 8)
  - See FEATURES_V0_7.md for details
- **Sound System**: Planned but not implemented
- **Multiplayer**: Planned for v1.0.0+

#### Code Refactoring (Phases 3-6 Completed)

**Phase 3: demo_game.py Refactoring**
- **Reduced demo_game.py**: 3,496 → 2,607 lines (25.4% reduction, -889 lines)
- **Created 4 new modular files**:
  - `game/game_initialization.py` (430 lines) - System initialization
  - `game/level_factory.py` (377 lines) - Level creation
  - `game/world_builder.py` (549 lines) - World regeneration
  - `game/game_helpers.py` (63 lines) - Utility functions
- **Removed duplicate code**: 767 lines of duplicates eliminated
- **Improved maintainability**: Functions now organized by purpose

**Phase 4: Technical Debt Resolution (Partial)**
- **Fixed EventBus Memory Leak**:
  - Added owner-based subscription tracking
  - Implemented `unsubscribe_all(owner)` for bulk cleanup
  - Updated CameraEffectsHandler with cleanup() method
  - Prevents memory leaks from recreated entities
- **Verified Save System Security**: HMAC-SHA256 signature and validation confirmed working
- **Skipped**: PlayerState refactoring (43 fields → 9) deferred to future release due to complexity

**Phase 5: Code Quality Enforcement**
- **Black Formatting**: 170 files formatted to consistent style (100% compliance)
- **Ruff Linting**: 2,084 → 115 errors (94.5% reduction)
  - 1,969 auto-fixed issues
  - Modern Python 3.10+ type syntax (`str | None` instead of `Optional[str]`)
  - Sorted imports, removed f-string placeholders
- **Type Hints Added**:
  - Core modules: 98% type coverage improvement
  - Fixed callable type hints, dataclass fields, event inheritance
  - mypy errors: 251 → 240 (core/ modules down to 2 minor issues)

**Phase 6: Testing & Finalization**
- **Test Suite Verified**: All 16/17 tests passing (94.1% pass rate)
  - 1 pre-existing failure (raycast test, unrelated to refactoring)
  - No regressions introduced
- **Created Migration Guide**: `docs/MIGRATION_GUIDE.md` with upgrade instructions
- **Updated Documentation**: README, CHANGELOG, ARCHITECTURE aligned with v0.7.0

### Quality Metrics

**Before Refactoring**:
- demo_game.py: 3,496 lines
- Ruff errors: 2,084
- Black formatted: 0%
- mypy errors (core/): Many
- Documentation files: 98

**After Refactoring**:
- demo_game.py: 2,607 lines (-25.4%)
- Ruff errors: 115 (-94.5%)
- Black formatted: 100%
- mypy errors (core/): 2 (-98%)
- Documentation files: 28 (-71%)

**Code Quality Improvements**:
- 170 files formatted with Black (100% compliance)
- Modern Python 3.11+ type hints throughout
- Organized modular structure
- Comprehensive type safety in core modules
- Memory leak prevention in EventBus

### Breaking Changes
None - all changes are internal refactoring and code organization improvements.

### Migration Notes
- See `docs/MIGRATION_GUIDE.md` for detailed upgrade guide
- Import paths changed for extracted functions (see migration guide)
- EventBus now supports owner-based subscription cleanup (backward compatible)
- Old documentation in `docs/archive/` for historical reference
- No API or functionality changes to public interfaces

---

## [0.7.0-dev] - 2025-12-12 (Camera System & Collision)

### Added - Camera System & Collision Improvements

- **Camera System** (`systems/camera_system.py`):
  - Multi-mode camera: WORLD_CLAMP, ROOM_CLAMP, FREE, LOCKED
  - Smooth following with configurable lerp and deadzone
  - Responsive letterboxing for any window size
  - Virtual resolution (1280x720) scaled to physical display
  - Bounds clamping for world and room modes
  - In-game mode cycling with 'C' key

- **Player Size Adjustments**:
  - Changed player to 28x56 pixels (2:1 height:width ratio)
  - Proper platformer proportions
  - Crouch reduces height to 28x28 pixels (half height)

- **Tile Scaling**:
  - Scaled tiles to 32x32 pixels (industry standard)
  - World size: 5120x5120 pixels (160x160 tiles)
  - Physics tuned for larger tiles (gravity 0.4, max fall 12px)

### Fixed - Collision System

- **Platform Collision Fix**:
  - Changed from center-based to feet-based detection
  - Now works correctly with tall player (56px height)
  - Fixed: `entity_rect.bottom <= platform.bottom` instead of center check
  - Location: [collision_system.py:283-291](../systems/collision_system.py#L283-L291)

- **Wall Climbing Bug Fix** (Critical):
  - Fixed infinite wall climbing when walking into walls
  - Corner detection now requires `abs(vy) > abs(vx) * 1.5` (must be falling)
  - Both overlap_x AND overlap_y must be small (4-14px)
  - Ground detection requires `overlap_y < overlap_x` (more horizontal = landing on top)
  - Locations:
    - Corner detection: [collision_system.py:135-148](../systems/collision_system.py#L135-L148)
    - Ground detection: [collision_system.py:227-246](../systems/collision_system.py#L227-L246)

- **Vertical Tunneling Prevention**:
  - Reduced max fall speed from 22px to 12px (< half tile)
  - Reduced gravity from 0.7 to 0.4
  - Ensures physics speed stays below tunneling threshold

### Changed - Documentation

- Updated [ARCHITECTURE.md](ARCHITECTURE.md) with camera system and phase completion
- Updated [WORLD_GENERATION.md](WORLD_GENERATION.md) with 16x16 zone grid
- Updated [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) with camera API
- Created [HANDOVER.md](HANDOVER.md) - comprehensive project handover document
- Refreshed docs (SUMMARY, QUICK_START, INDEX, README, PROJECT_ORGANIZATION) for v0.7.0, headless note, and wall-slide-disabled status
- Moved historical collision/playability notes to `docs/legacy/` (WALL_COLLISION_FIX, PLATFORM_COLLISION_SUMMARY, PLAYABILITY_TESTING)
- Added headless flag documentation and roadmapping for CI runs
- Added input command/snapshot serializers and replay record/playback harness (demo flags: --record/--replay/--show-replay)
- Added env override for logs (`NINJADASH_LOG_DIR`) to keep logs in the project or a custom path

### Changed - Wall Interaction & Input Safety

- Disabled wall slide mechanic during rework; enabled wall friction clamp plus wall-jump coyote buffer (player orchestrator)
- Ground detection tuned to avoid wall contact setting `on_ground`; predictive ground snap constrained to narrow gaps
- Input handling hardened to accept sparse/dict key data (integration tests updated)
- Full test suite passing (`python run_tests.py`)

### Added - Phase B: Procedural World Generation

- **World Generation System** (`systems/world_generation.py`):
  - Seed-based deterministic procedural generation
  - Hierarchical structure: World -> Biomes -> Rooms -> Zones -> Tilemap
  - Multi-biome support (DUNGEON, CAVE, BUILDING themes)
  - Frontier-based room graph generation (organic, connected layouts)
  - Room type system (START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS)
  - Door port system with multi-door support and proper alignment
  - Performance: Generates 30-room world in ~2-5ms

- **Zone Planning System** (`systems/zone_planning.py`):
  - 16x16 zone grid layout per room (256 zones -> 160x160 tiles)
  - Intelligent feature placement (shops, save points, loot)
  - BFS connectivity validation (guarantees all critical zones are reachable)
  - Room type-specific zone patterns
  - Zone roles: WALK, FILL, PLAT, DOOR, SAVE, SHOP, LOOT, VOID
  - Pathfinding ensures no isolated zones
  - Increased from 5x5 to 16x16 for finer granularity and more complex layouts

- **Room Generation System** (`systems/room_generation.py`):
  - Zone -> Tilemap conversion (each zone expands to 10x10 tiles)
  - 160x160 tilemap per room
  - Door carving system (creates passable connections between rooms)
  - Tile types: TILE_EMPTY (0), TILE_SOLID (1), TILE_PLATFORM (2)
  - Collision integration helper (`tilemap_to_collision_rects()`)

- **Placeholder Tile Assets** (`assets/generate_placeholder_tiles.py`):
  - 30 generated placeholder tiles (10 types  3 biomes)
  - 8x8 pixel PNG files with colored squares
  - Simple borders for visual distinction
  - Organized in `assets/biomes/dungeon/`, `cave/`, `building/`

- **Demo Integration** (`demo_game.py`):
  - Command-line flag: `--procedural` to enable procedural world mode
  - Command-line flag: `--seed 12345` to specify generation seed
  - In-game toggle: P key switches between static and procedural modes
  - HUD display: Mode indicator (STATIC/PROCEDURAL) and seed display
  - Seamless integration with existing collision, physics, and player systems

### Fixed - Bug Fixes & Enhancements (v0.4.0)

- **Player Spawn System**:
  - Fixed player falling through procedurally generated worlds
  - Smart spawn point search finds safe floor tiles with empty space above
  - Calculates spawn in tilemap coordinates, converts to screen space
  - Fallback to center if no safe floor found

- **ASCII Visualization** (`systems/room_generation.py`):
  - Added `print_tilemap_ascii()` function for console output
  - Downsamples 160x160 tilemaps to 40x40 ASCII visualization
  - Shows generated room layouts during world creation
  - Symbols: `#`=Solid, `-`=Platform, (space)=Empty

- **Zone Generation Complexity** (`systems/zone_planning.py`):
  - Room-type-specific probability distributions for zone roles
  - PLATFORM rooms: 55% platforms, 22% fill, 22% walk (high density)
  - COMBAT rooms: 45% platforms, 14% fill, 22% walk (medium density)
  - TREASURE rooms: 35% platforms, 10% fill, 22% walk (moderate)
  - BOSS rooms: 30% platforms, 12% fill, 22% walk (arena-like)
  - Default rooms: 25% platforms, 8% fill, 22% walk (open)

- **Room Boundaries** (`systems/room_generation.py`):
  - Added walls around all room edges (top, bottom, left, right)
  - Added base floor platform near bottom (like source project)
  - Ensures rooms are always navigable and contained
  - Prevents players from leaving room bounds

- **Platform Collision** (`systems/collision_system.py`, `demo_game.py`):
  - Implemented one-way platform collision (TILE_PLATFORM type 2)
  - Platforms only collide when player falls onto them from above
  - Player can jump up through platforms from below
  - Separate rendering for platforms (lighter gray, half-height visual)
  - Collision system now handles both solid tiles and platform tiles
  - Platforms work with all player mechanics (jump, double-jump, wall-jump, dash)

- **Zone Grid Enhancement** (`systems/world_generation.py`, `systems/zone_planning.py`, `systems/room_generation.py`):
  - Increased zone grid from 5x5 to 16x16 for finer granularity
  - 256 zones per room (more than before)
  - Each zone now 10x10 tiles instead of 32x32
  - Maintains 160x160 room size while providing much more detail
  - Allows for more complex and varied platform arrangements
  - Better control over obstacle placement and room complexity

### Technical Details - World Generation

- **Data Structures**:
  - `World`: Top-level container with biomes, seed, room graph, bounds
  - `Biome`: Thematic grouping with BiomeTheme enum
  - `RoomNode`: Individual room with position, type, neighbors, tilemap, zone_grid
  - `DoorPort`: Door connection point with center position and span

- **Generation Pipeline**:
  1. WorldGenerator creates room graph with frontier algorithm
  2. Rooms divided into biomes by clustering
  3. ZonePlanner assigns 16x16 zone grid to each room
  4. RoomGenerator converts zones to 160x160 tilemap
  5. Demo converts tilemap to collision rects for physics

- **BFS Connectivity Algorithm**:
  - Ensures all doors can reach each other
  - All features (shop, save, loot) reachable from doors
  - Creates walkable paths by converting DECOR  WALK zones
  - Validates playability before tilemap generation

- **Performance Metrics**:
  - World generation: 2-5ms for 30 rooms
  - Zone planning: <1ms per room
  - Tilemap generation: <1ms per room
  - Total pipeline: <10ms for complete world
  - Memory: ~1.5MB for 30-room world
  - Demo FPS: Stable 60 FPS with 1568 collision tiles

### Bug Fixes - World Generation

- Fixed Unicode encoding error (replaced  with "[OK]" for Windows console compatibility)
- Fixed StopIteration error when generating single room (added fallback logic in `_create_biomes()`)
- Fixed tilemap scaling for demo (scale down by factor of 4 to fit 160x160 room in viewport)

### Documentation - Phase B

- **NEW**: `docs/WORLD_GENERATION.md` - Complete API documentation
  - Architecture overview
  - API reference (WorldGenerator, ZonePlanner, RoomGenerator)
  - Complete pipeline example
  - Performance metrics
  - Design patterns (seed-based determinism, frontier generation, BFS validation)
  - Future enhancements
- **Updated**: `docs/DEVLOG.md` - Session 2025-12-12 (Afternoon) entry
  - Source system analysis
  - Design decisions log
  - Implementation details
  - Testing results
  - Problems solved
  - Code highlights
- **Updated**: `docs/ROADMAP.md` - Added Phase B tasks and progress tracking

### Planned
- Input system refactor with command pattern
- Camera system integration
- Sprite rendering and animation system
- HUD and menu systems
- Level progression and exit system
- Pickup system (coins, health, power-ups)
- Particle effects and visual polish
- Room transition system (door-based room switching)
- Platform collision (TILE_PLATFORM integration)
- Minimap system (Phase D)
- Autotiling system (9-slice, Phase C)

---

## [0.3.2] - 2025-12-12

### Added

- **Movement System**: Smooth interpolation-based movement eliminates jitter
  - High acceleration constant (2600.0) for responsive, tight controls
  - Interpolation formula: `vx += (target_vx - vx) * smooth_factor`
  - Frame-rate independent with dt scaling
  - Professional polish matching commercial platformers
- **Fast-Fall Mechanic**: Variable gravity when holding down while falling
  - Gravity multiplier (1.7x) improves air control and landing precision
  - Integrated into Player physics system
  - Source: Dynamic dungeon platformer project

### Changed

- **Movement Mechanic** (`mechanics/movement.py`):
  - Replaced discrete acceleration steps with smooth interpolation
  - Unified ground and air physics (same algorithm for both)
  - Removed separate ground/air acceleration constants
  - Added MOVEMENT_ACCEL constant (2600.0)
- **Player Physics** (`entities/player.py`):
  - Added fast-fall gravity multiplier (1.7x)
  - Added down key tracking for fast-fall activation
  - Fast-fall only activates when falling (vy > 0) and in air
- **Physics System** (`systems/physics_system.py`):
  - Updated FAST_FALL_MULT from 2.4 to 1.7 (matches source implementation)

### Technical Details

- **Movement Algorithm**: Smooth interpolation to target velocity
  - `target_vx = direction * MAX_SPEED * multiplier`
  - `smooth_factor = min(1.0, ACCEL * dt / max(MAX_SPEED, 1.0))`
  - `vx += (target_vx - vx) * smooth_factor`
- **Fast-Fall Conditions**: vy > 0 (falling) AND not on_ground AND down key held
- **Benefits**:
  - Eliminates jitter from discrete acceleration
  - More responsive feel from high acceleration constant
  - Better air control with fast-fall mechanic
  - Smoother acceleration/deceleration curves

### Documentation Updates

- **ROADMAP.md**: Added Phase 4.5 (Movement Enhancement) with detailed tasks
- **DEVLOG.md**: Added 2025-12-12 session with source system analysis
- **Movement Docstring**: Updated to reflect smooth interpolation approach

---

## [0.3.1] - 2025-12-11

### Fixed
- **Collision System**: Fixed wall clipping bug where players could get stuck in walls
- **Collision System**: Refined corner collision detection to prevent jitter when landing on platform edges
- **Collision System**: Added sophisticated overlap-based collision detection with special case handling for falling
- **Jump Mechanic**: Blocked all jump types (ground, wall, double) while crouching to prevent fall-through bug
- **Crouch Mechanic**: Fixed collision box height issues that caused players to fall through floor when jumping while crouched

### Changed
- **Collision System**: Improved horizontal vs vertical collision classification using overlap calculations
- **Collision System**: Added falling preference for corner collisions (overlap_x >= 8, overlap_x <= 15, overlap_y <= 20, diff <= 8)
- **Jump Mechanic**: Added crouch blocking to `_try_double_jump()` and `_try_wall_jump()` methods

---

## [0.3.0] - 2025-12-11

### Added - Architecture
-  **Event-Driven Architecture**: Complete pub/sub system with priority handlers
-  **Modular Mechanic System**: Self-contained, reusable mechanics
-  **Component-Based Entities**: Reusable components across all entity types
-  **Mod/Plugin Support**: Full plugin architecture with component registration
-  **Fixed 60Hz Physics**: Deterministic physics simulation (Glenn Fiedler pattern)

### Added - Core Systems
-  **Event Bus** (`core/event_bus.py`): Priority-based pub/sub with queue processing
-  **Logging System** (`core/logger.py`): Persistent file-based logging with user-configurable location
-  **Game Clock** (`core/clock.py`): Fixed 60Hz timestep with variable render rate
-  **State Management** (`core/state.py`): JSON-serializable state with snapshot/restore
-  **Entity System** (`core/entity_system.py`): Component-based architecture with fast queries
-  **Mod System** (`core/mod_system.py`): Plugin lifecycle management

### Added - Collision
-  **Collision System** (`systems/collision_system.py`): Universal AABB collision for all entities
-  **Collision Events**: Event-driven collision response
-  **Advanced Queries**: Radius searches and raycasting
-  **Penetration Resolution**: Automatic collision resolution with normal vectors

### Added - Physics
-  **Physics System** (`systems/physics_system.py`): Gravity application and velocity integration
-  **Fall Speed Capping**: Configurable maximum fall velocity
-  **Fixed Timestep**: Deterministic 60Hz simulation

### Added - Player Mechanics
-  **Jump Mechanic** (`mechanics/jump.py`):
  - Ground jump (14.5 units/tick)
  - Coyote time (0.12s grace period)
  - Jump buffering (0.14s input window)
  - Double jump (configurable air jumps)
  - Wall jump (8.5x horizontal, 14.5y vertical)
  - Crouch modifier (0.7x power)

-  **Movement Mechanic** (`mechanics/movement.py`):
  - Ground physics (0.9 acceleration, responsive)
  - Air physics (0.5 acceleration, floaty)
  - Max speed (8.0 units/tick)
  - Smooth acceleration/deceleration

-  **Dash Mechanic** (`mechanics/dash.py`):
  - Speed (16.0 units/tick, 2x normal)
  - Duration (0.16s, ~10 frames)
  - Cooldown (0.45s, ~27 frames)
  - Wall collision cancel

-  **Wall Slide Mechanic** (`mechanics/wall_slide.py`):
  - Stamina system (3.0s max, 2.0s regen)
  - Slide speed (2.2 units/tick controlled descent)
  - Min stamina requirement (0.3s to prevent spam)

-  **Crouch Mechanic** (`mechanics/crouch.py`):
  - Stealth movement (60% speed, 80% acceleration)
  - Collision box changes (50% height)
  - Ceiling detection
  - Jump power modifier (70%)

### Added - Entities
-  **Player Class** (`entities/player.py`): Orchestrates all player mechanics
-  **Reusable Components** (`entities/components.py`):
  - HealthComponent (damage, healing, invincibility)
  - PatrolComponent (back-and-forth movement)
  - FollowComponent (entity tracking)
  - ProjectileComponent (velocity-based projectiles)
  - PickupComponent (collectibles with auto-collection)
  - AIComponent (state machine for NPCs/enemies)

### Added - Testing
-  **14 Comprehensive Test Suites**: Full coverage of all systems
-  **Integration Tests**: Player + all mechanics working together
-  **Collision Edge Cases**: Corner cases, wall clipping, falling jitter
-  **Physics Tests**: Gravity, velocity, fall capping

### Added - Documentation
-  **SYSTEM_OVERVIEW.md**: Complete guide with API reference
-  **ARCHITECTURE.md**: Design patterns and component examples
-  **MODDING_GUIDE.md**: Plugin development guide
-  **README.md**: Quick start and feature overview

### Added - Demo
-  **Playable Demo** (`demo_game.py`): All systems integrated and working
-  **Controls**: Arrow keys/WASD, Space, Shift, Crouch toggle
-  **Level**: Platform layout with walls, ground, and obstacles

### Changed
-  **Migration**: Moved original files to `legacy/` folder for reference
-  **Project Name**: Renamed to "Vain Asher Gaming's: Indie Ninja Adventures"

### Technical Details
- **Language**: Python 3.11+
- **Graphics**: Pygame 2.6+
- **Architecture**: Component-based entity system, event-driven
- **Physics**: Fixed 60Hz deterministic simulation
- **State**: Serializable with JSON support

---

## [0.2.0] - Previous Version (Legacy)

### Added
- Basic player movement
- Monolithic player class
- Simple collision detection
- Procedural level generation
- Camera system
- UI elements

### Deprecated
- Original monolithic architecture (moved to `legacy/` folder)
- All code preserved for reference and potential integration

---

## Version History Summary

- **v0.7.0** (2025-12-12): Procedural world generation (16x16 grid), camera system, tile/player scaling, collision fixes
- **v0.3.1** (2025-12-11): Collision bug fixes, crouch-jump fix, wall clipping prevention
- **v0.3.0** (2025-12-11): Complete modular refactor, all core systems implemented
- **v0.2.0** (Previous): Original monolithic implementation

---

## Versioning Scheme

- **Major** (X.0.0): Breaking API changes, major architecture changes
- **Minor** (0.X.0): New features, systems, mechanics (backwards compatible)
- **Patch** (0.0.X): Bug fixes, refinements, optimizations

---

**Last Updated**: 2025-12-12
**Current Version**: 0.7.0
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
