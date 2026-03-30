# Architecture Reference

Technical architecture of Indie Ninja Adventures. For the original design patterns doc see
[docs/ARCHITECTURE.md](../ARCHITECTURE.md). This document adds multi-repo context, data flow
diagrams, and the multiplayer/replay internals.

---

## Multi-Repo Context

This game repo (`indie-ninja-adventures`) is one of four:

```
indie-ninja-launcher   (public)  — distributes launcher .exe, hosts player docs
indie-ninja-adventures (private) — game source, CI/CD ← you are here
indie-ninja-feedback   (public)  — player bug reports
indie-ninja-pipeline   (private) — dev management
```

The game repo's CI dispatches to the launcher repo on tag push. The launcher polls the game
repo's GitHub Releases API for update checks.

---

## Core Design Principles

### 1. Component-Based Entities (ECS)

Entities are composed from components. No inheritance hierarchies.

```
Player = Physics + Health + Input + JumpMechanic + DashMechanic + CrouchMechanic + ...
Enemy  = Physics + Health + AI + PatrolBehaviour + ...
NPC    = Physics + DialogComponent + ShopComponent + ...
```

Relevant files:
- `core/entity_system.py` — base Entity, ComponentRegistry
- `entities/components.py`, `entities/components_core.py` — shared components
- `entities/player.py` — Player orchestrator

### 2. Event-Driven Communication

Systems publish to the event bus; other systems subscribe. No direct imports between systems.

```
CollisionSystem.emit(CollisionEvent)
  → JumpMechanic.on_collision() resets coyote timer
  → HealthMechanic.on_collision() applies hazard damage
  → CameraSystem.on_collision() adjusts room bounds
```

Relevant files:
- `core/event_bus.py` — EventBus with priority handlers
- `core/clock.py` — emits TickEvent at fixed 60Hz

### 3. Fixed 60Hz Timestep

Physics runs deterministically at 60Hz regardless of render FPS.

```
Game loop (variable FPS)
  ├── clock.tick()          → emits TickEvent (60Hz, fixed 0.0167s)
  │     └── physics_system.on_tick()
  │     └── mechanics.on_tick()
  │     └── network.on_tick()  (if multiplayer)
  └── render()              → variable delta, interpolated
```

This enables:
- Deterministic replay (record inputs, replay at same tick rate)
- Authoritative server (server runs same loop, clients reconcile)

---

## Data Flow

### Single-Player Frame

```
pygame.event.get()
  → InputPipeline.process()     → CommandKeyView (dict-like key state)
  → Player.process_input(keys)  → activates mechanics
  → clock.tick()                → TickEvent
  → PhysicsSystem.on_tick()     → apply velocity, gravity
  → CollisionSystem.on_tick()   → resolve AABB collisions
  → Mechanics.on_tick()         → jump, dash, combat state machines
  → EntityManager.on_tick()     → enemy AI, NPCs, pickups
  → CameraSystem.on_tick()      → follow player, clamp to room
  → HUD.render()
  → World.render()
  → pygame.display.flip()
```

### Multiplayer Frame (Client)

```
NetworkClient.poll_state()      → WorldSnapshot from server
  → RemotePlayer.apply_state()  → update position/anim of remote peers
  → LocalPlayer.process_input() → send InputCommand to server
  → (same render path as single-player)
```

### Multiplayer Frame (Server — authoritative, 60Hz)

```
TCP recv loop (daemon thread)
  → route InputCommand to ConnectedPlayer.latest_input

Simulation tick (asyncio, 60Hz)
  → GameSimulator.tick()        → runs physics + entity update
  → build WorldSnapshot         → serialise all player states
  → broadcast to all clients
```

---

## Replay System

Input-based recording — stores `InputCommand` objects per frame, not video.

### Recording

```python
# In InputPipeline
_recording: list[InputCommand]     # built up during play
finalize() → writes JSON to file   # on game end / ESC
```

Metadata written: `game_start_frame`, `terminated_frame`, version, seed, player spawn.

### Playback

```python
# InputPipeline in replay mode
replay_commands: list[InputCommand]   # loaded from JSON
process() → returns command by frame index (seeks past pre-game frames)
```

The game loop sees no difference — it just receives `InputCommand` objects from the pipeline.
Because the physics is deterministic at 60Hz, replays are bit-exact.

Relevant files:
- `network/input_pipeline.py` — recording and playback
- `network/commands.py` — InputCommand dataclass
- `network/snapshots.py` — Snapshot, PlayerState, MultiplayerSnapshot

---

## Multiplayer Architecture

### Phase 3 (Current — Authoritative Server)

```
Host machine:
  GameSimulator (60Hz)
  └── physics, entities, AI all run here
  └── broadcasts WorldSnapshot each tick

Client machine:
  receives WorldSnapshot
  └── updates RemotePlayer positions/animations
  └── local player still renders responsively (optimistic local input)
  └── sends InputCommand to server each frame
```

This is Phase 3a. Phase 3b (client prediction + server reconciliation) is planned.

### Network Protocol

TCP, framed messages with length prefix:

```
[4 bytes: length][JSON payload]
```

Message types (`network/protocol.py`):
- `HELLO` — client → server handshake
- `SERVER_HELLO` — server → client, assigns slot
- `INPUT` — client → server, per-frame InputCommand
- `SERVER_STATE` — server → client, WorldSnapshot
- `ENTITY_EVENT` — bidirectional, entity state change (pickup/kill)
- `PLAYER_JOIN` / `PLAYER_LEAVE` — lobby events
- `GAME_START` — server signals all clients to start

### Entity Event Sync

Pickup collections and enemy kills are broadcast as `ENTITY_EVENT` messages so all clients
suppress the entity simultaneously. Enemy AI still runs locally (divergence is tolerated for now).

---

## Save System

JSON-based persistence with HMAC integrity checking.

```
user_data/saves/
  save_slot_0.json    — save data + HMAC signature
  save_slot_0.bak     — automatic backup
```

Relevant file: `systems/save_system.py`

---

## World Generation

Hierarchical, seed-based procedural generation:

```
World (seed)
  └── Biomes (7 types: dungeon, cave, building, forest, town, sewer, hollow)
       └── Rooms (BFS connectivity validation)
            └── Zones (16×16 tiles)
                 └── Tilemaps (160×160 pixels)
```

Key constraint: BFS validates every room is reachable before the world is accepted.
Seed hierarchy ensures deterministic generation — same seed always produces same world.

Relevant files: `systems/world_generation.py`, `systems/zone_planning.py`,
`systems/room_generation.py`, `systems/connectivity.py`, `systems/seed_hierarchy.py`

---

## Network-Serialisable Systems

These systems produce/consume serialised state for multiplayer and replay:

| System | Serialised via | Used in |
|--------|---------------|---------|
| Player position/velocity/health | `PlayerState` in `snapshots.py` | Phase 3 server→client |
| Full world snapshot | `WorldSnapshot` in `snapshots.py` | Phase 3 broadcast |
| Input commands | `InputCommand` in `commands.py` | Replay, Phase 1/2/3 client→server |
| Entity events | JSON payload in `ENTITY_EVENT` | Pickup/kill sync |
| Save data | JSON in `save_system.py` | Persistence |
| Game state | `core/state.py` | Debugging / inspection |
