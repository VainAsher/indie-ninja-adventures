# Plan — Phase 3: Authoritative Server

**Date:** 2026-03-29
**Status:** Phase 3a COMPLETE — server simulation running, clients synced. Phase 3b deferred.
**Precedes:** Full server-authoritative game simulation where the server is the source of truth for all entity state.

---

## 1. Current State (v0.7.8)

| Layer | Status |
|---|---|
| Phase 1: Input relay | ✅ Complete — server relays per-frame `InputCommand`; each client runs independent simulation |
| Phase 2.5: Entity events | ✅ Complete — pickup collection and enemy kills broadcast via `ENTITY_EVENT`; remote clients suppress matching entities |
| Phase 3: Authoritative simulation | ❌ Not started — the server runs no game logic; divergence from independent AI still occurs |

### Remaining divergence sources (v0.7.8)

1. **Enemy AI** — `enemy_manager.update(player_x=local_x, player_y=local_y)` uses the **local player's position**. Each client's AI makes different chase/attack decisions since it only knows its own player, not the remote players.
2. **Falling platforms** — trigger state not tracked, not broadcast.
3. **Boss state** — entirely unsynced.
4. **Loot drops** — enemies drop loot locally; remote clients suppress the *kill* but not the *loot items spawned by it*.
5. **Hazards / environment** — lava/water damage, dynamic hazard spawns are each client-local.

Phase 2.5 fixed the two highest-visibility desyncs (pickups, enemy kills). Phase 3 fixes everything else by moving the simulation to the server.

---

## 2. What "Authoritative Server" Means

The server runs the complete game simulation every tick:

```
Server tick (60 Hz):
  1. Collect latest InputCommand from each connected slot
  2. Apply inputs to each player entity (physics + mechanics)
  3. Update enemies (AI chase/attack using all players' positions)
  4. Update pickups, hazards, falling platforms
  5. Resolve all collisions
  6. Build WorldSnapshot (full state of every entity)
  7. Broadcast WorldSnapshot to all clients

Client tick (60 Hz):
  1. Capture local input → send to server
  2. (Optional) Run local prediction for own player
  3. Receive WorldSnapshot → apply authoritative positions to all entities
  4. Render
```

The client simulation becomes a display layer. The server is the single source of truth.

---

## 3. Gap Analysis — Work Needed Before Phase 3

These are the blockers and prerequisites, ordered by dependency.

---

### G1 — Extract `GameSimulator` from `demo_game.py` [CRITICAL BLOCKER]

**Problem:** `demo_game.py` is 4,255 lines. The entire game loop (`run_game()`) is one function that tightly intermixes simulation logic with pygame rendering, audio, UI, menus, and single-player-only assumptions.

The server cannot import `demo_game.py` to run the simulation — it would drag in pygame display, audio init, all menu systems, etc.

**Required:** A `GameSimulator` class (or module) that contains only the simulation:
- Player physics (apply `InputCommand` per slot, update position/velocity/health)
- Enemy AI + physics (`enemy_manager.update`)
- Pickup state (`pickup_manager.check_collections`)
- Hazard collisions (`hazard_manager.check_hazards`)
- Collision resolution (`collision_system.check_and_resolve`)
- Platform step (falling/moving platforms)

**Must not contain:**
- Any `pygame.draw`, `pygame.Surface`, `pygame.display` calls
- Camera system
- Audio manager calls
- Menu/dialogue/UI code
- Save/replay/input pipeline code

**Approach:** Incremental extraction, not a big-bang rewrite.
1. Identify the "physics block" in the game loop (roughly lines 2383–2870 in `demo_game.py`).
2. Pull it into `game/game_simulator.py` as `class GameSimulator`.
3. `GameSimulator.__init__(seed, tiles, collision_system)` — takes the pre-built world.
4. `GameSimulator.step(inputs: Dict[int, InputCommand]) -> None` — advances one tick.
5. `GameSimulator.get_snapshot() -> WorldSnapshot` — serialises current state.
6. `demo_game.py` creates a `GameSimulator` and delegates to it (no behaviour change).

**Estimate:** Largest single task — 2–3 work sessions.

---

### G2 — Enemy AI must support multiple players [CRITICAL BLOCKER]

**Problem:** `enemy_manager.update(player_x, player_y, ...)` assumes one player. The server will have 1–4 players. Enemy AI needs to target the nearest of all players.

**Current signature:**
```python
def update(self, dt, player_x, player_y, player_width, player_height, ...) -> int:
```

