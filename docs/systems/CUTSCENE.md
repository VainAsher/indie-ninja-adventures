---
doc_type: system
status: living
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.3
---

# Cutscene System

The Java client uses data-driven cutscenes for Act I story delivery. Cutscenes
are client-side only: they can lock local input, run inline dialogue, move the
camera, apply temporary client-side NPC presentation overrides, set story flags,
and mark themselves complete in the active save slot.

## Runtime

- `CutsceneLoader` reads `data/cutscenes/index.json` and loads each listed JSON
  by explicit path. This is required for fat-JAR runtime support; directory
  listing does not work from the classpath.
- `CutsceneManager` owns sequencing. It starts by id, advances steps in
  `tick(delta)`, honours skip policy, writes completion flags, and restores
  player/camera state on complete, skip, interrupt, or emergency stop.
- `GameScreen` wires manager ticking, player lock, camera override, entity
  overrides, DevConsole commands, and trigger entry points.
- `SaveManager.completedCutscenes()` persists completed ids; old saves without
  the field default to an empty set.

## Authoring Contract

Each cutscene file is an object:

```json
{
  "id": "act1_linzi_first_appearance",
  "version": 1,
  "act": 1,
  "blocking": true,
  "skip_policy": "allow_after_first_view",
  "triggers": [{ "event": "npc_interact", "id": "linzi" }],
  "start_conditions": [{ "flag_not_set": "act1_linzi_met" }],
  "completion_flags": ["act1_linzi_met"],
  "steps": []
}
```

Supported trigger events:

- `npc_interact`
- `mission_complete`
- `flag_change`

Supported step types:

- `lock_player`, `unlock_player`
- `dialogue`
- `wait`
- `set_flag`
- `camera_focus`, `camera_pan`, `camera_restore_player`
- `entity_face`, `entity_move_to`, `entity_set_visible`, `entity_play_anim`

Accepted but currently safe no-op step types:

- `title_card`, `fade_in`, `fade_out`, `hub_change`, `start_mission`

## Markers

Camera and entity target coordinates can be authored directly as `"x,y"` or by
marker id. Named marker ids live in `data/cutscenes/markers.json`:

```json
[{ "id": "marker_linzi_bridge", "x": 820, "y": 420 }]
```

Missing markers are logged and skipped safely.

## Authoring Rule

Every new `data/cutscenes/*.json` scene file must be added to
`data/cutscenes/index.json`. `markers.json` is loaded separately and should not
be listed in the scene manifest.
