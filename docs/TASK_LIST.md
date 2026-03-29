# Task List — Indie Ninja Adventures

**Living document.** Review and update this file at the start of every development session.

Last updated: 2026-03-28 | Version: 0.7.2

---

## How to use this document

- **Now** — actively being worked on or the single next thing to do
- **Next** — ready to start; all dependencies met
- **Backlog** — confirmed work, not yet scheduled
- **Deferred** — agreed to do eventually; no timeline
- **Done** — completed; kept for reference (trim periodically)

---

## Now

Nothing actively in progress. Pick from **Next**.

---

## Next

### 2. UAT pass — fill in UAT_SUITE.md

**Why it matters**: M0 exit criteria requires recorded pass/fail results. The columns are blank.

**What to test** (manual playtest):

- Boot → main menu renders
- Campaign start → hub loads → forest portal accessible with basic jump
- Enter forest_1 → complete objective → victory screen → return to hub
- Mission unlock: completing forest missions grants double_jump ability
- Town portal inaccessible without double_jump (elevated platform)
- After unlocking double_jump: town portal now accessible
- Player death → respawn with full health
- F9 debug menu: password prompt → ability toggle → gates update live
- Settings menu: SFX volume cycles → sound level changes → persists on restart
- Settings menu: fullscreen toggle → no crash
- Key rebinding: change jump key in settings → new key works in-game

**File**: `docs/UAT_SUITE.md` or `docs/reviews/2026-03-25/UAT_SUITE.md`

---

### 3. Replace placeholder SFX with real audio assets

**Why it matters**: 12 placeholder WAV files exist (sine-wave tones). They work but sound terrible.

**Format**: 44100 Hz, 16-bit, mono WAV. Keep the same filenames.

**Files needed** (drop into `assets/audio/sfx/`):

| Filename | Sound |
| --- | --- |
| `swing.wav` | Sword swing whoosh |
| `hit_enemy.wav` | Impact on enemy |
| `player_hurt.wav` | Player takes damage |
| `player_death.wav` | Player death sting |
| `jump.wav` | Jump takeoff |
| `land.wav` | Landing thud |
| `dash.wav` | Dash whoosh |
| `pickup_coin.wav` | Coin collect |
| `pickup_item.wav` | Item pickup |
| `menu_select.wav` | Menu cursor move |
| `menu_confirm.wav` | Menu confirm |
| `inventory_open.wav` | Inventory open |

No code changes needed — `AudioManager.load_sounds()` will pick them up automatically.

---

## Backlog

### 4. Add background music (BGM)

**Why**: Silent exploration and combat reduces immersion. The AudioManager is ready for it.

**Approach**:

1. Add `pygame.mixer.music.load()` and `play()` call in `initialize_audio()` or as a new `play_music(track)` method on AudioManager
2. Wire region-specific tracks: hub music, forest music, combat music
3. Fade transitions between tracks on hub/mission load

**Depends on**: Real music assets

---

### 5. Gamepad support

**What**: Wire `pygame.joystick` so a controller can play through a full mission.

**Scope**:

1. Detect joystick in `initialize_pygame()`, store as `joystick: pygame.joystick.Joystick | None`
2. Add joystick axis/button reads to `Player.process_input()` (alongside existing keyboard reads)
3. Add gamepad key binding mapping to `config/settings.py` and `_build_key_bindings()`
4. Settings menu item: "Controller" toggle (enabled if joystick detected)

**Acceptance**: Player can complete forest_1 using only a controller.

---

### 6. New UAT suite document

The current `UAT_SUITE.md` covers pre-Phase-2 features. Write a new suite covering:

- Boss encounters (one per region)
- Ability gates (each portal height gate and each invisible gate)
- SFX for each of the 12 events
- Settings persistence (volume, fullscreen, key bindings survive restart)
- Debug ability menu (all abilities toggle correctly, gates rebuild)
- Portal placement gating (forest accessible, town blocked pre-double_jump)

**File**: `docs/UAT_SUITE.md` — replace or extend existing

---

### 8. Shuriken collision box always visible

**Issue**: The shuriken AABB debug rect renders in non-debug play.

**Fix**: Gate the shuriken collision draw behind `show_debug_overlay` flag the same way other hitboxes are.

**Files**: `rendering/` or wherever shuriken is drawn — grep for the draw call.

---

### 9. Fix raycast test

**Issue**: `tests/edge_cases/test_raycast.py` has a known pre-existing failure.

**Effort**: Low — investigate the failure, either fix the test or the code.

---

## Deferred

### Multiplayer / networking

Full authoritative-server multiplayer. The physics are deterministic and the input pipeline is command-pattern ready. Actual network code is in `network/` but is not wired.

**Timeline**: v1.0.0+ — requires launcher infrastructure first.

---

### Custom launcher

Downloads and verifies client, server, and mod bundles from GitHub releases. Enforces version parity. Supports mod browser.

**Timeline**: After multiplayer foundation.

---

### In-game level editor

Allow players to create and share custom missions.

**Timeline**: Post-multiplayer.

---

### Music / soundtrack (full)

Full OST with looping regional tracks, boss themes, victory sting. The SFX foundation is in place. Needs music assets and BGM wiring (tracked separately in Backlog item 4).

---

### Accessibility

- Text size option
- High contrast mode
- Reduce motion (disable screen shake, reduce particles)
- Colourblind mode for HUD colours

---

## Done (recent)

| Date | What | Commit |
| --- | --- | --- |
| 2026-03-28 | F9 debug ability menu (password: devmode) | `1aa12b6` |
| 2026-03-28 | Fullscreen crash fix (camera resize after toggle) | `5d30837` |
| 2026-03-28 | Hub portal placement: forest=floor, town=elevated | `94f6541` |
| 2026-03-28 | Settings wiring: key bindings, fullscreen, sfx_volume, hitboxes | `da60c55` |
| 2026-03-28 | SFX audio foundation wired end-to-end (12 events) | `4e6fdd1` |
| 2026-03-28 | Boss AI + champion system: movement, 6 boss types, per-type attacks, champion spawn | — |
| 2026-03-28 | Boss integration: BossManager wired, 6 boss missions | `4a9a096` |
| 2026-03-28 | Ability gates: sync_player_abilities + _rebuild_hub_gates | `88e9a93` |
| 2026-03-28 | Phase 0: all 6 campaign loop bugs fixed | `985e811` |
| 2026-03-28 | Docs/M0: all docs aligned to v0.7.x reality | `143840d` |
| 2026-01-01 | v0.7.0 project restructure and documentation overhaul | `029b7e8` |
