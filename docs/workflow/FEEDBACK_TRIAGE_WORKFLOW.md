---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Feedback Triage Workflow

Reference documents:
- [PLAYTEST_PACKET_WORKFLOW.md](PLAYTEST_PACKET_WORKFLOW.md)
- [BUG_REPRO_REPLAY_WORKFLOW.md](BUG_REPRO_REPLAY_WORKFLOW.md)
- [SPRINT_WORKFLOW.md](SPRINT_WORKFLOW.md)

Workflow for converting raw bug reports, feature requests, and qualitative reactions into actionable solo-dev work.

## Rules

1. Separate breakage, clarity, feel, and preference feedback.
2. Require reproduction data for technical issues whenever possible.
3. Classify severity before scheduling work.
4. Preserve feedback that reflects emotional or tonal mismatch even when it is not a bug.

## Required Labels

- `bug`
- `feel`
- `clarity`
- `balance`
- `ux`
- `performance`
- `network`
- `narrative`
- `p0`
- `p1`
- `p2`
- `p3`
- `needs-replay`
- `needs-seed`
- `cannot-repro`

## Canonical Loop

1. Read the report.
2. Classify the report type (`bug`, `feel`, `clarity`, `balance`, `request`).
3. Assign severity.
4. Request replay/log/seed if the report is technical and under-specified.
5. Route the item:
   - hotfix
   - next iteration
   - backlog
   - monitor
6. Link the item to a plan task, release note, or bug doc when actioned.

## Severity Model

- `P0` — crash, corrupt save, progression blocker, desync
- `P1` — core mechanic unreliable, onboarding blocker, repeatable unfairness
- `P2` — annoyance, polish, local clarity issue
- `P3` — backlog or preference

## Done Criteria

- [ ] Classification applied
- [ ] Severity applied
- [ ] Missing reproduction data requested where needed
- [ ] Issue routed to the correct work lane
- [ ] Resolution linked back to version or plan item when closed

## Failure Path

If reports accumulate without clear routing:

1. Run a triage pass before new feature work.
2. Merge duplicates.
3. Elevate repeated clarity/feel complaints even when no single report looks severe.
4. Prefer fixing high-frequency friction over low-frequency novelty requests.

## Related Workflows

- [PLAYTEST_PACKET_WORKFLOW.md](PLAYTEST_PACKET_WORKFLOW.md)
- [BUG_REPRO_REPLAY_WORKFLOW.md](BUG_REPRO_REPLAY_WORKFLOW.md)