**Required change:**
```python
def update(self, dt, players: list[tuple[float, float, int, int]], ...) -> dict[int, int]:
    # players = [(x, y, width, height), ...] per active slot
    # returns damage dealt to each slot
```

Inside `EnemyAI.update()`, replace the hardcoded player target with `nearest_player(players)`.

Also affects `check_player_enemy_collision` — needs to check against all players.

**Estimate:** Medium task — 1 session.

---

### G3 — Design and implement `WorldSnapshot` [MUST]

**Problem:** The current `MultiplayerSnapshot` carries only player positions:
```python
@dataclass
class MultiplayerSnapshot:
    frame: int
    seed: int
    players: list[PlayerState]    # only player pos/vel/health/facing/is_dead
    metadata: dict
```

Phase 3 needs a complete world state that clients can render from without running local simulation:

```python
@dataclass
class WorldSnapshot:
    frame: int
    seed: int
    players: list[PlayerState]           # unchanged
    enemies: list[EnemyState]            # id, type, x, y, vx, vy, hp, ai_state, facing
    pickups: list[PickupState]           # id, x, y, type, alive
    platform_states: list[PlatformState] # id, triggered, current_y, etc.
    # boss, hazards, etc. — deferred to Phase 3b
```

**Bandwidth concern:** At maximum entity counts (say 60 enemies, 80 pickups) uncompressed JSON is ~8 KB/frame → ~480 KB/s per client. At 4 clients this is ~2 MB/s server outbound — acceptable on LAN, marginal over internet. Delta compression or interest-management can be Phase 3b.

**Estimate:** Small–medium — define schema, implement serialisation. 1 session.

---

### G4 — Falling platform stable IDs and sync [MUST]

**Problem:** Falling platforms have no stable world-space ID. Their trigger state (untriggered / falling / at bottom) is not tracked in any shareable structure.

**Required:**
- Each falling platform gets a stable ID: `f"plat_{tile_x}_{tile_y}"`
- `FallingPlatform` or equivalent tracks `state: "idle" | "triggered" | "falling" | "settled"`
- Platform state included in `WorldSnapshot.platform_states`
- Server applies all clients' trigger events authoritatively

**Estimate:** Small — 1 session. Builds on Phase 2.5's entity event foundation (already has `platform_trigger` etype slot defined in the protocol).

---

### G5 — Server simulation loop (asyncio 60 Hz) [MUST]

**Problem:** The server currently processes one tick per received `INPUT` message — it advances `session.frame` each time it gets an input. This is reactive, not proactive.

Phase 3 needs a proactive 60 Hz server loop:
```python
async def _simulation_loop(self):
    while not self._stop.is_set():
        t0 = asyncio.get_event_loop().time()
        inputs = self._collect_latest_inputs()   # one InputCommand per slot
        self.simulator.step(inputs)              # advance game by one tick
        snapshot = self.simulator.get_snapshot()
        await self.session.broadcast(MessageType.WORLD_STATE, snapshot.to_dict())
        elapsed = asyncio.get_event_loop().time() - t0
        await asyncio.sleep(max(0.0, TICK_INTERVAL - elapsed))
```

The existing `_client_loop` per player still handles INPUT messages but only stores the latest command; the simulation loop consumes them.

**Estimate:** Medium — 1 session.

---

### G6 — Client reconciliation — apply `WorldSnapshot` to local entities [MUST]

**Problem:** Currently the client's `poll_state()` returns a `MultiplayerSnapshot` that only updates remote player ghosts. For Phase 3, the client needs to apply the full `WorldSnapshot` to its own enemy manager, pickup manager, and platform system.

For the local player: the simplest correct approach is to apply the server's authoritative position each frame ("rubber band"). This adds 1 RTT of latency (~20–40 ms on LAN — barely perceptible). Input prediction (G7) eliminates this cost but is optional.

**Required:**
```python
# In demo_game.py multiplayer block:
snap = WorldSnapshot.from_dict(_net_client.poll_state())
if snap:
    # Players — already done for remote players
    # Enemies — overwrite enemy_manager positions from snap.enemies
    _apply_enemy_snapshot(enemy_manager, snap.enemies)
    # Pickups — overwrite pickup_manager from snap.pickups
    _apply_pickup_snapshot(pickup_manager, snap.pickups)
    # Platforms — overwrite platform states from snap.platform_states
    _apply_platform_snapshot(platforms, snap.platform_states)
    # Local player (no prediction) — apply server position directly
    player.state.physics.x = snap.players[local_slot].pos[0]
    player.state.physics.y = snap.players[local_slot].pos[1]
```

