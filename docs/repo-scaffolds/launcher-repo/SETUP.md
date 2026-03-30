# Launcher Repo — One-Time Setup

Steps to configure this repo after creating it at `VainAsher/indie-ninja-launcher`.

---

## 1. Enable GitHub Pages

1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/docs`
4. Save — the player guide will be available at `https://vainasher.github.io/indie-ninja-launcher/`

Or use MkDocs (see `mkdocs.yml`) with the deploy workflow for a nicer theme.

---

## 2. Add Repository Secret

The game repo dispatches a `game-release` event here when a new version is released.
To receive it:

1. Go to **Settings → Secrets and variables → Actions**
2. Add secret: `CROSS_REPO_PAT` — same PAT used in the game repo (needs `repo` scope)

---

## 3. Create the First Release

After copying the launcher source from the game repo and building:

```bash
git tag v1.1.0
git push origin v1.1.0
```

The `release_launcher.yml` workflow will build and attach the `.exe`.

---

## 4. Update Launcher Source URL

In `launcher/launcher.py` (game repo), the constant:

```python
LAUNCHER_REPO = "VainAsher/indie-ninja-launcher"
```

This should already point here once the game repo is updated for the split.

---

## 5. Configure GitHub Actions Permissions

Go to **Settings → Actions → General → Workflow permissions**:
- Select: "Read and write permissions"
- Allow: "Allow GitHub Actions to create and approve pull requests"
