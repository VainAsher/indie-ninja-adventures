---
doc_type: index
status: living
owner: core-team
last_updated: 2026-05-01
version_anchor: v0.13.17
replaces: docs/INDEX.md (2026-03-28)
---

# Documentation Index

This index tracks only the active documentation system for the Java v0.13.x line.

## Core Canonical

- [PLAYABLE_TRUTH.md](PLAYABLE_TRUTH.md) — honest playable state, G0 golden route, tester scope
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [ROADMAP.md](ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)
- [GDD.md](GDD.md)
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md)
- [GAMEPLAY_KPI_TARGETS.md](GAMEPLAY_KPI_TARGETS.md) — Phase 2 stance/Flow numeric KPI targets (living, update each tuning loop)
- [BALANCE_LOG.md](BALANCE_LOG.md) — tuning loop entries; one per loop, referenced from KPI targets
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md)
- [PLAYTEST_HANDOVER_v0.11.69.md](PLAYTEST_HANDOVER_v0.11.69.md) — active playtest handover (v0.11.69)

## Plans

- Developing:
  - [plans/developing/PLAN_ANIMATION_INTEGRATION.md](plans/developing/PLAN_ANIMATION_INTEGRATION.md)
  - [plans/developing/PLAN_CODE_REVIEW_AND_CLEANUP.md](plans/developing/PLAN_CODE_REVIEW_AND_CLEANUP.md)
  - [plans/developing/PLAN_WORKFLOW_ALIGNED_IMPROVEMENT_CHECKLIST.md](plans/developing/PLAN_WORKFLOW_ALIGNED_IMPROVEMENT_CHECKLIST.md)
  - [plans/developing/PLAN_ENEMY_ANIMATION.md](plans/developing/PLAN_ENEMY_ANIMATION.md)
  - [plans/developing/animation_pipeline_plan.md](plans/developing/animation_pipeline_plan.md)
  - [plans/developing/perf_optimisation_plan.md](plans/developing/perf_optimisation_plan.md)
  - [plans/developing/perf_render_gap_plan.md](plans/developing/perf_render_gap_plan.md)
- Implementing:
  - [plans/implementing/PLAN_SHADOW_ASCENT.md](plans/implementing/PLAN_SHADOW_ASCENT.md)
  - [plans/implementing/PLAN_CUTSCENE_MANAGER.md](plans/implementing/PLAN_CUTSCENE_MANAGER.md)
  - [plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md](plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md)
  - [plans/implementing/PLAN_WORLDGEN_VISION_EXECUTION.md](plans/implementing/PLAN_WORLDGEN_VISION_EXECUTION.md) — worldgen schema hardening, traversal contracts, Act I variety, quality scoring v2
  - [plans/implementing/PLAN_WORLDGEN_RUNTIME_ADOPTION.md](plans/implementing/PLAN_WORLDGEN_RUNTIME_ADOPTION.md) — RFC stub: promote worldgen validation to runtime gating
- Completed:
  - [plans/completed/BRIEF_2026-04-21_SYSTEMS_DOCS_JAVA_REWRITE.md](plans/completed/BRIEF_2026-04-21_SYSTEMS_DOCS_JAVA_REWRITE.md)
  - [plans/completed/PLAN_PHASE3_AUTHORITATIVE_SERVER.md](plans/completed/PLAN_PHASE3_AUTHORITATIVE_SERVER.md)
  - [plans/completed/PLAN_MULTIPLAYER_HOTJOIN_RECONNECT_PERSISTENCE.md](plans/completed/PLAN_MULTIPLAYER_HOTJOIN_RECONNECT_PERSISTENCE.md)
  - [plans/completed/PLAN_N4_L2.md](plans/completed/PLAN_N4_L2.md)
  - [plans/completed/launcher-enhancement-plan.md](plans/completed/launcher-enhancement-plan.md)
  - [plans/completed/remote_player_anim_sync_plan.md](plans/completed/remote_player_anim_sync_plan.md)
  - [plans/completed/remote_ghost_smoothing_v2_plan.md](plans/completed/remote_ghost_smoothing_v2_plan.md)

