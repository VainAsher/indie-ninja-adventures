# Stage 4: Execution Loop

Per-task development loop. Repeat for each sprint task.

---

## The Loop

```
Branch → Implement → Test → Verify → Commit → PR → CI → Merge → Done
```

If any step fails: fix it before proceeding. Never skip tests to ship faster.

---

## Step by Step

### 1. Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/<task-name>
```

Name branches clearly: `feature/boss-ai-forest`, `fix/multiplayer-coin-desync`

### 2. Implement

Work in focused chunks. Commit each logical unit — not at end of day.

Commit format:
```
feat|fix|docs|test|chore: short description

[optional body: why this approach, what was tried]
[optional: Closes #123]
```

### 3. Test Locally

```bash
# Full test suite (always)
python run_tests.py

# If physics or input pipeline changed:
# Run a saved replay and verify it plays back correctly
python demo_game.py --replay user_data/replays/<session>.json

# If netcode changed:
# Smoke test: host + join 2-player local, check basic sync
python demo_game.py --host 7777
# (second terminal) python demo_game.py --connect 127.0.0.1:7777
```

**Never merge a red branch.** If tests fail, fix before continuing.

### 4. Verify Acceptance Criteria

Go through the task's acceptance criteria checklist. Check each item off.

If a criterion can't be verified: it either needs clarification or the implementation is incomplete.

### 5. Push + PR

```bash
git push -u origin feature/<task-name>
# Open PR → develop on GitHub
```

PR description: fill in the PR template (what changed, why, testing done).

### 6. CI Passes → Merge

Wait for CI to pass (tests, lint, format check). If CI fails, fix it.

Once green: merge the PR, delete the branch.

### 7. Close Task

- Move task to Done on the sprint board
- Mark feedback repo issue as `fixed` if it originated there
- Note completion in DASHBOARD.md

---

## When You're Blocked

- Move task to "Blocked" column
- Add a comment explaining the blocker
- Pull the next backlog item into the sprint
- Don't sit idle — switch tasks, not priorities

---

## Commit Discipline

Good commits:
```
feat: add Forest boss phase 1 — patrol and charge patterns
fix: resolve coin desync when host collects before client joins
test: add edge case for wall jump during dash cancellation
docs: update ARCHITECTURE.md with authoritative server data flow
```

Bad commits:
```
wip
stuff
fix things
updates
```
