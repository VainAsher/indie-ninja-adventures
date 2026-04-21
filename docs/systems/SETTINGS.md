---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Settings and Persistence Surface (Java)

## Scope

Runtime control bindings and slot-based save settings currently active in Java runtime.

## Primary Java owners

- Controls:
  - `java/client/src/main/java/com/indieniinja/client/KeyBindings.java`
  - `java/client/src/main/java/com/indieniinja/client/InputPoller.java`
- Save slots:
  - `java/client/src/main/java/com/indieniinja/client/game/SaveManager.java`
  - `java/client/src/main/java/com/indieniinja/client/ui/SlotSelectScreen.java`
- Settings load site:
  - `java/client/src/main/java/com/indieniinja/client/GameScreen.java`

## Runtime behavior

- Keybinding overrides load from `user_data/settings/settings.json`.
- Defaults are embedded in `KeyBindings.applyDefaults()`.
- Save system is slot-based (`slot_1..slot_3`) with checksum and backup rotation.
- Mission/story state restoration flows through `SaveData` and manager restore paths.

## Method-level call graphs

- Controls load graph:
  - `GameScreen` startup -> `KeyBindings.load(settingsFile)` -> `KeyBindings.applyDefaults()` -> JSON override parse -> resolved action bindings
- Input command graph:
  - `GameScreen.render(...)` -> `InputPoller.poll()` -> `InputCommand` -> solo sim step or network send path
- Save slot graph:
  - `SlotSelectScreen` constructor -> `SaveManager.listSlots()` -> slot metadata for UI selection
- Save runtime graph:
  - Gameplay events -> `SaveManager.markDirty()`
  - Per-frame autosave -> `GameScreen.render(delta)` -> `SaveManager.tick(delta)` -> `SaveManager.save()` at threshold
  - Restore path -> `SaveManager.load()` -> `SaveManager.applyLoadedData(...)` -> `SaveData.restore(story, missions)`

## Notes

- Launcher-level configuration lives in `launcher/launcher.py` and `launcher_config.json`.
- Java client does not yet expose a full in-game settings menu equivalent to legacy prototype docs.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/SETTINGS.md`
