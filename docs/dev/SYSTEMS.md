# Systems Reference

Per-module summary of public APIs, key classes, and cross-system notes.
For full docstrings, generate the API reference: `pdoc game/ systems/ network/ -o docs/dev/api/`

---

## Core (`core/`)

### `event_bus.py` — EventBus

Pub/sub event system. Systems communicate only through events.

```python
bus = EventBus()
bus.subscribe(TickEvent, handler, priority=0)
bus.emit(TickEvent(dt=0.0167))
bus.process()   # drains the queue
```

### `entity_system.py` — Entity, ComponentRegistry

Component-based entity architecture.

```python
entity = Entity(entity_id=0)
entity.add_component(PhysicsComponent())
entity.get_component(PhysicsComponent)
```

### `clock.py` — GameClock

Fixed 60Hz timestep. Emits `TickEvent` each physics step.

```python
clock = GameClock(event_bus=bus)
clock.tick()   # call once per frame; emits 0 or more TickEvents
```

### `state.py` — PhysicsState, PlayerState

Network-serialisable game state.

```python
state = PlayerState(player_id=0, pos=(x, y), vel=(vx, vy), health=100)
d = state.to_dict()
state2 = PlayerState.from_dict(d)
```

### `logger.py` — GameLogger

Persistent rotating log file in `user_data/logs/`.

```python
logger = GameLogger()
log = logger.get_logger("ninja_dash.network")
log.info("Connected")
```

---

## Systems (`systems/`)

### `collision_system.py` — CollisionSystem

AABB collision with 11+ edge case fixes. Emits `CollisionEvent`.

```python
result = collision_system.resolve(entity, tilemap, dt)
# result: CollisionResult with .on_ground, .hit_wall, .hit_ceiling
```

**Network note**: Collision is deterministic at fixed 60Hz — safe for replay/server.

### `physics_system.py` — PhysicsSystem

Gravity integration, fall speed cap.

```python
physics.on_tick(entity, dt)   # modifies entity.vel_y
```

### `world_generation.py` — WorldGenerator

Generates a complete world from a seed.

```python
gen = WorldGenerator(seed=42)
world = gen.generate()   # World object with biomes, rooms, zones
```

**Network note**: Same seed always produces same world — clients don't need to sync world data.

### `save_system.py` — SaveSystem

JSON persistence with HMAC integrity + automatic backup.

```python
save = SaveSystem()
save.save(slot=0, data=game_state_dict)
data = save.load(slot=0)   # None if no save or integrity failure
```

### `camera_system.py` — CameraSystem

Multi-mode camera with smoothing and letterboxing.

Modes: `WORLD_CLAMP`, `ROOM_CLAMP`, `FREE`, `LOCKED`

```python
camera.set_mode(CameraMode.ROOM_CLAMP)
camera.follow(player)
offset = camera.get_offset()   # apply to all render calls
```

---

## Network (`network/`)

### `server.py` — run_server, GameSession

Asyncio TCP server. Runs game simulation at 60Hz (Phase 3).

```python
asyncio.run(run_server(port=7777, seed=42, max_players=4))
```

### `client.py` — NetworkClient

Background daemon thread. Non-blocking interface for the game loop.

```python
client = NetworkClient("127.0.0.1", 7777, player_id="p1")
client.connect()
client.send_input(command, pos=(x, y), vel=(vx, vy), health=100)
snapshot = client.poll_state()    # WorldSnapshot or None
events = client.poll_entity_events()  # list of entity event dicts
client.disconnect()
```

**Network note**: `send_input` and `poll_state` are safe to call every frame — they're non-blocking.

### `input_pipeline.py` — InputPipeline

Unified live/record/replay input source. Game loop uses this instead of `pygame.key.get_pressed()`.

```python
pipeline = InputPipeline(mode=PipelineMode.RECORD)
keys = pipeline.process(pygame_keys)   # CommandKeyView
pipeline.finalize()   # writes replay JSON on game end
```

### `snapshots.py` — Snapshot, PlayerState, MultiplayerSnapshot

Serialisable state for replay and multiplayer.

```python
snap = MultiplayerSnapshot(frame=100, seed=42, players=[PlayerState(...)])
d = snap.to_dict()
snap2 = MultiplayerSnapshot.from_dict(d)
```

### `commands.py` — InputCommand

Input command dataclass. All player input is expressed as `InputCommand`.

```python
cmd = InputCommand(up=True, dash=True, attack=False, ...)
```

---

## Entities (`entities/`)

### `player.py` — Player

Orchestrator for all player mechanics. Uses feature flags to enable/disable abilities.

```python
player = Player(
    player_id=0,
    spawn_x=100, spawn_y=100,
    event_bus=bus,
    feature_flags={"double_jump": True, "dash": True}
)
player.process_input(keys)   # called each frame
```

### `enemy_manager.py` — EnemyManager

Spawns and manages all enemies. Tracks `recently_killed_ids` for multiplayer sync.

```python
mgr = EnemyManager(event_bus=bus)
mgr.spawn(enemy_type="ORC", pos=(x, y))
mgr.update(dt, player)
kills = mgr.recently_killed_ids   # cleared each tick
```

### `remote_player.py` — RemotePlayer

Renders a remote peer from network snapshots. Infers animation state from velocity.

```python
remote = RemotePlayer(slot=1)
remote.apply_state(player_state)   # called on each WorldSnapshot
remote.render(surface, camera_offset)
```

---

## Game (`game/`)

### `campaign_manager.py` — CampaignManager

Manages campaign progression across regions and missions.

```python
mgr = CampaignManager()
mgr.complete_mission(mission_id="forest_01")
mgr.get_available_missions()   # list of unlocked mission IDs
```

### `game_simulator.py` — GameSimulator

Server-side simulation. Runs physics + entity tick without rendering.

```python
sim = GameSimulator(seed=42)
sim.tick(player_inputs)        # dict[slot → InputCommand]
snapshot = sim.get_snapshot()  # WorldSnapshot
```

**Network note**: This is what the Phase 3 server runs at 60Hz.

---

## How to Add a New System

1. Create `systems/my_system.py` with a class that subscribes to `TickEvent`
2. Initialise with an `EventBus` reference
3. Add to `demo_game.py` initialisation block
4. Add to `game/game_simulator.py` if it needs to run server-side
5. Write tests in `tests/unit/test_my_system.py`
6. Update this doc

---

## Generating API Docs

```bash
pip install pdoc
pdoc game/ systems/ network/ core/ entities/ -o docs/dev/api/
# Open docs/dev/api/index.html
```
