---
name: document-codebase
description: >-
  Builds a single, unified, indexed documentation corpus for an application by
  running a coordinated fleet of subagents over BOTH the codebase and any
  existing docs, verifying every claim against the actual code. Produces a
  navigable docs/ tree with a master index, a cross-referenced glossary
  (ubiquitous language mapped to code), architecture/domain coverage, data &
  persistence models, and an explicit gaps list. Use this whenever the user
  wants to document, map, reverse-engineer, consolidate, or onboard onto a
  codebase at scale — e.g. "document this whole service", "consolidate our
  scattered docs", "build a documentation wiki", "write up the architecture and
  domain model", "create a glossary / ubiquitous language", "map the bounded
  contexts and event flows", "produce onboarding docs from the code". Reach for
  it even when the user doesn't say "fleet" or "agents" but is clearly asking
  for comprehensive, codebase-wide documentation rather than a single file's
  docstring.
---

# Documentation Corpus

Turn a codebase plus its scattered, half-true documentation into **one coherent,
indexed, code-verified corpus** — built by many agents but reading as if written
by one careful author.

The hard parts of this task are not writing prose; they are **coordination**:
partitioning the work so agents don't overlap or leave holes, keeping one
consistent vocabulary across many authors, treating existing docs as *claims to
verify* rather than truth, and ending up with something navigable instead of a
pile of files. The phases below exist to solve those problems. Follow them in
order; each one sets up the next.

## Operating principles (these are the whole point)

- **Code is ground truth; existing docs are claims.** Docs, comments, ADRs,
  wikis drift. Every non-trivial statement in the output is either backed by a
  code citation (`path/to/file.ext:line`) or explicitly marked unverified. When
  a doc contradicts the code, you document what the code does and record the
  discrepancy — you never silently pick one.
- **Partition before you fan out.** Agents working in parallel must own
  disjoint areas. Overlap wastes work and produces contradictions; gaps produce
  silent incompleteness. The recon phase exists to draw clean boundaries.
- **One vocabulary.** The same concept must have the same name everywhere. This
  is why a shared glossary seeds the agents and a reconciliation pass merges
  what they each discovered.
- **One voice.** Many authors read as one only if they share templates, a style
  guide, and a final editorial pass. Don't skip the assembly phase.
- **Name the unknowns.** Anything you couldn't verify, couldn't find, or found
  contradictory goes in the gaps list — explicitly. Inventing plausible detail
  is the worst failure mode here; a flagged gap is a feature.

## Adaptivity: detect the architecture, don't assume it

This skill is often reached for on Domain-Driven / event-sourced systems, and it
goes deep on them — bounded contexts, aggregates, commands, events, projections,
read models, sagas/process managers. **But only when the code actually works
that way.** During recon, determine the real architecture (event-sourced? CRUD
+ layered? microservices? a framework-shaped monolith?) and shape the corpus to
match. Use DDD/event-sourcing sections as first-class structure *if and only if*
those patterns are present in the code. Otherwise document what is actually
there (controllers, services, models, jobs, integrations) using the generic
structure. Forcing ES/DDD vocabulary onto a plain CRUD app is a failure, not
thoroughness.

---

## Phase 0 — Reconnaissance

Goal: understand the system well enough to *plan the work*, not to document it
yet. Do this yourself (or with one or two scout agents for a large repo).

Establish:
- **Shape & stack**: languages, build/dependency files, entry points, top-level
  modules/packages, how the app is run and deployed.
- **Existing documentation**: where it lives (READMEs, `docs/`, ADRs, wikis,
  design notes, rich inline comments) and roughly what it covers. Note it as
  input to verify — not as settled fact.
- **Architecture style**: the real one (see adaptivity above). Identify
  candidate **areas** — the units you'll assign to agents. Good area boundaries
  follow the system's own seams: bounded contexts, top-level modules, service
  boundaries, or feature domains. Aim for areas of comparable size with minimal
  coupling at the edges.
- **Persistence & data**: databases, schemas, migrations, and — if
  event-sourced — the event store, event types, projections, and read models.
- **Seed glossary**: a first list of domain terms you keep seeing in names,
  modules, and docs. This seed is handed to every authoring agent so they start
  from shared vocabulary. It will be incomplete; that's fine.

`references/corpus-structure.md` defines the target structure and page templates
for both the ES/DDD-rich and the generic case. Read it before planning so your
proposed structure matches what agents will actually produce.

---

## Phase 1 — Plan, then confirm

Produce a short **documentation plan** and present it to the user before any
fan-out. The prompt that invokes this skill explicitly asks for this — don't
skip it. The plan states:

