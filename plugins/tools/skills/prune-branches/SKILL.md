---
name: prune-branches
description: Safely clean up git branches — from removing only branches whose work is already merged into the default (including squash-merges that `git branch --merged` cannot see) up to a full wipe leaving just main/master/trunk. Use whenever the user wants to delete, nuke, wipe, prune, tidy, or reset branches, drop merged/stale branches, or shrink a cluttered branch list. Destructive — classify branches first, confirm scope, rescue unsaved work, then delete. Requires explicit user authorization.
---

# prune-branches

Clean up git branches without losing work. Requests range from the gentle ("delete branches that are already merged") to the absolute ("wipe everything except main"). The danger is that the blunt version — force-delete every non-default branch and every remote — also destroys unmerged commits, uncommitted changes sitting in worktrees, and open pull requests. So the job is not "delete branches"; it's **classify what's safe, confirm how far to go, rescue anything unsaved, then delete.**

## When to trigger

The user wants to delete, nuke, wipe, prune, tidy, or reset branches — whether that's "remove the merged ones," "clean up this mess," or "leave only main." Default branch is usually `main` but may be `master` or `trunk`; confirm if unclear.

## Core principle: classify before you delete

The instinct is `git branch --merged` → delete the rest. **This is wrong, and dangerously so**, because it misses **squash merges**: a squash lands a brand-new commit on the default, so the branch's own commits never become ancestors and the branch reads as "unmerged" forever — even though its work is fully in the default. Blindly force-deleting "unmerged" branches therefore looks safe but can nuke branches you'd want gone *and* keep ones whose absence you'd mourn.

So decide each branch by **whether its work is already in the default**, detected empirically:

1. **Patch-id equivalence** — squash the branch's whole net diff onto its merge-base as one synthetic commit, then ask `git cherry` whether the default already contains that patch. Catches squash merges.
2. **Delta-over-touched-files fallback** — patch-id drifts if the default later re-touched the same lines. Compare the branch tip to the default over *only* the files the branch changed; zero diff ⇒ the content is in the default anyway.

A branch is **CONTAINED** (work is in the default — safe to delete) or **UNIQUE** (has commits/content not in the default — deleting loses work, recoverable only via local reflog, and never on the remote).

`scripts/classify-branches.sh [default]` does all of this read-only and prints a table with each branch's verdict plus its worktree/dirty/PR context. Prefer it over re-deriving the probes by hand.

## Workflow

### 1. Inventory — show the whole picture first

```bash
echo "=== local ==="    && git branch
echo "=== remote ==="   && git branch -r
echo "=== worktrees ===" && git worktree list
echo "=== open PRs ===" && gh pr list 2>/dev/null || echo "(no gh / not a GitHub repo)"
```

### 2. Classify every branch

```bash
bash <skill>/scripts/classify-branches.sh        # auto-detects default
# or: classify-branches.sh master
```

Read the table. `CONTAINED` rows are the safe-to-delete set. `UNIQUE` rows hold real work — deleting them loses commits, so they need explicit per-branch sign-off. The `WORKTREE(dirty)` and `PR` columns flag the two things that bite (below).

### 3. The two things that bite

**Worktrees.** A branch checked out in another worktree **cannot** be `git branch -D`'d until that worktree is removed (`git worktree remove <path>`). Worse, a worktree may hold **uncommitted changes** (the dirty count) that exist nowhere else — `git worktree remove --force` discards them silently. Also check **detached-HEAD worktrees** (no branch, listed separately by the script): the commit may or may not be in the default, and it too can hold unsaved edits. Never remove a dirty worktree without rescuing first (step 5).

**Open PRs.** Deleting a remote branch **closes its PR**. Before proposing to delete any branch with an open PR, check whether the PR is actually outdated — e.g. its content is already in the default (`CONTAINED`), or it patches a file/area the default has since rewritten. If a PR is live work, leave it. If you do close an outdated PR whose underlying change never actually landed in the default, say so plainly so the user can re-capture it — don't let a still-valid fix vanish silently. Never close a PR without explicit authorization for that branch.

### 4. Confirm scope — offer tiers, don't assume the maximum

"Clean up branches" rarely means "detonate everything." Present the scope as a graduated choice (use the AskUserQuestion tool when the picture is rich), and recommend the safe end:

- **Merged-only (recommended default):** delete only `CONTAINED` branches (local, and their remotes if the user wants remote tidy-up too). Keep every `UNIQUE` branch, every open PR, and every dirty worktree. Loses nothing.
- **Local-only:** as above but never touch remotes/PRs — purely a local tidy.
- **Full nuke:** delete every non-default branch and remote, force-deleting `UNIQUE` work and closing open PRs. This is the original blunt behavior — only on unambiguous, explicit authorization ("wipe everything except main, yes I know it closes the PRs"), and spell out the consequences first.

Authorization phrases that count: "delete the merged ones," "nuke everything except `<branch>`," "yes do it" in reply to a flagged-risk prompt. When in doubt, ask.

### 5. Rescue before removing anything unsaved or UNIQUE

For any dirty worktree, detached-HEAD worktree, or `UNIQUE` branch you're about to remove with the user's blessing, preserve a recoverable copy first:

```bash
mkdir -p ../branch-cleanup-rescue
git -C <worktree> diff > ../branch-cleanup-rescue/<name>.patch     # uncommitted changes
cp <worktree>/<changed-file> ../branch-cleanup-rescue/             # full copy, survives a non-applying patch
```

Local branch deletes are reflog-recoverable for a while (note the printed `was <sha>`); remote deletes are not. Rescue removes the "oops."

### 6. Execute — order matters

Make sure the default branch is checked out so it can't delete itself.

```bash
# a) Remove worktrees that are merged + clean (frees their branches for deletion).
git worktree remove <path>                 # add --force only after rescuing dirty ones

# b) Delete the chosen local branches.
git branch -d <branch>                      # plain -d for CONTAINED branches git sees as merged
git branch -D <branch>                      # -D for squash-CONTAINED (git won't see them merged) or authorized UNIQUE

# c) Remote deletes — ONLY for branches in scope. This closes any open PR on them.
git push origin --delete <branch> [<branch> ...]

# d) Prune stale remote-tracking refs.
git fetch --prune
```

Do the deletes branch-by-branch (or in small explicit groups) rather than a blind `git branch | xargs -D` — you've already classified, so name what goes.

### 7. Verify

```bash
echo "=== local ===" && git branch && echo "=== remote ===" && git branch -r
```

If you closed PRs, confirm with `gh pr view <n> --json state` — and re-fetch first, since `gh pr list` can briefly report a stale head SHA right after a push.

## Notes

- `git branch -d` refuses to delete an unmerged branch — a useful safety check; reach for `-D` only when you've confirmed the branch is squash-CONTAINED or the user explicitly authorized losing `UNIQUE` work.
- `--force-with-lease` is a `git push` flag, not a branch-delete flag; it has no role in `git branch -d/-D`.
- Skip this on a CI machine or shared workstation — remote deletes have no undo, and reflog only helps locally.
- The classifier is read-only; it never deletes. Deciding and deleting stay with the human-authorized workflow above.
