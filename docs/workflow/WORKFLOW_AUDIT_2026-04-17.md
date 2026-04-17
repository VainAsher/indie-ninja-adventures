---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-17
version_anchor: v0.11.54
---

# Workflow Audit — 2026-04-17

Point-in-time audit of workflow adherence across the v0.11.49–v0.11.54 release window and the cross-session recovery incident that surfaced during the 2026-04-17 session.

---

## 1. Scope

This audit covers:

- Adherence to [`ITERATION_RELEASE_PROTOCOL.md`](ITERATION_RELEASE_PROTOCOL.md)
- Adherence to [`SPRINT_WORKFLOW.md`](SPRINT_WORKFLOW.md)
- Adherence to [`BRANCHING.md`](BRANCHING.md)
- Adherence to [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
- The stale-context incident (session resumed from a wrong version anchor)
- The CI formatting failure (black compliance gate)
- Process gaps and recommended safeguards

Version window reviewed: `v0.11.44` through `v0.11.54` (confirmed via `git log --oneline -30`).

---

## 2. Protocol Adherence — Findings

### 2.1 ITERATION_RELEASE_PROTOCOL — Overall: PASS with one gap

| Step | Status | Notes |
|------|--------|-------|
| 1. Sync `master` before implementing | ✅ Pass | Observed in all v0.11.44–v0.11.54 loop notes |
| 2. Implement one logical unit | ✅ Pass | Commits are scoped; no oversized batches in recent history |
| 3. Run local gates (version sync, docs freshness, build, tests) | ✅ Pass | All loop notes record gate execution |
| 4. Update docs (CHANGELOG, active plan, contracts) | ✅ Pass | Plan loop notes updated each cycle |
| 5. Commit | ✅ Pass | Conventional commit format followed (`feat/fix/docs/chore`) |
| 6. Tag with annotated tag | ✅ Pass | Annotated tags confirmed for v0.11.44–v0.11.54 |
| 7. Push commit + tag | ✅ Pass | Push confirmed in loop notes each release |
| 8. Verify CI + Release workflows | ✅ Pass | Run IDs recorded in plan for v0.11.44, v0.11.48, v0.11.54 |
| 9. Confirm release assets include JARs + docs archive ZIP | ✅ Pass | Asset list confirmed in v0.11.48 and v0.11.54 loop notes |

**Gap:** Not all intermediate patch releases (v0.11.49–v0.11.53) have explicit CI/Release run-ID records in the plan. Verification appears to have occurred but was not always transcribed.

**Recommendation:** All releases — including minor iterative patches — must record their CI/Release run IDs in the loop note. Even a one-liner suffices.

---

### 2.2 SPRINT_WORKFLOW — Overall: PASS

| Criterion | Status | Notes |
|-----------|--------|-------|
| Review plan state before starting | ✅ Pass | Each loop note confirms prior state review |
| Build scoped task list | ✅ Pass | Plan IDs (`P0-01` through `P0-10`) map to explicit checklist rows |
| Execute tasks one by one | ✅ Pass | Individual tasks committed separately in v0.11.43–v0.11.48 window |
| Commit after each logical unit | ✅ Pass | Commit granularity is appropriate |
| Update plan with completed IDs and next step | ✅ Pass | Plan updated every loop |
| Push branch progress | ✅ Pass | All master pushes confirmed |

No material gaps found in sprint cadence.

---

### 2.3 BRANCHING — Overall: PASS

| Criterion | Status | Notes |
|-----------|--------|-------|
| `v0.<minor>.<patch>` tag format only | ✅ Pass | All tags observed follow this format |
| No v1.x.x tags without alpha authorization | ✅ Pass | No v1.x.x tags exist |
| Conventional commit format | ✅ Pass | `feat/fix/docs/chore/test` prefixes used consistently |
| `master` as primary branch | ✅ Pass | All verified releases land on master |

---

### 2.4 RELEASE_CHECKLIST — Overall: PASS with one gap

| Gate | Status | Notes |
|------|--------|-------|
| Version parity gate (`check_version_sync.py`) | ✅ Pass | Run recorded in v0.11.43, v0.11.45, v0.11.47, v0.11.48 |
| Docs freshness gate (`check_docs_freshness.py`) | ✅ Pass | Run recorded in v0.11.45, v0.11.46, v0.11.48 |
| Java build + server tests | ✅ Pass | `./gradlew :server:test :client:compileJava` recorded each release |
| Python tests when tooling changed | ✅ Pass | `run_tests.py` recorded in v0.11.46 |
| CHANGELOG updated | ✅ Pass | Confirmed present in docs/CHANGELOG.md |
| Active plan updated | ✅ Pass | PLAN_SHADOW_ASCENT.md updated each loop |
| Archive action recorded | ✅ Pass | Archive ZIPs created and published |
| EXE + launcher + checksum in assets | ✅ Pass | Verified v0.11.48, v0.11.54 |
| JARs in assets | ✅ Pass | Both fat JARs confirmed in release |
| Docs archive ZIP in assets | ✅ Pass | Confirmed v0.11.48, v0.11.54 |

**Gap:** Python test gate is run inconsistently — only explicitly recorded when Python tooling changed. CI formatting gate (Black compliance) caused a failure that required a corrective commit.

---

## 3. Incident Reports

### INC-001: Stale Session Context Incident (2026-04-17)

**What happened:**
A session was resumed from an auto-summary that reported the codebase at `v0.11.18`. The actual HEAD of `master` at session start was `v0.11.54`. The session proceeded to re-implement features (respawn on death, platform collision, death overlay) that had already been shipped in earlier releases.

**Impact:**
- No production code was damaged. The re-implemented features were delivered as additive commits below the real `v0.11.54` HEAD in the DAG.
- All `v0.11.19`–`v0.11.21` commits from the stale session are historical artifacts; `v0.11.54` HEAD is intact.
- No data was lost. No branches were force-pushed. No releases were overwritten.
- Time was spent on work that was already done.

**Root cause:**
The session context summary was generated from a prior conversation that ended at `v0.11.18`. The summary was not re-verified against the actual current `version.json` at session start.

**Corrective actions taken:**
1. Spawned an Explore agent to do a full codebase review, which surfaced the true `v0.11.54` HEAD.
2. Spawned a git history agent to confirm no data loss and verify all v0.11.19–v0.11.54 features are intact.
3. This audit document is the formal record.

**Safeguards recommended:**
- **Rule:** At the start of every resumed session, read `version.json` before taking any action. If it does not match the summary's stated version, treat the session context as stale and perform a scope review before implementing.
- **Rule:** If the session summary describes an older version than the repo HEAD, do not re-implement features — first audit what is already present.

---

### INC-002: CI Failure — Black Formatting (session preceding v0.11.19)

**What happened:**
CI failed on a push to `master` because `tools/stitch_enemy_frames.py` was not Black-formatted. The `black --check .` gate in `.github/workflows/ci.yml` reported one file would be reformatted.

**Impact:**
- CI was red on master until a corrective `chore:` commit reformatted the file.
- No release assets were affected.

**Root cause:**
A Python tooling file was edited without running Black locally before commit.

**Corrective actions taken:**
Applied `python -m black tools/stitch_enemy_frames.py` and pushed a dedicated formatting commit.

**Safeguards recommended:**
- **Rule:** Any commit touching `.py` files must be preceded by `python -m black <file>` locally (or a pre-commit hook running `black --check`).
- **Recommendation:** Add a `pre-commit` hook configuration (`pre-commit-config.yaml`) to enforce Black on staged Python files before commit.

---

## 4. Process Gap Summary

| ID | Gap | Severity | Recommendation |
|----|-----|----------|----------------|
| GAP-01 | CI/Release run IDs not always recorded for intermediate patch releases | Low | Add one-liner run-ID entry to plan loop note for every tag push, even minor patches |
| GAP-02 | Stale session context not verified against `version.json` at resume | High | Read `version.json` as first action of any resumed session |
| GAP-03 | Python Black formatting not enforced locally before commit | Medium | Add `pre-commit` Black hook or include Black check in pre-commit gate script |
| GAP-04 | Python test gate (`run_tests.py`) recorded only for explicit tooling changes | Medium | Run `python run_tests.py` as part of every full release gate, not only when Python code changes |

---

## 5. Positive Observations

- The workloop discipline (plan → task list → implement → commit → update plan → push → verify) is being followed consistently. Every release from v0.11.44 through v0.11.54 has a clear loop trail in `PLAN_SHADOW_ASCENT.md`.
- Release asset completeness is strong: EXE, launcher, JARs, and docs archive ZIP present in confirmed releases.
- Version parity and docs freshness gates are running reliably on release days.
- The feel-first design audit rule (added 2026-04-14) is being applied — loop notes record stance/Flow/Lantern impact for relevant changes.
- Commit messages include `plan_id`, `scope`, `reason`, `risk` as specified by the workloop operating model.

---

## 6. Next Review

This audit should be re-run at the `v0.12.0` milestone boundary (or earlier if a new incident surfaces). Update the `last_updated` frontmatter and append new findings as a dated section below.
