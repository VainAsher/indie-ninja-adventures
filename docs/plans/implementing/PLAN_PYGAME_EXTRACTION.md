---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# PLAN - Pygame Prototype Extraction

## Scope

Extract `ninja_dash.exe` and the connected Pygame prototype runtime/development lane out of this repository into a separate project, while keeping Java runtime delivery stable.

## Goal

Make `indie-ninja-adventures` a Java-first repo with no default dependency on `demo_game.py`, root python game systems, or python EXE release assets.

## Constraints

- No destructive removal before migration evidence exists.
- Releaseability for the current version line must remain intact during transition.
- Cross-repo ownership must be explicit (game repo vs new pygame repo vs launcher repo).

## Work Phases

### Phase 0 - Governance and Freeze

- [x] Record architectural decision to split python prototype.
- [x] Create extraction plan and inventory artifacts.
- [ ] Freeze new feature work in python prototype lane (bugfix/security-only).

### Phase 1 - Inventory and Boundary Contract

- [x] Finalize extraction inventory by folder, script, test suite, and release asset.
- [x] Define what remains in this repo as temporary compatibility shims.
- [x] Define final contract for launcher behavior after split.
- [x] Confirm migration window timing for launcher fallback retirement (closed 2026-04-21).

### Phase 2 - New Repo Setup and Move

- [ ] Create dedicated pygame repo and initialize docs/CI baseline.
- [ ] Move python runtime code and tests from this repo to new repo.
- [ ] Port python build specs and packaging metadata to new repo.
- [ ] Publish migration handover note and ownership mapping.

### Phase 3 - Decouple This Repo

- [x] Remove launcher fallback to `demo_game.py` entirely (migration window closed 2026-04-21).
- [x] Remove python runtime from this repo CI default lane.
- [x] Remove python EXE asset creation from this repo release workflow.
- [x] Update docs/workflows to remove python-runtime-as-current guidance.

### Phase 4 - Cleanup and Archive

- [ ] Remove temporary compatibility shims after migration window closes.
- [ ] Move split-era historical docs to archive.
- [ ] Re-run workflow/docs audit and close extraction plan.

## Validation Gates

- `python tools/check_version_sync.py`
- `python tools/check_docs_freshness.py --emit-report`
- `cd java && gradle :server:test :client:test --no-daemon`

## Rollback Plan

If extraction destabilizes release flow, pause at phase boundary, restore prior workflow lane from git history, and resume only after cross-repo contract gaps are resolved.

## Risks

- Hidden launcher expectations for legacy EXE path.
- CI breakage from mixed java/python assumptions.
- Documentation drift if routing is not updated in lockstep.
