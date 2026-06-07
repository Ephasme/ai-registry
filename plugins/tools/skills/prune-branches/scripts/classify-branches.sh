#!/usr/bin/env bash
# Read-only branch classifier for the prune-branches skill.
#
# For each local branch (except the default) it answers the question that
# actually decides whether a branch is safe to delete: "is this branch's work
# already in the default branch?" — INCLUDING work that landed via a SQUASH
# merge, which `git branch --merged` cannot see (a squash lands a brand-new
# commit, so the branch's own commits never become ancestors of the default).
#
# It never deletes anything. Run it, read the table, then decide.
#
# Usage:  classify-branches.sh [default-branch]
#   default-branch defaults to origin/HEAD's target, else main/master/trunk.
#
# Columns:
#   BRANCH           local branch name
#   VERDICT          CONTAINED = work already in the default (safe to delete)
#                    UNIQUE    = has commits/content NOT in the default
#                               (deleting loses work — reflog-recoverable locally)
#   ahead            commits on the branch since its merge-base with the default
#   WORKTREE(dirty)  worktree the branch is checked out in + uncommitted file
#                    count (a branch in a worktree can't be -D'd until removed;
#                    a non-zero dirty count means unsaved work to rescue first)
#   PR               open GitHub PR number for this branch, if gh is available
#                    (deleting the remote branch CLOSES that PR)

set -uo pipefail

default="${1:-}"
if [ -z "$default" ]; then
  default=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
fi
if [ -z "$default" ]; then
  for cand in main master trunk; do
    if git show-ref --verify --quiet "refs/heads/$cand"; then default="$cand"; break; fi
  done
fi
if [ -z "$default" ]; then
  echo "Could not determine the default branch — pass it explicitly:" >&2
  echo "  classify-branches.sh <default>" >&2
  exit 1
fi

# Compare against the remote tip if it exists — it's the source of truth for
# what has actually merged (and where squash commits land).
ref="$default"
git show-ref --verify --quiet "refs/remotes/origin/$default" && ref="origin/$default"

# Worktree path for a given branch (empty if not checked out anywhere).
# awk keeps this portable to macOS's bash 3.2 (no associative arrays).
wt_for() {
  git worktree list --porcelain | awk -v b="refs/heads/$1" '
    $1=="worktree"{p=$2}
    $1=="branch" && $2==b {print p; exit}'
}

printf "default = %s   (comparing against %s)\n\n" "$default" "$ref"
printf "%-44s %-10s %-6s %-26s %s\n" "BRANCH" "VERDICT" "ahead" "WORKTREE(dirty)" "PR"

git for-each-ref --format='%(refname:short)' refs/heads/ | while IFS= read -r b; do
  [ "$b" = "$default" ] && continue

  base=$(git merge-base "$ref" "$b" 2>/dev/null) || {
    printf "%-44s %-10s\n" "$b" "NO-BASE"; continue;
  }
  ahead=$(git rev-list --count "$base..$b")

  verdict="UNIQUE"
  if [ "$ahead" -eq 0 ]; then
    verdict="CONTAINED"
  else
    # Pass 1 — patch-id equivalence. Squash the branch's whole net diff onto
    # its merge-base as one synthetic commit, then ask `git cherry` whether the
    # default already contains an equivalent patch. This is what catches a
    # squash merge: same diff, different commit. Collisions are effectively
    # impossible (patch-id is a hash of the diff).
    tree=$(git rev-parse "$b^{tree}")
    squash=$(git commit-tree "$tree" -p "$base" -m _ 2>/dev/null)
    if [ -n "$squash" ] && git cherry "$ref" "$squash" 2>/dev/null | grep -q '^-'; then
      verdict="CONTAINED"
    else
      # Pass 2 — fallback for when the default RE-TOUCHED the same files after
      # the squash merge (which shifts the patch-id so pass 1 misses it).
      # Compare the branch tip to the default over ONLY the files the branch
      # changed: zero diff means the content is in the default regardless.
      # (Unquoted $files can't handle paths with spaces — rare; eyeball those.)
      files=$(git diff --name-only "$base" "$b")
      if [ -n "$files" ]; then
        delta=$(git diff "$ref" "$b" -- $files | wc -l | tr -d ' ')
        [ "$delta" -eq 0 ] && verdict="CONTAINED"
      fi
    fi
  fi

  wt=$(wt_for "$b")
  wtcol="-"
  if [ -n "$wt" ]; then
    dirty=$(git -C "$wt" status --porcelain 2>/dev/null | grep -c '' || true)
    wtcol="$(basename "$wt")($dirty)"
  fi

  pr="-"
  if command -v gh >/dev/null 2>&1; then
    found=$(gh pr list --head "$b" --state open --json number -q '.[0].number' 2>/dev/null)
    [ -n "$found" ] && pr="#$found"
  fi

  printf "%-44s %-10s %-6s %-26s %s\n" "$b" "$verdict" "$ahead" "$wtcol" "$pr"
done

echo
echo "Detached-HEAD worktrees (no branch — handle manually, may hold unsaved work):"
git worktree list --porcelain | awk '
  $1=="worktree"{p=$2; det=1}
  $1=="branch"{det=0}
  $1=="detached"{ if(det) print "  " p }'