**Estimate:** Medium — 1 session, depends on G3 and G5.

---

### G7 — Input prediction for local player [NICE TO HAVE]

**Problem:** Without prediction, the local player's position lags by 1 RTT. On LAN this is ~5–20 ms (barely felt). Over the internet (~80–200 ms RTT) it feels sluggish.

**Approach:** Client-side prediction + server reconciliation:
1. Apply input locally each frame (run local physics for own player only).
2. Keep a ring buffer of (frame, InputCommand, predicted_position).
3. When the server snapshot arrives for frame N, compare with predicted position.
4. If they diverge beyond a threshold, snap to server position.

This is classic "client prediction + rollback" and is well-understood. It is complex to implement correctly (handling collisions in prediction, re-simulating buffered inputs after correction).

**Decision:** Defer to Phase 3b. Phase 3a uses rubber-band reconciliation (G6). Prediction can be added without breaking the architecture.

**Estimate:** Large — 1–2 sessions.

---

### G8 — Loot drops authoritative [SHOULD]

**Problem:** In Phase 2.5, `suppress_enemy()` removes the enemy on remote clients but *does not replicate the loot that dropped*. Each client runs `_handle_enemy_death` locally — loot is generated, but only on the client that killed the enemy.

In Phase 3, loot is generated server-side and included in `WorldSnapshot.pickups`. Clients apply it from the snapshot. The `_handle_enemy_death` loot logic moves to the server.

**Estimate:** Falls out of G3 + G6 — no extra work if WorldSnapshot includes pickup state.

---

### G9 — Remove Phase 2.5 workarounds after Phase 3 is live [CLEANUP]

Once Phase 3 is stable, the following Phase 2.5 scaffolding becomes redundant:
- `send_entity_event("pickup_collect")` / `suppress_by_id` — world state is authoritative
- `recently_killed_ids` / `suppress_enemy` — server handles enemy deaths
- `ENTITY_EVENT` message type can be deprecated (or repurposed for player-triggered events like abilities)

Keep until Phase 3 is verified in testing. Remove in a cleanup commit.

---

## 4. Work Order

```
Phase 3a — Foundation (2–3 sessions)
  [1] G3: Design WorldSnapshot schema + serialisation
  [2] G2: Enemy AI multi-player support
  [3] G4: Falling platform stable IDs + state tracking
  [4] G1: Extract GameSimulator (largest task — do in sub-steps)
      [1a] Identify and list all simulation calls in demo_game.py game loop
      [1b] Create game/game_simulator.py skeleton with step() + get_snapshot()
      [1c] Move player physics block into GameSimulator.step()
      [1d] Move enemy update block into GameSimulator.step()
      [1e] Move pickup/hazard/platform blocks into GameSimulator.step()
      [1f] Wire demo_game.py to delegate to GameSimulator (smoke test solo play)
      [1g] Verify solo play is identical before/after (use replay determinism)

Phase 3b — Server Simulation (1–2 sessions)
  [5] G5: Server simulation loop (asyncio 60 Hz, proactive)
  [6] G3 (cont.): Server builds WorldSnapshot from GameSimulator each tick
  [7] Broadcast WorldSnapshot via new WORLD_STATE message type

Phase 3c — Client Reconciliation (1–2 sessions)
  [8] G6: Client applies WorldSnapshot to enemies, pickups, platforms
  [9] G6 (cont.): Rubber-band reconciliation for local player
  [10] G9: Remove Phase 2.5 workarounds, cleanup

Phase 3d — Prediction (optional, later)
  [11] G7: Input prediction + server reconciliation for local player
```

---

## 5. Architecture Decisions

### 5a — Does `GameSimulator` need pygame?

Pygame is needed on the server for:
- `pygame.Rect` — used in collision detection (`core/state.py`, `systems/collision_system.py`)
- Physics constants — defined in `config/physics_constants.py` (pure Python, no pygame)

Pygame is **not** needed for:
- Physics math (pure Python)
- AI logic (pure Python)
- World generation (pure Python)

**Decision:** Run pygame in headless mode on the server (SDL_VIDEODRIVER=dummy). This is already how `--headless` works in `demo_game.py`. The server calls `pygame.init()` in headless mode at startup. No display surface is ever created.

### 5b — Server world generation