## Workflow and Operations

### Release and Sprint

- [workflow/ITERATION_RELEASE_PROTOCOL.md](workflow/ITERATION_RELEASE_PROTOCOL.md)
- [workflow/RELEASE_CHECKLIST.md](workflow/RELEASE_CHECKLIST.md)
- [workflow/SPRINT_WORKFLOW.md](workflow/SPRINT_WORKFLOW.md)
- [workflow/OPERATING_RHYTHM_AND_HABITS.md](workflow/OPERATING_RHYTHM_AND_HABITS.md)
- [workflow/BRANCHING.md](workflow/BRANCHING.md)
- [operations/CI_CD_PLAN.md](operations/CI_CD_PLAN.md)
- [operations/PYGAME_MIGRATION_HANDOVER.md](operations/PYGAME_MIGRATION_HANDOVER.md)
- [operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md](operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md)

### Session and Daily Loop

- [workflow/SESSION_START_WORKFLOW.md](workflow/SESSION_START_WORKFLOW.md)
- [workflow/SESSION_END_WORKFLOW.md](workflow/SESSION_END_WORKFLOW.md)
- [workflow/PRE_COMMIT_LOCAL_GATES.md](workflow/PRE_COMMIT_LOCAL_GATES.md)
- [workflow/DAILY_SMOKE_WORKFLOW.md](workflow/DAILY_SMOKE_WORKFLOW.md)
- [workflow/ONEDRIVE_BUILD_RECOVERY.md](workflow/ONEDRIVE_BUILD_RECOVERY.md) — recovery steps when OneDrive locks Gradle output dirs

### Quality Gates

- [workflow/READY_DONE_WORKFLOW.md](workflow/READY_DONE_WORKFLOW.md)
- [workflow/TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md](workflow/TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md)
- [workflow/DEBUG_EVIDENCE_CAPTURE.md](workflow/DEBUG_EVIDENCE_CAPTURE.md)
- [workflow/PR_AND_REVIEW_WORKFLOW.md](workflow/PR_AND_REVIEW_WORKFLOW.md)
- [workflow/GOLDEN_PATH_REGRESSION.md](workflow/GOLDEN_PATH_REGRESSION.md)

### Compatibility and Replay

- [workflow/COMPATIBILITY_AND_MIGRATION_WORKFLOW.md](workflow/COMPATIBILITY_AND_MIGRATION_WORKFLOW.md)
- [workflow/REPLAY_AND_DESYNC_TRIAGE.md](workflow/REPLAY_AND_DESYNC_TRIAGE.md)

### Playtest and Feedback

- [workflow/PLAYTEST_PACKET_WORKFLOW.md](workflow/PLAYTEST_PACKET_WORKFLOW.md)
- [workflow/FEEDBACK_TRIAGE_WORKFLOW.md](workflow/FEEDBACK_TRIAGE_WORKFLOW.md)

### Documentation and Architecture

- [workflow/ARCHITECTURE_AND_SPEC_SYNC.md](workflow/ARCHITECTURE_AND_SPEC_SYNC.md)
- [workflow/DECISION_RECORD_WORKFLOW.md](workflow/DECISION_RECORD_WORKFLOW.md)
- [workflow/DEVLOG_AND_MARKETING_CAPTURE.md](workflow/DEVLOG_AND_MARKETING_CAPTURE.md)

### Cross-Repo

- [workflow/CROSS_REPO_COORDINATION.md](workflow/CROSS_REPO_COORDINATION.md)

### Audits

- [workflow/WORKFLOW_AUDIT_2026-04-17.md](workflow/WORKFLOW_AUDIT_2026-04-17.md)

## Inspiration Studies

