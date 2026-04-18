---
doc_type: workflow
status: living
owner: design-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Devlog and Marketing Capture Workflow

Reference documents:
- [docs/DEVLOG.md](../DEVLOG.md)
- [docs/CHANGELOG.md](../CHANGELOG.md)
- [README.md](../../README.md)

Workflow for capturing development progress in a form that can later become public-facing updates without losing the project voice.

## Rules

1. Not every internal task is marketing-worthy.
2. Capture public-facing moments as they happen instead of reconstructing them at release time.
3. Focus on player-visible progress, emotional tone, and why the work matters.
4. Do not publish raw internal notes without rewriting them into player language.
5. Every capture item should answer at least one of:
   - what changed for the player
   - why this mattered
   - what problem was solved
   - what visual/system moment is worth showing

## Capture Categories

- visual moment
- feel improvement
- onboarding clarity improvement
- performance win
- boss/mission reveal
- world/hub evolution milestone
- tooling or pipeline improvement worth community trust
- narrative-aligned design insight

## Canonical Loop

1. During implementation or playtest, note public-worthy moments.
2. Record them in a short capture block:
   - build/version
   - feature/system
   - player-facing impact
   - evidence available (screenshot/clip/log/replay)
3. Move the best captures into `docs/DEVLOG.md`.
4. Flag any player-visible shipped item for `docs/CHANGELOG.md`.
5. Carry only the strongest public-facing items forward into release notes/community wording.

## Capture Block Minimum

- Date
- Version
- System
- What changed
- Why it matters to players
- Suggested screenshot/clip moment
- Confidence (`internal only` / `public-safe draft`)

## What Not To Surface Directly

- vague internal task churn
- unresolved design debates
- private operational details
- raw bug counts without context
- speculative promises for uncommitted features

## Done Criteria

- [ ] Meaningful progress moments were captured during the work, not reconstructed later
- [ ] `docs/DEVLOG.md` contains player-relevant narrative, not only task lists
- [ ] Public-safe captures are separated from internal-only notes
- [ ] Release candidates already have material ready for public wording

## Failure Path

If a release or weekly update has nothing clear to say publicly:

1. Review whether capture happened during implementation.
2. Check whether notes describe internal activity instead of player impact.
3. Narrow the next capture pass to one visual/system highlight per work session.

## Related Workflows

- [RELEASE_NOTES_AND_PUBLIC_COMMS.md](RELEASE_NOTES_AND_PUBLIC_COMMS.md)
- [DOCUMENTATION_ROUTING_WORKFLOW.md](DOCUMENTATION_ROUTING_WORKFLOW.md)
