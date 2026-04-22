---
doc_type: current_state
status: living
owner: core-team
last_updated: 2026-04-22
version_anchor: v0.12.02
replaces: docs/HANDOVER.md
---

# Current State

Canonical runtime and handover snapshot for the active Java stack.

## Baseline

- Date baseline: 2026-04-22
- Version baseline: v0.12.02
- Platform baseline: Windows desktop
- Engine stack: Java 21 + libGDX + Netty
- Source of truth for release metadata: `version.json`

## Product State

- Product direction: campaign-first single-player with optional multiplayer overlay.
- Active execution plan: [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- Extraction closure archive: [`docs/archive/retired/2026-04-21_v0.11.71_pygame-extraction/`](archive/retired/2026-04-21_v0.11.71_pygame-extraction/)
- Current milestone lane: P0 stabilization and onboarding/runtime evidence hardening.
- Next release candidate: v0.12.03 (post-release stabilization follow-up).
- Latest release verification (`2026-04-22`):
  - Tests green locally (BUILD SUCCESSFUL - all modules)
  - Tag target: v0.12.02

## Runtime Reality (Implemented)

- Authoritative server loop, zone simulation, and snapshot replication are active.
- Client rendering/UI loop is on libGDX desktop runtime.
- Mission lifecycle tracing and session-correlation logging are active.
- Siren-first onboarding flow and objective/mission affordances are active.
- NPC runtime dimensions are now authoritative over the wire (`NPCState.width/height`) and used by client render/debug hitbox overlays.
- Map input now follows explicit tap/hold semantics: `Tab` tap toggles quick map, `Tab` hold opens full map while held.
- Animation integration: stance-coupled posture readability (Yin unarmed / Yang armed) is enforced client-side â€” `EntityRenderer` routes animation key prefix from `stanceMode` directly (GDD Â§3.3), so Yin always renders unarmed and Yang always renders armed regardless of desync or offline state. Ledge corner hang-climb context and water-bank exit traversal bridge are also implemented with playtest log events.
- Solo/multiplayer campaign unification is live: `handleSoloPortalTravel()` now applies the same ability-gate + zone-migration logic as the server's `handlePortalTravel()`. Player state (health, level, xp, currency, inventory, abilities) is preserved across hub transitions; hub seeds are derived deterministically from the session seed via `HubRegistry.hubSeed()`. Campaign experience is identical whether played solo or co-op (drop-in/drop-out up to 4 players).
- Portal travel blocker fixes (v0.11.65): start-room portals removed from `LevelLayout` (exit-rooms only), render-loop race condition fixed (`refreshSoloWorldRoomCache` + `camera.snapTo` now called in `pollZoneTransition` handler). Portal travel is now stable.
- Stance animation fix (v0.11.65): `EntityRenderer` uses `hasAnyWithPrefix("player_sword_")` for Yang so all locomotion states (idle/walk/jump/crouch) display correct armed posture when sword sheets are registered.
- F9 debug ability toggle active (v0.11.65): solo mode only â€” cycles all abilities granted/cleared; HUD toast feedback.
- Mode select updated (v0.11.65): Sandbox retired, CAMPAIGN maps to solo ID, DEVELOPER replaces old solo card.
- Runtime keybinding ingestion is now live from `user_data/settings/settings.json` (`keybindings` block plus legacy `key_*` fallback), and map/debug/mission hotkeys consume the same binding table as input polling.
- Direct posture hot-swap input is now active (`select_weapon_1` / `select_weapon_2`, default `1`/`2`) with Yin-lock to unarmed and persistent Yang posture preference for runtime readability testing.
- `F1` controls overlay now renders active live bindings instead of a static key legend.
- Interaction affordance readability bridge is now active: lever/button/echo-trigger and pickup interactions queue short explicit animation feedback with `[Playtest][Interaction]` traces.
- Release/version parity gate is enforced through `tools/check_version_sync.py`.
- Solo replay playback is now routed through the Java client (`ninja-client-all.jar`) via `-Dninja.replayPath`; `ninja_dash.exe` / `demo_game.py` is no longer invoked for any launcher-initiated game operation.
- Pygame prototype extraction phase-4 cutover is complete in this repo: launcher fallback to `demo_game.py` is removed, CI/release default lanes are Java-first, and migrated prototype runtime paths now live in `VainAsher/indie-ninja-prototype`.
- **Engine Platform Phases A-C complete (2026-04-19)**: Content definition system (`ContentLoader`, `ContentRegistry`, JSON-schema-validated definitions), `GameConfig` balance constants, animation manifest + hot-reload, Tiled TMX room loader (4 templates), Yarn Spinner dialogue format (23 files), in-game DevConsole (backtick toggle, 14 commands), Gradle `buildAssets` pipeline (436 files, SHA-256). Module extraction: `:shadowascent` module created - `sim.*` and `world.*` moved out of `:core`; `EntityTypeRegistry` + `ShadowAscentEntityTypeBootstrap` added; `:core` published as `engine-core` Maven artifact to GitHub Packages. All server tests pass.
- **Engine Platform Phase D complete (2026-04-19)**: Save checksums (`savegame.sha256` SHA-256 sidecar, verified on load with corrupt-save fallback). Perf regression gate (`TickDurationRegressionTest` â€” 2000-tick run, 5 ms ceiling, `perf_baseline.json`). Multi-slot save support (`user_data/saves/slot_N/`, `SlotSelectScreen`, legacy single-slot auto-migration). `tools/validate_animation_manifest.py` validates manifest against registry at authoring time.

## Canonical Documentation Set

- [INDEX.md](INDEX.md) - top-level documentation routing
- [ROADMAP.md](ROADMAP.md) - milestone sequencing and current targets
- [CHANGELOG.md](CHANGELOG.md) - release-facing version history
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md) - launcher-first playtest contract
- [GDD.md](GDD.md) - design intent and narrative/mechanics contracts
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md) - release metadata gate
- [workflow/OPERATING_RHYTHM_AND_HABITS.md](workflow/OPERATING_RHYTHM_AND_HABITS.md) - daily/weekly/monthly operating model
- [operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md](operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md) - cross-repo control-tower handover