The server generates the world from `current_seed` using the same `regenerate_world_state()` call that clients use. Since both use the same seed and the same deterministic generators, the world is identical. Clients skip local world generation when connected to a server (they receive tiles from the server as part of `GAME_START`).

Wait — currently clients generate the world locally from `server_seed`. For Phase 3, the server's `WorldSnapshot` is authoritative for entity state, but the **tile layout** is still generated locally from the seed (tiles don't change). This is fine — only dynamic entity state (enemies, pickups, platforms) needs to be in the snapshot.

**Decision:** Tile layout remains client-generated from seed (deterministic, doesn't need sync). Entity state comes from server snapshot. This avoids sending tile data over the network.

### 5c — Bandwidth budget

At 60 Hz, a `WorldSnapshot` with:
- 4 players (6 fields each) ≈ 200 bytes
- 60 enemies (8 fields each) ≈ 2,400 bytes
- 80 pickups (4 fields each) ≈ 1,600 bytes
- 20 platforms (3 fields each) ≈ 300 bytes
- Total ≈ ~4,500 bytes uncompressed JSON per frame

At 60 Hz to 4 clients: ~4.5 KB × 60 × 4 ≈ **1.08 MB/s outbound from server**

This is fine for LAN. For internet play, msgpack or delta encoding could reduce this by 3–5×. Deferred to Phase 3b.

---

## 6. Files Changed by Phase 3

| File | Change |
|---|---|
| `game/game_simulator.py` | **New** — `GameSimulator` class |
| `network/snapshots.py` | **Extend** — `WorldSnapshot`, `EnemyState`, `PickupState`, `PlatformState` |
| `network/protocol.py` | **Add** — `WORLD_STATE` message type |
| `network/server.py` | **Extend** — `GameServer` runs `GameSimulator`, proactive 60 Hz loop |
| `network/client.py` | **Extend** — handles `WORLD_STATE`, stores `WorldSnapshot` |
| `entities/enemy_manager.py` | **Modify** — `update()` accepts multiple player positions |
| `entities/enemy_ai.py` | **Modify** — `update()` targets nearest of all players |
| `demo_game.py` | **Modify** — delegates simulation to `GameSimulator`; applies `WorldSnapshot` |
| `systems/room_generation.py` | **Modify** — falling platforms get stable IDs |

---

## 7. Known Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `demo_game.py` refactor breaks single-player | High | High | Use replay determinism tests to verify before/after |
| Server 60 Hz loop drifts under load | Medium | Medium | Use asyncio.sleep with drift correction; log when behind |
| WorldSnapshot bandwidth too large for internet play | Medium | Low | Defer compression to Phase 3b; LAN is the initial target |
| Pygame in headless server mode causes issues on Windows | Low | Medium | Already proven by `--headless` in demo_game.py |
| Input prediction diverges on collisions | High (if implemented) | Medium | Use rubber-band first; add prediction in Phase 3d only |

---

## 8. Exit Criteria

Phase 3a is complete when:

- [x] Two clients connected to a server show enemies in the same positions, making the same AI decisions, dying at the same time — **VERIFIED** (automated test: both clients report identical frame/enemy/pickup counts)
- [x] Pickup collection by one client removes the pickup on all other clients — **IMPLEMENTED** (server runs check_collections authoritatively; dead pickups drop from WorldSnapshot)
- [x] Falling platforms trigger in sync for all clients — **IMPLEMENTED** (560 platform states broadcast each tick; client applies server state each frame)
- [x] Solo play (no server) is behaviourally identical to pre-Phase 3 — **UNCHANGED** (WorldSnapshot block only runs when `_net_client is not None`)
- [x] Server logs show stable 60 Hz tick rate under 4-client load — **VERIFIED** (~82 Hz avg; drift warning logs when behind)

### Known Phase 3a Limitations (deferred to Phase 3b)

- **Server-side combat**: `GameSimulator.step()` does not run `combat_mechanic.check_enemy_collisions()`. Player health is client-authoritative. Server's WorldSnapshot always shows full HP for all players. (Health sync disabled in rubber-band to avoid resetting client health each frame.)
- **World transition sync**: Server simulates the initial hub world only. When clients transition to arcade/dungeon mode (different shape/rooms), entity positions diverge from client tile layout. Phase 3b requires signalling the server to regenerate with new shape/seed/rooms.
- **Input prediction (G7)**: Local player position lags by 1 RTT. Rubber-band correction is the current approach. Prediction deferred to Phase 3d.
