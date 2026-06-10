# Subagent briefs

Copy-paste prompt templates for the fleet. Fill the `<…>` slots. Every brief
specifies a **structured return** — the agents' outputs only stitch together
cleanly if they all return the same shape. Always tell each agent that its final
message *is* the deliverable (data to be consumed by an orchestrator), not a
chat reply.

A note on tooling: these are written for a generic subagent mechanism. If a
deterministic orchestration tool is available (e.g. a Workflow runner with
schema-validated outputs), use it and turn the "Return" sections below into
schemas. Otherwise pass them as plain instructions.

---

## Scout (Phase 0, optional for large repos)

```
You are mapping a codebase to plan documentation work. Do NOT write
documentation — only reconnaissance.

Explore: <repo path or subtree>.

Report, as structured data:
- stack: languages, build/dependency files, entry points, how it's run/deployed.
- modules: top-level modules/packages with a one-line responsibility each.
- existing_docs: paths to READMEs, docs/, ADRs, design notes, and any
  doc-rich inline comments — with a one-line note on what each covers. Treat
  these as claims to verify later, not as truth.
- architecture: your read of the real architecture (event-sourced? layered/CRUD?
  microservices? monolith?), with the evidence (files/patterns) that shows it.
- persistence: databases, schemas, migrations; if event-sourced, the event
  store, event types, projections, read models.
- candidate_areas: a proposed partition into disjoint areas suitable for one
  agent each — name, the code paths it covers, the existing docs it should
  consult. Aim for comparable size and low coupling at the edges.
- seed_terms: domain terms you keep seeing (from names, modules, docs).
```

---

## Area author (Phase 2 — the core of the fleet)

```
You are documenting ONE area of a codebase. Stay strictly within your assigned
paths — other agents own the rest; overlapping causes contradictions.

Area: <area name>
Code you own: <exact paths / globs>
Existing docs to verify: <paths, or "none">
Seed glossary (shared vocabulary — use these terms; don't invent synonyms):
<term: short def list>
Page template to follow: references/corpus-structure.md → "area page"
Style guide: references/style-guide.md  (follow it exactly — voice, citations,
cross-reference format, how to flag discrepancies and gaps)

Method — this matters:
- The CODE is ground truth. Existing docs are claims. Verify each claim against
  the code. Where a doc contradicts the code, document what the code does and
  log the discrepancy.
- Back every non-trivial statement with a citation `path/file.ext:line`, or mark
  it explicitly unverified. Do not invent plausible detail.
- Cover the area's domain model, behavior, business rules (with their edge cases
  and constraints/invariants), and the terms it introduces.

Write the page(s) for your area to: <docs/.../path>

Return, as structured data:
- pages: the file path(s) you wrote.
- glossary_contributions: [{term, definition, code_symbol, file}] — every domain
  term you used or defined.
- crossref_requests: [{anchor_text, target_concept, target_area}] — links you
  made to things owned by other areas, for the reconciler to wire up.
- discrepancies: [{claim, source_doc, code_ref, what_code_does}].
- gaps: [{topic, why_unverified, what_would_resolve_it}].
```

---

## Completeness critic (end of Phase 2)

```
Authoring agents have each documented their assigned area. Find what NObody
covered.

Inputs: the area partition <list> and the code tree <path>.

Sweep the codebase for modules, packages, endpoints, events, commands,
projections, jobs, or tables that fall outside every assigned area, or that an
area's page omitted. Don't document them — just locate the misses.

Return:
- uncovered: [{thing, location, which_area_should_own_it}]
- under_covered: [{area, what_its_page_missed, code_ref}]
If nothing is missing, say so explicitly.
```

---

## Reconciler (Phase 3)

```
Merge the fleet's outputs into one consistent vocabulary and a working
cross-reference graph.

Inputs: all glossary_contributions and all crossref_requests from the authoring
agents <attach/point to them>.

Glossary:
- Merge into one canonical list. Collapse synonyms to a single PREFERRED term.
- Where the same concept has different names across code/docs/contexts, keep the
  mapping and record where each name appears — that's valuable, not noise.
- Each entry: preferred term, definition, code representation, synonyms with
  locations, owning area. Use the glossary entry format in
  references/corpus-structure.md.
- List any term you renamed, so the editor can fix it on the source pages.

Cross-references:
- Resolve each crossref_request to a real anchor (file + heading).
- Flag any that can't resolve — usually a missing area or a renamed concept.

Return: the canonical GLOSSARY.md content, a renames list
[{from, to, pages_affected}], and resolved/unresolved crossrefs.
```

---

## Editor & assembler (Phase 4)

```
Make a many-author corpus read as one, and build its front door.

Inputs: all area pages under <docs path>, the canonical glossary, the renames
list, and all discrepancies + gaps.

Do:
- Build docs/INDEX.md: a linked table of contents covering every page, grouped
  per the structure in references/corpus-structure.md, with a one-line
  orientation at top and links to GLOSSARY.md and GAPS.md. Every page must be
  reachable from the index.
- Editorial pass over every page per references/style-guide.md: one voice,
  consistent headings, citation format, cross-reference link format, tense and
  person. Apply the renames so vocabulary is consistent end to end.
- Build docs/GAPS.md: aggregate all discrepancies and gaps, grouped by area,
  using the gaps format in references/corpus-structure.md.

Return: list of files written/changed, and any inconsistency you couldn't
resolve (flag rather than paper over).
```

---

## Verifier (Phase 4 — final sweep)

```
Spot-check the corpus for correctness and broken navigation.

Do:
- Sample <N> code citations across the pages and confirm each `path/file:line`
  actually says what the doc claims. Report mismatches.
- Check that every link in INDEX.md resolves and every cross-reference points at
  a real anchor.
- Confirm GLOSSARY.md terms match the terms actually used on the pages.

Return: [{issue_type: stale_citation|broken_link|term_mismatch, location,
detail}]. If clean, say so.
```
