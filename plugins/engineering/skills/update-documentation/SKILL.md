---
name: update-documentation
description: >-
  Keeps an existing documentation corpus in sync with code by re-running the
  document-codebase verification workflow over a SMALL, bounded scope — a set of
  changes rather than the whole repo. Resolve the scope (uncommitted working-tree
  changes by default, or an explicit commit, commit range, PR, or staged set),
  map the changed code to the doc pages, glossary entries, diagrams, and index
  links it affects, then update those — and only those — re-verifying every claim
  and citation against the new code. Use this whenever code has changed and the
  docs need to catch up: "update the docs for this PR", "I just refactored the
  billing service, fix the documentation", "keep the docs in sync with my
  changes", "document what changed in this commit / since main", "the docs are
  stale after this merge", "regenerate the affected wiki pages", "update the
  glossary and architecture docs for these changes". Reach for it even when the
  user doesn't say "corpus" or "fleet" — any "update / refresh / sync the
  documentation for <a change>" belongs here. This is the INCREMENTAL companion
  to document-codebase: document-codebase builds the corpus from scratch over the
  whole codebase; update-documentation patches an existing corpus from a diff. If
  no corpus exists yet, this skill stops and points at document-codebase.
---

# Update Documentation

Patch an existing, code-verified documentation corpus so it stays true to the
code after a change — touching exactly the pages the change affects, no more,
and re-verifying everything you touch against the **new** code.

