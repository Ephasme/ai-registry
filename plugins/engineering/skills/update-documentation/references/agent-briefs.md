# Subagent briefs (incremental update)

Copy-paste prompts for updating a corpus from a diff. Fill the `<…>` slots. Each
brief specifies a **structured return** so the reconcile and verify passes can
stitch the work together — the outputs only compose cleanly if every agent
returns the same shape. Always tell each agent that its final message *is* the
deliverable (data for the orchestrator), not a chat reply.

These mirror `document-codebase`'s briefs but are scoped to a change set: agents
**update an existing corpus**, they don't author one from scratch. If a
deterministic orchestration tool with schema-validated outputs is available, turn
the "Return" sections into schemas; otherwise pass them as plain instructions.

For small scopes you won't spawn anything — do the work inline. Reach for these
when the change spans several areas and parallel updaters pay off.

---

## Scope / impact scout (Phase 1, optional for large diffs)

```
You are mapping a code change onto an existing documentation corpus to plan an
update. Do NOT edit anything — reconnaissance only.

Change set: <list of changed files with their A/M/R/D/move status, + the diff or
a path to it>.
Corpus root: <docs path>. Its conventions: <citation format, structure — or
"read INDEX.md + a sample page to infer them">.

For each changed file/symbol, find where the corpus references it. Use, in order:
1. grep the corpus for the file path (and the OLD path if the file moved) — pages
   that cite it are directly affected;
2. grep for the changed symbol/term names and their glossary entries;
3. locate the area folder owning the changed code; note pages there that may
   describe the behavior even if uncited.

Return, as structured data:
- impact: [{doc_artifact, kind: page|glossary|diagram|index, reason,
  action: update|create|delete|flag}]
- ripples: {renames: [{from, to}], maybe_broken_crossrefs: [...],
  index_changes: [{add|remove, page}]}
- unknowns: [things the diff implies but you couldn't pin to a doc].
```

---

## Doc updater (Phase 2 — the core)

```
You are updating ONE area of an existing documentation corpus to match changed
code. Stay strictly within your assigned pages — other agents own the rest.

Pages you own: <exact doc paths>.
Code that changed (your area): <files + symbols + change kind: added/modified/
renamed/moved/deleted; attach the relevant diff hunks>.
Corpus conventions: follow the EXISTING style exactly — citation format, page
template, voice, cross-reference style, how gaps/discrepancies are noted. Detect
them from the corpus (corpora built by document-codebase follow its
style-guide.md). Do NOT introduce a new structure or voice.

Method — this is the whole job:
- The NEW code is ground truth; the current docs describe the OLD code. Walk
  every existing claim your pages make that the change bears on, and confirm,
  correct, or remove it per what the post-change code now does.
- Re-anchor every citation you touch to the NEW path/file.ext:line — line numbers
  move even when behavior doesn't. If the cited code is gone, fix the claim, not
  just the number.
- Add content for genuinely new behavior, following the existing page template.
  Create a new page only if the impact plan said to, where the structure dictates.
- Remove what the code removed; note the removal for cross-ref/glossary cleanup.
- Don't rewrite sections the change doesn't touch — keep the diff to the change.

Return, as structured data:
- pages_changed: [{path, summary_of_change}]
- pages_created: [{path}]  /  pages_retired: [{path, reason}]
- glossary_deltas: [{term, action: add|update|retire, definition, code_symbol,
  file}]
- rename_requests: [{from, to}]  — names to propagate corpus-wide
- broken_crossref_candidates: [{from_page, dead_target, why}]
- discrepancies: [{old_claim, code_ref, what_code_now_does}]
- gaps: [{topic, why_unverified, what_would_resolve_it}]
```

---

## Reconciler (Phase 3)

```
Sweep up the cross-cutting ripples from a set of doc updates so the corpus stays
internally consistent.

Inputs: all updater returns — rename_requests, glossary_deltas,
broken_crossref_candidates, pages_created, pages_retired <attach/point to them>.
Corpus root: <docs path>.

Do:
- Renames: apply each {from, to} to EVERY occurrence across pages, glossary,
  diagrams, and the index. One term, one concept — no survivors of the old name.
- Glossary: add new terms, update changed ones (definition + code mapping),
  retire deleted ones (or mark retired if history matters), using the corpus's
  glossary entry format.
- Cross-references: re-point links whose target moved; remove or redirect links
  to deleted anchors.
- Index (INDEX.md / README.md): add created pages, remove retired ones, so the
  front door reaches everything and lists nothing gone.

Return: {renames_applied: [{from, to, pages}], glossary_updated: [...],
crossrefs_fixed: [...], index_changes: [...], unresolved: [...]}.
```

---

## Verifier (Phase 4 — final sweep)

```
Verify the TOUCHED surface of the corpus after an incremental update. Focus on
what changed this run; you need not re-check the whole corpus.

Inputs: the list of pages changed/created/retired this run, the rename list, and
the change set. Corpus root: <docs path>.

Do:
- Sample the citations changed this run and confirm each NEW path/file.ext:line
  actually says what the page claims. Report mismatches.
- Check every link added/changed this run resolves, and that nothing retired this
  run is still linked from the index or another page.
- Grep the corpus for each renamed OLD name — any hit is a missed rename.
- Confirm GAPS.md captured the run's discrepancies and gaps.

Return: [{issue_type: stale_citation|broken_link|missed_rename|dangling_to_deleted
|term_mismatch, location, detail}]. If clean, say so explicitly.
```
