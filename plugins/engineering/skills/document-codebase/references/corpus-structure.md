# Corpus structure & page templates

The target output is a `docs/` tree of linked markdown files with a master
index. Pick the structure that matches the **detected architecture** (Phase 0).
Don't impose event-sourcing/DDD sections on a codebase that isn't built that way.

## Where the corpus goes

Default to a `docs/` directory at the repo root (or a path the user specifies).
If a `docs/` already exists with material you're consolidating, treat its
contents as input to verify and either rebuild into the new structure or merge —
confirm with the user which, in the plan. Never delete existing docs without
sign-off.

---

## Structure A — Event-sourced / DDD system

```
docs/
├── INDEX.md                      # master table of contents — the front door
├── GLOSSARY.md                   # ubiquitous language, term → definition → code
├── GAPS.md                       # all discrepancies & unverified areas
├── architecture/
│   ├── overview.md               # system shape, contexts map, how it runs
│   ├── context-map.md            # bounded contexts and their relationships
│   ├── event-flows.md            # major end-to-end command→event→projection flows
│   └── integration.md            # external systems, APIs, message bus, boundaries
├── contexts/
│   └── <bounded-context>/        # one folder per bounded context (an "area")
│       ├── overview.md           # purpose, responsibilities, language
│       ├── aggregates.md         # aggregates, invariants, commands handled
│       ├── events.md             # events emitted, payloads, semantics
│       ├── projections.md        # projections / read models built from events
│       └── rules.md              # business rules, edge cases, constraints
├── data/
│   ├── event-store.md            # event store layout, streams, versioning
│   ├── read-models.md            # query-side schemas / materialized views
│   └── persistence.md            # databases, migrations, retention
└── features/
    └── <feature>.md              # user-facing capabilities, cross-linking the above
```

## Structure B — Generic (layered / CRUD / service) system

```
docs/
├── INDEX.md
├── GLOSSARY.md
├── GAPS.md
├── architecture/
│   ├── overview.md               # components, request lifecycle, how it runs
│   ├── modules.md                # module/package map and responsibilities
│   └── integration.md            # external systems, APIs, jobs, boundaries
├── modules/
│   └── <module>/                 # one folder per module/domain (an "area")
│       ├── overview.md
│       ├── model.md              # domain/data model for this module
│       ├── behavior.md           # services, endpoints, workflows
│       └── rules.md              # business rules, edge cases, constraints
├── data/
│   ├── schema.md                 # tables/collections, relationships
│   └── persistence.md            # migrations, indexes, retention
└── features/
    └── <feature>.md
```

Scale the depth to the system: a small app may collapse a context folder into a
single page; a large one may need sub-areas. Keep the index honest about what
exists.

---

## Page template — area page (context / module)

```markdown
# <Area name>

> **Purpose.** One paragraph: what this area is responsible for and why it
> exists in the system.

## Responsibilities & boundaries
What it owns; what it explicitly does not; who it talks to. Link related areas.

## Domain model
The aggregates / entities / value objects (or models) here, their invariants,
and the rules that always hold. Map each to code: `path/file.ext:line`.

## Behavior
For ES/DDD: commands handled, events emitted, projections built.
For generic: services, endpoints, workflows, jobs. Cite code.

## Business rules
Each rule as a checkable statement, with the code that enforces it and the
edge cases / constraints it covers. Cross-link to the feature(s) it serves.

## Key terms
The domain terms this area introduces (these feed the glossary). Term → code symbol.

## Notes & gaps
Anything unverified, contradictory, or missing. These roll up into GAPS.md.
```

## Glossary entry format (`GLOSSARY.md`)

```markdown
### <Preferred term>
**Definition.** One or two precise sentences.
**In code.** `ClassName` / `function_name` — `path/file.ext:line`.
**Also called.** <synonyms found in code/docs>, with where each appears.
**Owned by.** [<area>](contexts/<area>/overview.md)
```

## Master index format (`INDEX.md`)

A linked table of contents grouped by the section structure above, plus a
one-line orientation at the top (what the system is) and links to GLOSSARY.md
and GAPS.md. Every page in the corpus must be reachable from here.

## Gaps format (`GAPS.md`)

Group by area. Two kinds of entry, kept distinct:

```markdown
## <Area>
### Discrepancies (docs vs code)
- **<claim>** — existing doc at `<source>` says X; code at `path/file.ext:line`
  does Y. Documented Y.

### Unverified / missing
- **<topic>** — could not confirm because <reason>. Needs <what would resolve it>.
```