This is the incremental sibling of `document-codebase`. That skill builds the
whole corpus; this one keeps it honest as the code moves. The hard parts here are
different from building from scratch: the corpus and its conventions already
exist (so you **conform**, you don't reinvent), and the unit of work is a **diff**
(so the central skill is figuring out what a set of code changes *means* for docs
that were written against the old code). Citations drift as lines move; a renamed
symbol must be renamed everywhere; a deleted feature must leave no dangling
cross-reference; a new module may need a brand-new page wired into the index. The
phases below exist to catch exactly these failure modes.

## Operating principles (these carry over from document-codebase)

- **Code is ground truth; the existing docs are now stale claims.** After a
  change, the docs describe the *old* code. Re-verify every statement you touch
  against the new code. Back each non-trivial claim with a citation
  (`path/to/file.ext:line`) pointing at the **post-change** code, or mark it
  unverified. A doc that still matches the pre-change code is a defect to fix,
  not truth to preserve.
- **Conform to the corpus you found.** Match the existing structure, voice,
  citation format, glossary conventions, and cross-reference style exactly — a
  reader must not be able to tell which pages were updated. Detect the
  conventions from the corpus itself; corpora built by `document-codebase` follow
  its `style-guide.md` and `corpus-structure.md`. Do not impose a new structure.
- **Touch only what the change touches.** The scope is the diff. Update pages the
  changed code is cited on or described by; create pages for genuinely new areas;
  flag — don't rewrite — pages that are merely adjacent. Rewriting untouched
  sections invites drift and noise, and buries the real change in a giant diff.
- **A change is more than added lines.** Renames, deletions, moved files, and
  changed behavior all ripple. A deleted symbol means a removed glossary entry
  and possibly a dead cross-reference; a rename means a find-and-replace across
  the corpus; moved code means citations point at the wrong file. Hunt these,
  don't just document the additions.
- **Name what you couldn't resolve.** Anything you couldn't verify, a doc you
  suspect is now stale but lies outside the scope, a cross-reference you couldn't
  re-point — record it in `GAPS.md`. A flagged gap beats invented detail or a
  silent omission.

---

## Phase 0 — Resolve scope & locate the corpus

Two things must be true before you plan: you know exactly what changed, and you
know which corpus you're updating. `references/scope-and-impact.md` has the git
recipes for each scope type and how to detect the corpus — read it now.

**Resolve the scope** into a concrete change set (changed files, and within them
the symbols/regions and the *kind* of change — added, modified, renamed, moved,
deleted):

- **No argument → uncommitted working-tree changes** (staged + unstaged). This is
  the default: "I changed things, update the docs."
- An explicit argument overrides: a **commit** SHA, a **commit range** (`A..B` /
  `main..HEAD`), a **PR** (`#123` / URL → resolve via `gh`), or the **staged** set.

**Locate the corpus**: find the documentation tree (commonly `docs/`, or a path
the user names) and read enough of its index and conventions to know its
structure and style.

**If no corpus exists, stop.** This skill patches an existing corpus; it does not
build one from a diff (a tiny change would seed a misleading, mostly-empty tree).
Tell the user plainly that there's nothing to update yet and point them at
`document-codebase` to build the baseline first, then re-run this skill. Don't
improvise a corpus.

---

## Phase 1 — Impact analysis, then confirm

Map the change set onto the corpus and present a short **update plan** before
editing anything. `references/scope-and-impact.md` describes the mapping method
(how to trace changed code to the pages, glossary terms, diagrams, and index
entries that reference it). The plan states:

1. **Scope** — what resolved, in one line (e.g. "PR #123, 7 files in
   `src/billing/`, 1 new module, 2 renamed symbols, 1 deleted endpoint").
2. **Impact table** — one row per affected doc artifact: the page/glossary
   entry/diagram, why the change touches it, and the action — **update**,
   **create**, **delete/retire**, or **flag** (suspected stale but out of scope).
3. **Ripples** — renames to propagate corpus-wide, cross-references that may
   break, index entries to add or remove.
4. **Unknowns** — anything the diff implies but you can't yet pin down.

Then ask the user to confirm or adjust, and wait for sign-off. This gate is cheap
insurance: the skill mutates existing files, and a wrong impact map is far easier
to fix as a plan than as a pile of edits.

---

## Phase 2 — Update (proportional fan-out)

Scale the effort to the impact, don't over-engineer a small diff:

- **A few affected pages in one area** → do it inline (or one updater agent). No
  fleet needed.
- **A broad change spanning several areas** → spawn one updater subagent per
  affected area, in parallel, using the "Doc updater" brief in
  `references/agent-briefs.md`. Keep each agent inside its pages to preserve the
  partition, exactly as in `document-codebase`.

Every updater, inline or spawned, does the same thing for its pages:

- **Re-verify against the new code.** Walk each existing claim that the change
  bears on; confirm, correct, or remove it per what the post-change code now
  does. Refresh citations to point at the **new** `path/file.ext:line` — line
  numbers move even when behavior doesn't, so re-anchor them.
- **Write new content for genuinely new behavior**, following the existing page
  template and style. For a whole new area, create the page where the structure
  says it belongs.
- **Remove what the code removed**, and note the removal so cross-references and
  the glossary get cleaned up in reconciliation.
- **Return a structured result** (pages changed, glossary deltas, rename
  requests, broken-crossref candidates, discrepancies, gaps) so the
  reconciliation and verification passes can stitch it together — see the brief.

If a change turns out far larger than the plan assumed, stop and re-plan with the
user rather than letting one update sprawl across the whole corpus.

---

## Phase 3 — Reconcile the ripples

Updating pages in isolation leaves cross-cutting damage. Sweep it up:

- **Propagate renames.** If a symbol or term was renamed, apply it everywhere the
  old name appears — pages, glossary, diagrams, index — so vocabulary stays
  consistent end to end (the corpus's one-term-one-concept rule).
- **Fix the glossary.** Add entries for new domain terms, update the
  definition/code-mapping of changed ones, and retire entries for deleted
  concepts (or mark them removed if they carry history worth keeping).
- **Repair cross-references.** Re-point links whose target moved; remove or
  redirect links to deleted anchors. A dangling cross-reference is the most
  common breakage from a delete or move.
- **Update the index** (`INDEX.md` / `README.md`): add new pages, remove retired
  ones, so the front door still reaches everything and nothing it lists is gone.

---

## Phase 4 — Verify the touched surface

Re-verification is the whole value of this skill — don't skip it.

- **Spot-check citations you changed** against the new code: does
  `path/file.ext:line` still say what the page claims?
- **Check links** added/changed this run resolve, and that nothing you deleted is
  still linked from the index or another page.
- **Confirm renames are total** — grep the corpus for the old name; any survivor
  is a miss.
- **Roll up discrepancies and gaps** into `GAPS.md`, grouped as the corpus does
  it, so newly-suspected-stale areas are visible.

Report to the user: the scope you documented, the pages created/updated/retired,
renames propagated, and the headline gaps — plus a one-line note if you bounded
coverage anywhere, so "looks done" doesn't hide a silent truncation.

---

## Coordination cheatsheet

| Problem | Mechanism |
|---|---|
| Updating the wrong (or too many) pages | Impact map drawn in Phase 1, confirmed before editing |
| Docs still match the OLD code | Code is ground truth; re-verify every touched claim against post-change code |
| Citations point at moved lines | Re-anchor every citation you touch to the new `file:line` |
| A rename half-applied | Propagate corpus-wide in Phase 3; grep for survivors in Phase 4 |
| Dangling links after a delete | Reconcile cross-references and the index; verify nothing links to the gone |
| New page orphaned | Wire it into INDEX.md during reconciliation |
| Reinventing the corpus's style | Conform to detected conventions; never impose a new structure |
| No corpus to update | Stop and point at document-codebase — don't seed one from a diff |

## Reference files

- `references/scope-and-impact.md` — git recipes to resolve each scope type,
  corpus detection, and the method for mapping changed code to affected doc
  artifacts (incl. handling renames, deletes, moves, and citation drift). Read in
  Phases 0–1.
- `references/agent-briefs.md` — copy-paste subagent prompts (scope/impact
  scout, doc updater, reconciler, verifier) with their required structured
  outputs, adapted for incremental updates. Use in Phases 2–4.
