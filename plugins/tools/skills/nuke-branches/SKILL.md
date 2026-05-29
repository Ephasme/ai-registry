---
name: nuke-branches
description: Delete every local and remote git branch except a designated default (e.g. main), then prune stale tracking refs. Use when the user asks to clean up / nuke / wipe / reset branches to leave only main (or master/trunk). Destructive — requires explicit user authorization.
---

# nuke-branches

Wipe every local and remote git branch except a designated default. Destructive — only run after explicit user authorization (e.g. "delete all branches except main", "wipe everything except trunk").

## When to trigger

User asks to delete, clean up, nuke, wipe, or reset branches in a repo, leaving only the default branch. The default is typically `main` but may be `master` or `trunk` — confirm with the user if unclear.

## Workflow

### 1. Pre-flight inventory

Show the user the full picture before touching anything:

```bash
echo "=== local branches ==="
git branch
echo
echo "=== remote branches ==="
git branch -r
echo
echo "=== worktrees ==="
git worktree list
echo
echo "=== open PRs ==="
gh pr list 2>/dev/null || echo "(gh not available or not a GitHub repo)"
```

### 2. Flag risks

Before running destructive commands, call out:

- **Worktree branches**: any branch checked out in a worktree other than the current one cannot be deleted with `git branch -D` until the worktree is removed (`git worktree remove <path>`). Ask the user before touching these — they may have in-progress work.
- **Branches with open PRs**: deleting the remote branch closes the PR. Confirm explicitly if the user is iterating on any of them.

### 3. Confirm authorization

If the user hasn't already explicitly authorized the destructive action in their request, ask before proceeding. Phrases that count as authorization:
- "delete all branches except main"
- "nuke everything except <branch>"
- "yes do it" (in response to a flagged-risk prompt)

### 4. Execute

The default branch is `<DEFAULT>` (substitute `main`, `master`, or `trunk`). Make sure the default is currently checked out so it can't be deleted.

```bash
# 1. Local branches — force-delete (-D) since some may be unmerged.
git branch | grep -v '^\*' | grep -vw <DEFAULT> | xargs -n1 git branch -D

# 2. Remote branches — delete one by one.
git branch -r | grep -v HEAD | grep -v origin/<DEFAULT> | sed 's|origin/||' | xargs -n1 git push origin --delete

# 3. Drop stale tracking refs that match the now-deleted remote branches.
git fetch --prune
```

### 5. Verify

```bash
echo "=== local ===" && git branch && echo "=== remote ===" && git branch -r
```

Expect only `<DEFAULT>` and `origin/<DEFAULT>` (plus `origin/HEAD -> origin/<DEFAULT>`).

## Notes

- Uses `git branch -D` (capital D) to force-delete local branches that aren't merged into the default. This is intentional; the user has authorized it.
- Does not use `--force-with-lease` because that flag is for `push --force-with-lease`, not for branch deletion.
- The `xargs -n1` per-branch loop on the remote is slower than a single `git push origin --delete <a> <b> <c>` but produces clearer per-branch error messages and never silently skips on a single failure.
- Skip running this on a CI machine or shared workstation — there's no undo for the remote deletes (git's reflog only tracks local).
