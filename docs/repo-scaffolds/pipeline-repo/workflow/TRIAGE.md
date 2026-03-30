# Stage 2: Triage

Classify and prioritise the cleaned intake issues.

**When:** Monday, after Intake is complete.

---

## Classification Axes

### Severity

| Level | Criteria |
|-------|----------|
| P0 — Critical | Crash, data loss, unplayable, regression from previous release |
| P1 — High | Major feature broken, affects most players, no workaround |
| P2 — Medium | Noticeable bug, workaround exists, or moderate feature request |
| P3 — Low | Cosmetic, polish, minor annoyance, nice-to-have feature |

### Type

| Type | Label |
|------|-------|
| Bug | `bug` |
| Feature request | `feature` |
| Polish / UX | `feedback` |
| Performance | `performance` |

### System

Label the affected system:

- `combat` — player attacks, enemy interactions
- `multiplayer` — netcode, sync, server, lobby
- `replay-system` — recording, playback, determinism
- `world-gen` — procedural generation, seeding, connectivity
- `ui` — menus, HUD, dialogue, launcher
- `movement` — player physics, mechanics, collision
- `campaign` — missions, story, gates, NPCs
- `audio` — SFX, BGM

---

## Priority Matrix

| Severity | Many players | Some players | Few players |
|----------|-------------|--------------|-------------|
| P0 | Fix this sprint | Fix this sprint | Fix next sprint |
| P1 | This sprint | Next sprint | Backlog |
| P2 | Next sprint | Backlog | Backlog |
| P3 | Backlog | Backlog | Someday |

---

## Steps

1. For each new intake issue: assign severity + type + system labels
2. Add to GitHub Project backlog
3. Order backlog by: P0 first → P1 → P2 → P3, then by player impact within each tier
4. Flag anything that blocks an upcoming milestone

---

## Output

Labelled, prioritised backlog ready for sprint planning.
