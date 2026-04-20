---
doc_type: guide
status: living
owner: VainAsher
last_updated: 2026-04-20
version_anchor: v0.11.70
---

# Shadow Ascent — Workflow, Skills, and Agent Guide

Practical guide for using the workflow system, Claude skills, and agent chains with any AI coding tool (Claude Code, Codex, Cursor, Copilot, etc.).

---

## What Was Just Installed

| Component | Location | Purpose |
|-----------|----------|---------|
| `CLAUDE.md` | repo root | Project context loaded by Claude at every session start |
| 7 workflow docs | `docs/workflow/` | Policy: what to do and when |
| 6 Claude skills | `.claude/skills/` | Execution: step-by-step process helpers invokable as `/skill-name` |
| (Tier 2) 5 agents | `.claude/agents/` | Role-based subagent chains for complex work |

**Workflows are the law. Skills are how you invoke the law. Agents are who enforces it.**

---

## The Core Mental Model

```
You → /task-intake → scope the work → implement → /ready-done-check → commit
         ↑                                              ↑
    (before touching code)                      (before declaring done)
```

For bugs:
```
Bug appears → /debug-evidence → evidence bundle → /replay-desync-triage (if replay/desync) → fix → /ready-done-check
```

For risky changes:
```
/task-intake → /compatibility-migration (if touching save/replay/protocol) → implement → /ready-done-check
```

---

## Part 1: Using Skills with Claude Code

Skills live in `.claude/skills/<name>/SKILL.md`. In Claude Code you invoke them as slash commands.

### The 6 Installed Skills

#### `/project-operating-context`

**When:** Start of any session, or when you're unsure what docs to trust.

```
/project-operating-context
```

Claude will read README.md, docs/INDEX.md, and docs/CURRENT_STATE.md and give you a repo summary — confirmed version, active milestone, canonical docs, and known constraints. Use this any time a session resumes from a summary that might be stale.

**This is the INC-001 prevention tool.** The stale-context incident (re-implementing v0.11.19–v0.11.54 features) happened because the session resumed without verifying `version.json`. This skill makes that verification the first act.

---

#### `/task-intake`

**When:** Before writing any code, for any task.

```
/task-intake Add Yin stance visual feedback to the HUD
```

Claude produces an Implementation Brief:
- Goal (one sentence)
- Player-facing impact
- Systems touched
- Risks (persistence, protocol, replay, content format)
- Required tests
- Docs to update
- Rollback plan
- Escalation conditions

**Why this matters:** It forces scope definition before you start. Without it, "add HUD feedback" silently expands into touching the renderer, the FSM, and the EventBus with no plan. The brief is also what you hand to Codex or any other tool — it becomes the prompt.

---

#### `/ready-done-check`

**When:** Before starting (are we ready?) and before committing (are we done?).

**Ready check — before branching or coding:**
```
/ready-done-check ready
```
Claude checks: Is the behavior clear? Is the canonical doc identified? Is the acceptance test known? Refuses to call it ready if any condition is missing.

**Done check — after implementation:**
```
/ready-done-check done
```
Claude checks: Did it compile? Did tests pass? Was the smoke path verified? Were docs updated? Was a changelog/devlog decision made? Was evidence attached for runtime behavior changes?

**Rule:** "Code written" is not done. This skill enforces that.

---

#### `/debug-evidence`

**When:** Any time a bug appears — from your own testing or from playtest feedback.

```
/debug-evidence player clips through wall after dash in ice biome
```

Claude walks you through capturing:
- Version and commit
- Exact reproduction steps
- Expected vs actual behavior
- Log excerpts
- Replay path if available
- Screenshot/video if UI-related

The output is an evidence bundle you can file in the feedback repo, pass to a second session, or use as a Codex prompt.

**Rule:** "It broke" is not a valid bug report. This skill enforces that.

---

#### `/replay-desync-triage`

**When:** A replay doesn't reproduce expected behavior, or frame-hash / state divergence is reported.

```
/replay-desync-triage replays/bugs/v0.11.61/2026-04-18_physics_wall-clip
```

