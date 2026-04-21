---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Architecture and Spec Sync Workflow

Reference documents:
- [docs/GDD.md](../GDD.md)
- [docs/dev/JAVA_ARCHITECTURE.md](../dev/JAVA_ARCHITECTURE.md)
- [docs/workflow/ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)
- [docs/workflow/COMPATIBILITY_AND_MIGRATION_WORKFLOW.md](COMPATIBILITY_AND_MIGRATION_WORKFLOW.md)

Workflow for keeping design truth, implementation truth, and technical specs aligned as systems evolve.

## Rules

1. Design intent and implementation detail are different documents and must stay separated.
2. `docs/GDD.md` is design truth.
3. `docs/dev/JAVA_ARCHITECTURE.md` plus active workflow contracts are implementation/spec truth.
4. Aspirational ideas must be labeled as planned, not written as implemented.
5. Shipped schema/format changes require spec updates in the same work loop.
6. Runtime reality must not drift behind polished design wording for long.

## Update Triggers

Update sync whenever any of the following occur:

- major system architecture change
- mission/schema/serialization format change
- CI/CD path or release pipeline change
- GDD addendum changes implementation-facing constraints
- runtime onboarding/observability contracts change
- system deprecation changes real module boundaries

## Canonical Loop

1. Identify whether the change is:
   - design intent
   - implementation truth
   - both
2. Update the primary affected document first.
3. Update linked docs that depend on the changed truth.
4. Add explicit status wording when implementation is partial or planned.
5. Validate that no doc now overclaims what the runtime actually does.
6. Record major sync-impacting choices in `docs/decisions/INDEX.md` when needed.

## Truth Boundary Examples

`docs/GDD.md` should answer:
- what the game is trying to express
- intended pillars, loops, and experience
- target structure and system purpose

Technical docs should answer:
- how the system is implemented now
- what data/schema/contracts exist
- what CI/CD or mission-format rules currently apply

## Done Criteria

- [ ] Changed system has updated canonical docs
- [ ] Planned vs implemented status is explicit
- [ ] Specs reflect current schema/contracts
- [ ] No technical doc is being replaced by vague design prose
- [ ] No design doc claims runtime support that does not exist

## Failure Path

If docs disagree on what is implemented:

1. Prefer runtime/spec truth over aspirational wording.
2. Mark the design item as planned/partial if needed.
3. Update technical docs to reflect actual current behavior.
4. Create a decision note if the mismatch revealed a real scope change.

## Related Workflows

- [COMPATIBILITY_AND_MIGRATION_WORKFLOW.md](COMPATIBILITY_AND_MIGRATION_WORKFLOW.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