1. **Detected architecture** and why (one or two lines, with evidence).
2. **Proposed corpus structure** — the actual file tree of the `docs/` output,
   with the master index and the major sections.
3. **Division of work** — the list of areas, one row each: which agent owns it,
   what code paths and which existing docs it will consult, and what page(s) it
   produces. Make the disjointness visible.
4. **Cross-cutting passes** — glossary reconciliation, editorial assembly,
   verification — and who runs them.
5. **Known unknowns so far** — anything recon already flagged as murky.

Then ask the user to confirm or adjust. Wait for sign-off before Phase 2.

---

## Phase 2 — Parallel authoring (the fleet)

Spawn one subagent per area, in parallel. Each agent gets a brief built from the
template in `references/agent-briefs.md` (the "Area author" brief), parameterized
with: its area, the exact code paths it owns, the existing docs to verify, the
seed glossary, and the page template + style guide to follow.

Each authoring agent must return a **structured result**, not just prose, so the
later passes can stitch everything together:

- the markdown page(s) for its area, following the template and style guide;
- **glossary contributions**: every domain term it used or defined, with a
  one-line definition and the code symbol/file it maps to;
- **cross-reference requests**: anchors it linked to that live in other areas
  (so the reconciler can wire them up);
- **discrepancies**: each place existing docs disagreed with the code;
- **gaps**: anything it couldn't verify or couldn't find.

Keep agents strictly inside their assigned paths to preserve the partition. If
recon under-scoped an area (an agent reports it's far bigger than expected),
split it and spawn a follow-up rather than letting one agent sprawl.

For large systems, run authoring as a pipeline and consider a **completeness
critic** at the end of the wave: an agent that looks for modules, endpoints,
events, or tables that no area covered, and feeds the misses into a second wave.
Silent truncation ("documented the top 10 modules") reads as completeness when
it isn't — if you bound coverage, say so in the gaps list.

---

## Phase 3 — Reconcile

Two cross-cutting merges, best done as focused passes (the "Reconciler" brief in
`references/agent-briefs.md`):

- **Ubiquitous language**: merge all glossary contributions into one canonical
  glossary. Collapse synonyms to a single preferred term, and where the *same*
  concept carries *different* names in code vs docs vs across contexts, record
  that mapping explicitly — it's valuable knowledge, not noise. Each entry maps
  the term to its code representation and links to the area that owns it.
- **Cross-references**: resolve every cross-reference request so links actually
  point at real anchors. Flag any that can't resolve (often a sign of a missing
  area or a renamed concept).

If the canonical glossary renames a term an authoring agent used, fix the term
in that page during assembly so the vocabulary is consistent end to end.

---

## Phase 4 — Assemble & verify

- **Master index**: build `docs/INDEX.md` (or `README.md`) — the table of
  contents linking every section, organized by the structure from Phase 1. This
  is the front door; make it genuinely navigable.
- **Editorial pass**: apply one voice and consistent formatting across all
  pages per `references/style-guide.md`. Normalize headings, citation style,
  cross-reference link format, and tense/person. This is what makes a
  many-author corpus read as one.
- **Gaps appendix**: aggregate every discrepancy and gap into one
  `docs/GAPS.md`, grouped by area, so unverified or contradictory areas are
  visible in one place rather than buried.
- **Verification sweep**: spot-check a sample of citations against the code,
  and check that every link in the index and every cross-reference resolves.
  Broken links and stale citations are the most common defects; catch them here.

Report to the user: where the corpus lives, the index entry point, how many
areas were covered, and a pointer to the gaps list with its headline items.

---

## Coordination cheatsheet

| Problem | Mechanism |
|---|---|
| Agents overlap / leave holes | Disjoint partition drawn in recon, confirmed in the plan |
| Vocabulary drifts between authors | Seed glossary in → reconciliation merge out |
| Docs contradict code | Code is ground truth; discrepancies logged, never silently resolved |
| Many authors, many voices | Shared templates + style guide + editorial pass |
| Invented detail | Everything cited or marked unverified; gaps appendix |
| "Looks complete" but isn't | Completeness critic + explicit notes on any bounded coverage |

## Reference files

- `references/corpus-structure.md` — target file tree and page templates (ES/DDD
  and generic), glossary/index/gaps formats. Read in Phase 0.
- `references/agent-briefs.md` — copy-paste subagent prompts (scout, area author,
  reconciler, editor, verifier, completeness critic) with their required
  structured outputs. Use in Phases 0, 2, 3, 4.
- `references/style-guide.md` — voice, citation format, cross-reference
  convention, discrepancy/gap notation, formatting rules. Hand to every author;
  apply in Phase 4.