## Repository Process Defaults

- Plan-embedded tasks are canonical for implementation tracking.
- `indie-ninja-pipeline` is the control tower for master planning and cross-repo coordination.
- `docs/TASK_LIST.md` is historical and archived.
- Retired/stale docs move immediately to `docs/archive/retired/`.
- Archive ZIP snapshots are kept in `docs/archive/zips/` and mirrored to release assets.
- Docs freshness checks are warning-only in CI unless explicitly run in strict mode.

## Session Close-Out (2026-04-22)

- Date: 2026-04-22
- Branch + HEAD: `master @ 0b6abca`
- Current version: `v0.12.02`
- Systems touched: session-end verification evidence, handover alignment, and repo close-out hygiene confirmation.
- Validation run:
  - `python tools/check_version_sync.py` (PASS)
  - `tools/check_docs_freshness.py --emit-report` (PASS)
  - `gh run list --limit 3 --json status,conclusion,name,headSha,displayTitle,event` (CI=success for `0b6abca`; latest Release=success for `e6aa604`)
  - `gh release view v0.12.02 --json tagName,name,isDraft,isPrerelease,publishedAt,targetCommitish,assets` (release published; docs archive + client/server jars present)
- Known issue or risk: none blocking.
- Compatibility impact: replay=`no`, save=`no`, protocol=`no`.
- First action next session: implement host-authoritative hard guarantees for mission-critical pickups in multiplayer-hosted runs (guaranteed objective spawn, no pre-resolution despawn, late-join pickup state sync), then run a mission item/NPC sprite and animation readability pass.