Claude classifies the issue across four lanes:
- Local gameplay bug (replay reproduces the same wrong behavior)
- Replay ingestion issue (replay can't reproduce the original at all)
- Protocol/state desync (server and client disagree on authoritative state)
- Insufficient evidence (identifiers or artifacts are missing)

Because your server runs at 60Hz with delta encoding and frame-hash checks, a desync in one lane has completely different fixes from a desync in another. This skill prevents you from guessing which lane you're in.

---

#### `/compatibility-migration`

**When:** Any task that touches persistence, schema, serialization, networking, versioning, or offline mode.

```
/compatibility-migration adding offline local save for solo mode
```

Claude produces a compatibility matrix:
- Save lane: compatible / breaking?
- Replay lane: compatible / breaking?
- Protocol lane: compatible / breaking?
- Schema lane: compatible / breaking?
- Migration required? Version bump required? Rollback plan?

**This is mandatory before any work on the persistence layer, the server protocol, or `version.json`.**

---

## Part 2: Using Workflows

Workflows live in `docs/workflow/`. They are policy documents — what must happen, in what order, with what evidence.

### Session Rituals (Run Every Session)

#### SESSION_START_WORKFLOW — Do this first, every time

**The three-step rule:**
1. Read `version.json` — confirm the actual current version
2. Read `docs/CURRENT_STATE.md` — confirm runtime truth
3. Read the active implementation plan and `git log --oneline -10`

Then write a 3-line session note before touching code:
```
Target: [what you're building today]
Reason: [why this, why now]
Stop condition: [what would make you stop and reassess]
```

This is the single workflow most worth adopting. It prevents the costliest class of error: resuming from stale context and re-doing work that was already shipped.

**With Claude Code:**
```
Read version.json and CURRENT_STATE.md, then confirm the active milestone 
and last 10 commits. Write a session note for today's work.
```

**With Codex / any tool:**
Paste version.json content, CURRENT_STATE.md, and `git log --oneline -10` output as context before giving any implementation task. This is equivalent — you're manually doing what `SESSION_START_WORKFLOW` formalizes.

---

#### SESSION_END_WORKFLOW — Do this last, every time

Before ending any session, record:
- What changed
- Files/systems touched
- Commands run and their results
- Known issues and blockers
- **The next concrete action** (specific, not "continue work")
- Compatibility impact: replay? save? protocol? (yes/no each)

Without this, the next session starts blind. With it, you can resume in 30 seconds even after a week away.

**The handover note minimum:**
```
Date: 2026-04-18
Branch: master | HEAD: c279746
Version: v0.11.61
Systems touched: HUD, PlayerStateRenderer
Validation: ./gradlew test — PASS
Known issue: none
Compatibility: replay=no, save=no, protocol=no
Next action: implement Yin stance circle draw call in HUDRenderer.java:284
```

---

#### PRE_COMMIT_LOCAL_GATES — Run before every commit

Fast gates (pre-commit, seconds):
```bash
python -m black --check tools/
python tools/check_version_sync.py
```

Full gates (pre-push, ~1 min):
```bash
python tools/check_version_sync.py
python tools/check_docs_freshness.py --emit-report
cd java && ./gradlew test --no-daemon
```

This workflow directly fixes INC-002 (the CI Black failure). Any commit touching `.py` files must pass Black locally first. CI is not your first formatting gate.

---

### Quality Gates

#### READY_DONE_WORKFLOW

**Ready = allowed to start coding.** All five conditions must be true:
- Desired behavior is clear
- Canonical doc identified
- Dependencies known
- Target branch known
- Acceptance test known

**Done = allowed to commit and call it shipped.** All six conditions must be true:
- Code compiles
- Tests passed
- Smoke path checked
- Docs updated (or explicitly marked not needed)
- Changelog/devlog decision made
- Evidence attached if runtime behavior changed

Use `/ready-done-check` to run this as a skill rather than manually.

---

#### DEBUG_EVIDENCE_CAPTURE

Every bug report — from your own testing, from a playtest report, from the feedback repo — must include:
- Version + branch/commit
- Exact reproduction steps
- Expected vs actual
- Log excerpt
- Replay path if available

File this in `indie-ninja-feedback` with the evidence bundle. Use `/debug-evidence` to capture it during a Claude Code session.

---

### Compatibility Workflows

#### COMPATIBILITY_AND_MIGRATION_WORKFLOW

Trigger this any time a task touches:
- PostgreSQL schema (HikariCP/Jackson persistence)
- Redis cache shape
- Netty protocol fields
- Replay format / `InputRecorder` / `ReplayPlayer`
- `version.json` or `min_launcher_version`
- Offline/solo mode local storage

The five compatibility lanes: save / replay / protocol / schema / public version.

For each lane: compatible, conditionally compatible, or breaking. If breaking — migration plan, version bump, release note, docs update. If unknown — stop and classify before merging.

---

#### REPLAY_AND_DESYNC_TRIAGE

Replay naming convention:
```
replays/bugs/<version>/<date>_<system>_<short-label>
```

Example: `replays/bugs/v0.11.61/2026-04-18_physics_wall-clip`

Every replay bundle must include: version, build date, branch/commit, session id, seed/world id, expected result, observed result.

Use `/replay-desync-triage` to classify before attempting a fix.

---

## Part 3: Using with Codex

Codex (OpenAI's coding agent in the terminal) doesn't read your `.claude/` folder, but it reads everything else in your repo. Here's how to get the same process discipline out of it.

### Giving Codex a Session Start Context

Before any Codex task, paste this block into the prompt:

```
Context:
- Project: Shadow Ascent (Java 21 + libGDX + Netty authoritative server)
- Version: [paste version.json content]
- Active milestone: [paste relevant section from PLAN_SHADOW_ASCENT.md]
- Recent commits: [paste git log --oneline -10]
- Current state: [paste docs/CURRENT_STATE.md summary section]

Task: [your implementation request]

Constraints:
- Smallest safe change only
- Do not touch persistence, network protocol, or replay format without flagging compatibility
- Update CHANGELOG.md and the active plan after the change
- Tests must pass before declaring done
```

This manually replicates what `SESSION_START_WORKFLOW` + `CLAUDE.md` + `/task-intake` do automatically in Claude Code.

### Giving Codex an Implementation Brief

Run `/task-intake` in Claude Code first, then paste the resulting Implementation Brief as the Codex prompt. Codex gets:
- A scoped, single-sentence goal
- The systems it's allowed to touch
- The risks it must not create
- The acceptance test it must satisfy

This prevents Codex from wandering into unrelated systems.

### Reviewing Codex Output

After Codex makes changes, run `/ready-done-check done` in Claude Code. Paste the diff as context. Claude will verify the done checklist and flag missing tests, missing docs, or unintended scope creep.

---

## Part 4: Using with Cursor / Copilot / Other Tools

These tools read your codebase via their own indexing. The key integration point is `CLAUDE.md` — several AI tools (Cursor, Aider, etc.) respect `CLAUDE.md` as a project instruction file. Even if a tool doesn't load it automatically, you can paste it at the start of a session.

The workflow docs in `docs/workflow/` are plain markdown — paste any of them as system context for any tool that supports system prompts or project instructions.

---

## Part 5: Agents (Installed)

Five agents are now in `.claude/agents/`. In Claude Code, invoke them by asking Claude to act as a specific agent, or by referencing the chain you need.

### When to Use Agents vs Skills

| Situation | Use |
|-----------|-----|
| Routine single-system task | `/task-intake` → implement → `/ready-done-check` |
| New milestone start | `coordinator` agent |
| Bug with unclear root cause | `coordinator → debug → implementation → review` |
| Cross-repo change | `coordinator` → `/cross-repo-coordination` |
| Workflow / docs system change | `coordinator → process-librarian → review` |
| Routine docs update | `/docs-routing` |
| New skill or workflow needed | `/workflow-skill-author` |

### Invoking an Agent in Claude Code

```
Use the coordinator agent. Task: implement solo offline save mode
```

Or for a full chain:

```
Run the coordinator → implementation → review chain for this task:
[your task description]
```

### The Coordinator Agent

Scope before code. The coordinator produces exactly:

1. Task summary (one scope-controlled paragraph)
2. Canonical docs to read
3. Systems touched
4. Risk classification (low / medium / high)
5. Cross-repo impact
6. Recommended next agent
7. Required tests and evidence
8. Docs likely to update
9. Escalation conditions

**Use it for anything vague, risky, or cross-repo.** Skip it for clearly bounded single-system tasks — the skills cover those.

### The Debug Agent

Use instead of guessing. Input: version, branch, repro steps, logs, replay path. Output: evidence summary, likely systems, classification, next debug step, escalation decision.

```
Use the debug agent. [paste repro steps + logs + version]
```

### The Process Librarian Agent

Use when you need to add, update, or retire a workflow or skill without creating drift or duplication.

```
Use the process-librarian agent. I want to add a new workflow for [X].
```

---

## Part 6: Tier 2 Workflows (Now Installed)

### DAILY_SMOKE_WORKFLOW

Run at the start of any active dev day — not just session start. A quick sanity check that the build is clean before you begin work.

Minimum smoke:
```bash
cd java && ./gradlew :server:test :client:compileJava --no-daemon
python launcher/launcher.py  ← confirm launcher connects
```

If the smoke fails before you've written a line, the failure pre-dates your session. Record it in the session note and investigate before implementing.

---

### PLAYTEST_PACKET_WORKFLOW

Use this before and after each playtest session (you're in active playtest iteration now — v0.11.61–63 are all PLAYTEST-scope).

**Before playtest:** Build the packet:

- Current version from `version.json`
- Known issues list from `indie-ninja-feedback`
- Specific scenarios to test (golden path + targeted regression)
- Capture method: replay paths, log destination, screenshot instructions

**After playtest:** File the evidence:

- Use `/debug-evidence` for each bug found
- Update `indie-ninja-feedback` with evidence bundles
- Run `/feedback-triage` to decide what becomes a fix vs backlog

---

### GOLDEN_PATH_REGRESSION

Run this before any milestone release tag. It's a structured walkthrough of the full player experience — not just unit tests.

The golden path for Shadow Ascent:

1. Launch via `python launcher/launcher.py`
2. Hub loads and Siren onboarding triggers
3. First encounter (combat + ability acquisition)
4. Map navigation across biomes
5. Save and reload — inventory/progress intact
6. Replay playback of a known good session
7. Server reconnection (if multiplayer path active)

Document pass/fail per step. Attach replay. This is the evidence that supports a release tag.

---

### FEEDBACK_TRIAGE_WORKFLOW

For issues filed in `indie-ninja-feedback`. Run this weekly or after each playtest.

Triage each issue:
- Reproducible? → `/debug-evidence` if not already evidenced
- Severity: P0 (blocker) / P1 (this sprint) / P2 (backlog) / wont-fix
- Scope: single-system vs cross-system
- If replay/desync → `/replay-desync-triage`
- Close duplicates, link related issues

Output: a triage note in the feedback repo and an updated backlog in `indie-ninja-pipeline`.

---

### ARCHITECTURE_AND_SPEC_SYNC

Run this when `docs/dev/JAVA_ARCHITECTURE.md` may have drifted from the codebase — after any milestone that touched ECS, networking, persistence, or world gen.

The sync check:
1. Read `JAVA_ARCHITECTURE.md` system descriptions
2. Read the actual implementation files for each described system
3. Flag where the doc is stale, missing, or wrong
4. Update the doc — do not duplicate content elsewhere

**Do not defer this.** Stale architecture docs are the root cause of scope-creep bugs where Claude or Codex touches the wrong system because the doc said it was different.

---

### DECISION_RECORD_WORKFLOW

When you make a significant architectural or design decision, record it. The format is minimal:

```markdown
## Decision: [title] — [date]
Context: [what forced this choice]
Decision: [what you decided]
Consequences: [what this enables or closes off]
Alternatives considered: [what you rejected and why]
```

File in `docs/decisions/` (create if needed) or append to a running `DECISIONS.md`. Reference the record in commit messages with `decision=<id>`.

Use `/workflow-skill-author` to create new decision records as skills if the pattern repeats.

---

### DEVLOG_AND_MARKETING_CAPTURE

`docs/DEVLOG.md` exists but has no process governing when to update it. This workflow defines the trigger:

**Update DEVLOG.md when:**

- A milestone is tagged
- A playtest session produces notable feedback
- A significant system ships (boss AI, narrative FSM, hub evolution)
- A public-facing change is worth communicating to the launcher audience

**Format per entry:**

- Version anchor
- One-paragraph player-facing summary (what changed, why it matters)
- One screenshot or GIF path if visual
- Link to the GitHub release

This feeds `indie-ninja-launcher` GitHub Pages and any future devlog/social posts.

---

### CROSS_REPO_COORDINATION

When a change in `indie-ninja-adventures` has surface area in another repo, record the handoff explicitly before closing the task.

The four-repo handoff map:

| Change type | Also touches |
| --- | --- |
| New release tag | `indie-ninja-launcher` (update min_launcher_version if needed) |
| New public bug category | `indie-ninja-feedback` (update issue templates) |
| Sprint plan change | `indie-ninja-pipeline` (update triage/sprint docs) |
| Player-facing feature | `indie-ninja-launcher` (update GitHub Pages / guides) |

Use `/cross-repo-coordination` before closing any task that crosses a repo boundary.

---

## Part 7: Tier 2 Skills (Now Installed)

### `/gameplay-tuning-change`

**When:** Any change to damage values, enemy stats, speed, jump height, lethality, KO thresholds, timing windows.

Produces a Tuning Note:

- What changed (system + specific value)
- Before/after values
- Player-facing impact
- Test scenario
- Rollback note

These are currently especially relevant — v0.11.69 active playtest is targeting combat feel and balance.

---

### `/content-schema-change`

**When:** Any change to JSON/schema for missions, dialogue, trials, room types, or content definitions.

Checks: schema backward compatibility, migration need, replay impact, content tooling impact.

---

### `/pr-review`

**When:** Before creating a PR or before merging.

Produces a structured review:

- Scope coherence
- Missing tests or evidence
- Missing docs updates
- Compatibility observations
- Merge risk
- Ready yes/no

---

### `/cross-repo-coordination`

**When:** A task touches more than one of the four repos.

Produces a handoff record with: which repos are affected, what must happen in each, in what order, and who owns each step.

---

### `/docs-routing`

**When:** You're about to create a new doc and aren't sure where it belongs, or you suspect a doc is duplicating an existing canonical source.

Routes content to the correct location in the docs tree and flags duplication.

---

### `/repo-hygiene`

**When:** The repo accumulates stale branches, orphaned docs, or unclassified legacy files.

Produces a hygiene audit: active / archive / quarantine / delete-candidate classification for each flagged artifact.

---

### `/escalation-stop-work`

**When:** A task hits a condition that cannot be resolved safely — canonical docs conflict, unknown save/replay compatibility, cross-repo ownership unclear.

Produces a stop-work record: what condition was hit, what evidence exists, what must be resolved before work can resume.

---

### `/workflow-skill-author`

**When:** You need to add a new workflow or skill — after spotting a recurring process that has no doc yet.

Guides you through authoring a new `SKILL.md` or workflow markdown using the repo templates, then hands off to `process-librarian` for doc routing and index update.

---

## Quick Reference Card (Full System)

```
Every session start:
  cat version.json
  read docs/CURRENT_STATE.md
  git log --oneline -10
  Write 3-line session note (target / reason / stop condition)
  → /project-operating-context if context is uncertain

Before any task:
  → /task-intake <description>
  For risky/vague/cross-repo: use coordinator agent first

Before touching save/replay/protocol/schema:
  → /compatibility-migration <description>

After any bug appears:
  → /debug-evidence <description>
  → /replay-desync-triage <path>  (if replay/desync involved)

Before a playtest:
  → PLAYTEST_PACKET_WORKFLOW (build packet)

After a playtest:
  → /debug-evidence per bug
  → FEEDBACK_TRIAGE_WORKFLOW (triage and file)

After any tuning change (damage / speed / stats):
  → /gameplay-tuning-change

Before a PR or merge:
  → /pr-review

Before a milestone release tag:
  → GOLDEN_PATH_REGRESSION (structured playthrough)
  python tools/check_version_sync.py
  python tools/check_docs_freshness.py --emit-report

Before committing:
  python -m black --check tools/
  python tools/check_version_sync.py
  cd java && ./gradlew test --no-daemon
  → /ready-done-check done

When a cross-repo change is involved:
  → /cross-repo-coordination

When JAVA_ARCHITECTURE.md may be stale:
  → ARCHITECTURE_AND_SPEC_SYNC

When adding a new workflow or skill:
  → /workflow-skill-author → process-librarian agent

Every session end:
  Write handover note:
    Date / Branch / HEAD / Version
    Systems touched / Validation run
    Compatibility: replay=? save=? protocol=?
    Next concrete action
```

See [workflow/WORKFLOW_AUDIT_2026-04-17.md](workflow/WORKFLOW_AUDIT_2026-04-17.md) for the gap analysis that motivated this system.
