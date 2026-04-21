# Endings & Moral Choice System

**Indie Ninja Adventures** | v0.7.1 | 2026-03-28

---

## Rationale

The game has two distinct endings driven by a single moral choice at the climax of the campaign. Both endings share a bittersweet outcome — Yin & Yang remain as stars — but the fate of The Veil Maiden and the emotional tone of the post-game hub differ. The choice is designed to avoid a "good vs. bad" binary: both paths are defensible.

---

## Architecture

**File**: `game/ending_manager.py`

```
EndingChoice    (SAVE | DESTROY | NOT_CHOSEN)
EndingState     (NOT_STARTED → FINAL_BATTLE → CHOICE_PRESENTED → ENDING_PLAYING → COMPLETED)
EndingData      dataclass — per-ending title, description, cutscene_id, veil_maiden_fate, hub_final_state
EndingManager   orchestrates the state machine, callbacks, and hub state application
```

---

## Endings

### The Path of Mercy (SAVE)

> "You chose to save The Veil Maiden, offering her redemption."

- `cutscene_id`: `ending_save`
- Veil Maiden fate: **redeemed** — joins the hub as an NPC
- Hub final state:
  - `brightness: 0.9` — warm, hopeful
  - `veil_maiden_present: True`
  - `constellation_visible: True` — Yin & Yang visible as stars

### The Path of Justice (DESTROY)

> "You chose to destroy The Veil Maiden, ending her threat."

- `cutscene_id`: `ending_destroy`
- Veil Maiden fate: **defeated** — absent from hub
- Hub final state:
  - `brightness: 0.7` — dimmer, melancholic
  - `veil_maiden_present: False`
  - `constellation_visible: True` — Yin & Yang visible as stars

Both endings: `npcs_active: True`, `constellation_visible: True`. The constellation is the unifying symbol regardless of choice.

---

## State machine

```
NOT_STARTED
  → FINAL_BATTLE         when final boss mission begins
  → CHOICE_PRESENTED     when boss is defeated; player sees SAVE/DESTROY prompt
  → ENDING_PLAYING       after player selects a choice; cutscene runs
  → COMPLETED            cutscene ends; hub transitions to final state
```

### Callbacks

`EndingManager` uses two optional callbacks to integrate with the rest of the game:

| Callback | When called | Receives |
| --- | --- | --- |
| `on_choice_callback` | Player selects SAVE or DESTROY | `EndingChoice` |
| `on_ending_complete_callback` | Ending cutscene finishes | `EndingData` |

---

## Integration points

- **StoryManager** drives `EndingManager` — it detects final boss defeat and calls into the ending state machine
- **HubManager** reads `hub_final_state` to configure the post-game hub (brightness, NPC presence, constellation)
- **CampaignSaveData** stores the ending choice so it survives across sessions

---

## Companion orb tie-in

Yin & Yang (see [COMPANIONS.md](COMPANIONS.md)) are visible in Acts 0, 3, and 4. They are absent in Acts 1–2 (consumed by the Veil Maiden). In the post-game both endings return them as a visible constellation (`constellation_visible: True`), but never as physical orbs again.

---

## Current status

`EndingManager` is fully implemented. Integration with `StoryManager` and the cutscene system depends on boss AI being implemented (the final boss must be beatable to trigger the choice). See [TASK_LIST.md](../TASK_LIST.md) — boss AI is the current top-priority task.
