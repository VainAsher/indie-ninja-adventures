# Replay & Input Pipeline

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Rationale

The input pipeline exists to support three distinct use cases from a single code path:

1. **Live play** — raw `pygame` key state read each frame
2. **Recording** — live play with every frame's inputs serialized to JSON
3. **Replay** — playback driven entirely by the saved JSON (no keyboard needed)

This was designed for deterministic replay: the physics engine runs at a fixed 60 Hz timestep, so the same input sequence always produces the same world state. The same infrastructure will support future multiplayer (command-based authority).

---

## Architecture

```
network/
├── commands.py          InputCommand dataclass — one per frame
├── input_pipeline.py    InputPipeline — live/record/replay unified
└── __init__.py
```

**`InputCommand`** (`network/commands.py`) — one instance per physics tick, capturing every possible player action as booleans:

```
up, down, left, right, jump, dash, attack, throw, teleport, ninjutsu,
interact, inventory, consumable, minimap, fullmap, cycle_camera,
toggle_proc, debug_overlay, slow_walk, menu_confirm, menu_back,
controls_overlay
```

**`CommandKeyView`** — a pygame-key-like adapter so `keys[pygame.K_SPACE]` transparently uses the command's `jump` field. This means player code reads keys the same way in all three modes.

**`InputPipeline`** — the central class:

| Mode | Constructor params | `next()` returns |
| --- | --- | --- |
| Live | no `record_path` or `replay_path` | `(raw_keys_state, InputCommand)` |
| Record | `record_path=<path>` | `(raw_keys_state, InputCommand)` — commands buffered |
| Replay | `replay_path=<path>` | `(CommandKeyView, InputCommand)` — keyboard ignored |

---

## Usage

### CLI flags

```bash
python demo_game.py --record user_data/replays/my_run.json
python demo_game.py --replay user_data/replays/my_run.json
```

These are passed to the `InputPipeline` constructor at startup.

### In-code (game loop)

```python
pipeline = InputPipeline(record_path=..., replay_path=..., metadata={...})

# Each physics tick:
keys_like, command = pipeline.next(raw_keys, frame_idx, keydown_keys)

# Tell the pipeline when the menu was dismissed (gameplay started)
pipeline.set_game_start(frame_idx)

# At shutdown:
pipeline.finalize()   # writes JSON to disk if recording
```

### `set_game_start(frame)`

Records `game_start_frame` in the metadata. On replay the pipeline seeks past all menu-navigation frames so replays start directly at gameplay, not at the main menu.

### `finalize()`

Writes the recording to `record_path` as JSON. Also writes a command log to `log_path` if `log_commands=True`.

---

## File format

Recording files are JSON:

```json
{
  "game_start_frame": 145,
  "terminated_frame": 4207,
  "seed": 98765,
  "commands": [
    {"frame": 145, "jump": false, "left": false, ...},
    {"frame": 146, "jump": true,  "left": false, ...},
    ...
  ]
}
```

All `InputCommand` fields are serialized via `to_dict()` / `from_dict()`.

---

## Determinism requirements

For a replay to be byte-identical to the original run:

- Physics must run at fixed 60 Hz — no variable-timestep physics
- No `random.random()` or `time.time()` in player/physics code — use seeded RNG or tick counts
- World generation uses the same seed from recording metadata

The loot system (`game/loot_system.py`) already uses a seeded `random.Random` for this reason.

---

## Current status

The pipeline is **fully implemented** and wired in `demo_game.py`. The `--record` and `--replay` flags work. Recording files go to `user_data/replays/` by default.

Limitations:
- No in-game playback UI — replay is a launch-time flag only
- No replay browser or playback scrubbing
- `controls_overlay` and `menu_confirm`/`menu_back` fields exist but not all are fully consumed by the game loop
