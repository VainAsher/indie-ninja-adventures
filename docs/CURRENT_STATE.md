---
doc_type: current_state
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.64
replaces: docs/HANDOVER.md
---

# Current State

Canonical runtime and handover snapshot for the active Java stack.

## Baseline

- Date baseline: 2026-04-16
- Version baseline: v0.11.54
- Platform baseline: Windows desktop
- Engine stack: Java 21 + libGDX + Netty
- Source of truth for release metadata: `version.json`

## Product State

- Product direction: campaign-first single-player with optional multiplayer overlay.
- Active execution plan: [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- Current milestone lane: P0 stabilization and onboarding/runtime evidence hardening.
- Next release candidate: v0.11.65 (combat feel / balance iteration).
- Latest release verification (`2026-04-18`):
  - Tests green locally (BUILD SUCCESSFUL — all modules)
  - Tag target: v0.11.64

## Runtime Reality (Implemented)

- Authoritative server loop, zone simulation, and snapshot replication are active.
- Client rendering/UI loop is on libGDX desktop runtime.
- Mission lifecycle tracing and session-correlation logging are active.
- Siren-first onboarding flow and objective/mission affordances are active.
- NPC runtime dimensions are now authoritative over the wire (`NPCState.width/height`) and used by client render/debug hitbox overlays.
- Map input now follows explicit tap/hold semantics: `Tab` tap toggles quick map, `Tab` hold opens full map while held.
- Animation integration: stance-coupled posture readability (Yin unarmed / Yang armed) is enforced client-side — `EntityRenderer` routes animation key prefix from `stanceMode` directly (GDD §3.3), so Yin always renders unarmed and Yang always renders armed regardless of desync or offline state. Ledge corner hang-climb context and water-bank exit traversal bridge are also implemented with playtest log events.
- Solo/multiplayer campaign unification is live: `handleSoloPortalTravel()` now applies the same ability-gate + zone-migration logic as the server's `handlePortalTravel()`. Player state (health, level, xp, currency, inventory, abilities) is preserved across hub transitions; hub seeds are derived deterministically from the session seed via `HubRegistry.hubSeed()`. Campaign experience is identical whether played solo or co-op (drop-in/drop-out up to 4 players).
- Runtime keybinding ingestion is now live from `user_data/settings/settings.json` (`keybindings` block plus legacy `key_*` fallback), and map/debug/mission hotkeys consume the same binding table as input polling.
- Direct posture hot-swap input is now active (`select_weapon_1` / `select_weapon_2`, default `1`/`2`) with Yin-lock to unarmed and persistent Yang posture preference for runtime readability testing.
- `F1` controls overlay now renders active live bindings instead of a static key legend.
- Interaction affordance readability bridge is now active: lever/button/echo-trigger and pickup interactions queue short explicit animation feedback with `[Playtest][Interaction]` traces.
- Release/version parity gate is enforced through `tools/check_version_sync.py`.
- Solo replay playback is now routed through the Java client (`ninja-client-all.jar`) via `-Dninja.replayPath`; `ninja_dash.exe` / `demo_game.py` is no longer invoked for any launcher-initiated game operation.

## Canonical Documentation Set

- [INDEX.md](INDEX.md) - top-level documentation routing
- [ROADMAP.md](ROADMAP.md) - milestone sequencing and current targets
- [CHANGELOG.md](CHANGELOG.md) - release-facing version history
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md) - launcher-first playtest contract
- [GDD.md](GDD.md) - design intent and narrative/mechanics contracts
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md) - release metadata gate

## Repository Process Defaults

- Plan-embedded tasks are canonical for implementation tracking.
- `docs/TASK_LIST.md` is historical and archived.
- Retired/stale docs move immediately to `docs/archive/retired/`.
- Archive ZIP snapshots are kept in `docs/archive/zips/` and mirrored to release assets.
- Docs freshness checks are warning-only in CI unless explicitly run in strict mode.