- [inspiration/INSPIRATION_SYNTHESIS.md](inspiration/INSPIRATION_SYNTHESIS.md) — **Master synthesis: all four games, all lessons, organised by design domain — start here**
- [inspiration/INSPIRATION_PRINCE_OF_PERSIA_TRILOGY.md](inspiration/INSPIRATION_PRINCE_OF_PERSIA_TRILOGY.md) — PoP Sands of Time trilogy: movement grammar, flow protection, combat integration, tonal spine, architectural memory
- [inspiration/INSPIRATION_CASTLEVANIA_SYMPHONY_OF_THE_NIGHT.md](inspiration/INSPIRATION_CASTLEVANIA_SYMPHONY_OF_THE_NIGHT.md) — SOTN: place as protagonist, Alucard/Aen parallel, ability callbacks, gothic contrast, layered secrets, expressive progression
- [inspiration/INSPIRATION_GOD_OF_WAR.md](inspiration/INSPIRATION_GOD_OF_WAR.md) — GoW: weight as philosophy, weapon identity, mythic bosses as arguments, controlled rage, companion as character reveal, power with consequence
- [inspiration/INSPIRATION_SHINOBI_SERIES.md](inspiration/INSPIRATION_SHINOBI_SERIES.md) — Shinobi: fragile lethality, target priority, controlled aggression, Akujiki philosophy, silhouette clarity, three-beat combat loop

## Skills and Workflow Guide

- [WORKFLOW_AND_SKILLS_GUIDE.md](WORKFLOW_AND_SKILLS_GUIDE.md) — how to use skills, workflows, and agents with Claude Code / Codex

## Developer Documentation

- [dev/JAVA_ARCHITECTURE.md](dev/JAVA_ARCHITECTURE.md)
- [dev/JAVA_SETUP.md](dev/JAVA_SETUP.md)
- [QUICK_START.md](QUICK_START.md)
- [guides/WORLDGEN_SECTION_AUTHORING.md](guides/WORLDGEN_SECTION_AUTHORING.md)

## Systems (Java Canonical)

- [systems/AUDIO.md](systems/AUDIO.md)
- [systems/CAMPAIGN.md](systems/CAMPAIGN.md)
- [systems/COMPANIONS.md](systems/COMPANIONS.md)
- [systems/CUTSCENE.md](systems/CUTSCENE.md)
- [systems/ENDINGS.md](systems/ENDINGS.md)
- [systems/LOOT.md](systems/LOOT.md)
- [systems/MECHANICS.md](systems/MECHANICS.md)
- [systems/MODDING.md](systems/MODDING.md)
- [systems/PERFORMANCE.md](systems/PERFORMANCE.md)
- [systems/RENDERING.md](systems/RENDERING.md)
- [systems/REPLAY.md](systems/REPLAY.md)
- [systems/SETTINGS.md](systems/SETTINGS.md)
- [systems/WORLD_GEN.md](systems/WORLD_GEN.md)

## Reviews and Audits

- [reviews/2026-03-25/ROADMAP_AND_PLAN.md](reviews/2026-03-25/ROADMAP_AND_PLAN.md)
- [archive/audits/](archive/audits/)

## Decisions

- [decisions/INDEX.md](decisions/INDEX.md)
- [decisions/2026-04-21_pygame-prototype-extraction.md](decisions/2026-04-21_pygame-prototype-extraction.md)
- [decisions/2026-04-21_java-systems-docs-canonicalization.md](decisions/2026-04-21_java-systems-docs-canonicalization.md)

## Templates

- [templates/BUG_REPORT.md](templates/BUG_REPORT.md)
- [templates/ISSUE_TEMPLATE.md](templates/ISSUE_TEMPLATE.md)
- [templates/PLAYTEST_REPORT.md](templates/PLAYTEST_REPORT.md)

## Archives

- [archive/retired/](archive/retired/)
- [archive/retired/2026-04-21_v0.11.71_pygame-extraction/](archive/retired/2026-04-21_v0.11.71_pygame-extraction/)
- [archive/retired/2026-04-21_v0.11.71_python-systems-docs/](archive/retired/2026-04-21_v0.11.71_python-systems-docs/)
- [archive/zips/INDEX.md](archive/zips/INDEX.md)
- [HANDOVER.md](HANDOVER.md) (redirect)
- [DEVLOG.md](DEVLOG.md) (rolling index)
