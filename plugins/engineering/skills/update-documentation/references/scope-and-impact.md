# Scope resolution & impact mapping

Two jobs this file covers: turning a scope argument into a concrete change set
(Phase 0), and turning that change set into the list of doc artifacts to touch
(Phase 1). The whole skill rests on getting these right — over-scope and you
rewrite the world; under-scope and the docs stay stale.

## Table of contents

- Resolving the scope (git recipes per type)
- Detecting the corpus
- Reading the change set (it's more than added lines)
- Mapping changed code → affected docs
- Citation drift: re-anchoring line numbers
- Handling renames, deletes, and moves

---

## Resolving the scope

Default with no argument: **uncommitted working-tree changes** (staged +
unstaged). An explicit argument overrides. In every case you want two things: the
list of changed files, and the actual diff (to see *what* changed, not just
*where*).

| Scope | Files changed | Full diff |
|---|---|---|
| Working tree (default) | `git status --porcelain` then `git diff --name-status HEAD` | `git diff HEAD` |
| Staged only | `git diff --cached --name-status` | `git diff --cached` |
| A commit | `git show --name-status <sha>` | `git show <sha>` |
| A commit range | `git diff --name-status A..B` (e.g. `main..HEAD`) | `git diff A..B` |
| A PR | `gh pr diff <n> --name-only` | `gh pr diff <n>` (and `gh pr view <n>` for intent) |

Notes:
- `--name-status` prefixes each file with its change kind — `A` added, `M`
  modified, `D` deleted, `R###` renamed (with similarity %), `C` copied. This is
  how you learn a file was renamed/moved rather than rewritten; carry it forward.
- For a PR, read the title and body (`gh pr view`) too — the author's stated
  intent is a strong hint about which *behavior* changed, which is what docs
  describe.
- If the working tree is dirty but the user named a commit/PR, document the
  named scope and mention the uncommitted changes you're ignoring, so it's their
  choice.
- Untracked new files won't show in `git diff` without `--`; catch them via
  `git status --porcelain` (lines starting `??`) when scoping the working tree.

## Detecting the corpus

Look for the documentation tree the change should sync into:

- Common roots: `docs/`, `documentation/`, `wiki/`, or a path the user names.
- Confirm it's a *corpus* (an indexed tree — has an `INDEX.md`/`README.md`,
  likely `GLOSSARY.md`, `GAPS.md`, and area folders), not just a stray README.
- Read the index, the glossary, and one or two area pages to learn the
  **conventions**: citation format, heading structure, voice, cross-reference
  link style, how gaps/discrepancies are noted. You will conform to these.

**No corpus → stop** (per the SKILL). Don't seed one from a diff; send the user
to `document-codebase` to build the baseline, then this skill can patch it.

## Reading the change set (it's more than added lines)

For each changed file, classify what actually moved, because each kind ripples
into docs differently:

| Change kind | Typical doc impact |
|---|---|
| New file / new public symbol | New content; possibly a new page; new glossary term; new index entry |
| Modified behavior | Re-verify and rewrite the affected claims/rules; refresh citations |
| Modified signature/shape (params, fields, events) | Update the model/behavior tables that enumerate them |
| Renamed symbol or file | Corpus-wide find-and-replace of the name; re-anchor citations |
| Moved file (path changed) | Citations point at the old path — re-anchor all of them |
| Deleted symbol/file/feature | Remove the content; retire the glossary entry; kill dangling cross-refs and index links |

Pure formatting/whitespace or internal refactors with no behavior or
symbol-name change usually need only **citation re-anchoring** (lines moved), not
prose changes — but the cited lines still must be fixed.

## Mapping changed code → affected docs

For each changed symbol/file, find where the corpus talks about it. Effective
signals, roughly in order of precision:

1. **Citation search** — grep the corpus for the changed file path (and old path
   if moved). Pages that cite `path/file.ext` are directly affected. This is the
   highest-signal link because the corpus's own convention is to cite code.
2. **Symbol/term search** — grep for the changed class/function/event/field
   name, and for its glossary term. Hits are pages describing that thing.
3. **Area/structure match** — locate the changed code's module/context, then the
   corpus folder that owns that area (`contexts/<x>/`, `modules/<x>/`). Even
   uncited pages in that area may describe the changed behavior.
4. **Feature pages** — changes to user-facing behavior often surface on
   `features/` pages that cross-link the area pages.

Produce the impact table from the union of these hits, deduplicated, each row
tagged update / create / delete-retire / flag. **Flag** (not edit) pages that are
merely adjacent — in the same area but not actually describing the changed code —
so the user can decide whether they're in scope.

## Citation drift: re-anchoring line numbers

Even a change that doesn't alter behavior shifts line numbers, so every citation
on a touched page that points into a changed file is suspect. For each such
citation:

- Re-locate the cited symbol/claim in the **new** file and update the line number
  (`:line` or `:start-end`).
- If the cited code is *gone*, the claim it backed is stale — fix or remove the
  claim, don't just delete the line number.
- Don't trust the old number because "the function didn't change" — additions
  above it move it. Re-anchor by content, not by memory.

## Handling renames, deletes, and moves

These are the ripple-heavy cases the impact map must call out explicitly:

- **Rename** (symbol or term): this is a corpus-wide operation, not a one-page
  edit. Record a rename request `{from, to}` in Phase 2; in Phase 3 apply it to
  every page, the glossary entry, diagrams, and the index; in Phase 4 grep for
  survivors of the old name. A half-applied rename is a silent inconsistency.
- **Delete**: remove the content and the glossary entry, then chase every
  cross-reference and index link that pointed at it — a link to a deleted anchor
  is the most common post-delete breakage. If the concept carries history worth
  keeping, mark it retired rather than vanishing it, per how the corpus handles
  removals.
- **Move** (path change, same content): behavior docs may be fine, but every
  citation to the old path is now wrong — re-anchor them all to the new path.
