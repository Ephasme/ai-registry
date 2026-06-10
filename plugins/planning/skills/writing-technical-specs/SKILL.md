---
name: writing-technical-specs
description: >-
  Turns a large body of existing research — ADRs, proposals, context docs,
  tickets, investigation notes — into a rigorous, implementation-ready technical
  specification. Fans the reading across parallel subagents, surfaces the
  architectural decisions the spec depends on, records the settled ones as ADRs
  and presents still-open ones as 4–5 reasoned proposals with a recommendation
  (stopping to ask the user to choose before writing), then writes the full spec
  against a standards-grounded structure (IEEE 29148/1016, arc42, C4, RFC 2119,
  Google/Amazon design-doc practice). Use whenever the user wants to write,
  draft, author, or produce a technical spec, design doc, RFC, SDD, or software
  requirements/architecture document from accumulated research — especially a
  large or scattered corpus. Reach for it even when they say "turn this research
  into a spec", "write up the design", or "now produce the implementation doc",
  not only when they say the word "spec".
---

# Writing Technical Specs

Turn a pile of research — prior ADRs, proposals, context docs, tickets, threads,
investigation notes — into **one implementation-ready specification**: a document
a developer can build from without re-deriving the analysis or guessing at the
decisions.

The hard part of this task is not prose. It is three things, and the phases below
exist to solve them in order:

1. **Digesting a large corpus without losing fidelity or inventing detail.** You
   fan the reading out across subagents, then merge — rather than skimming and
   confabulating.
2. **Making the decisions explicit before writing.** A spec is only as good as the
   architectural decisions underneath it. Most weak specs are weak because a
   decision was quietly assumed instead of being surfaced, resolved, and recorded.
3. **Writing to a structure that is actually actionable** — concrete interfaces,
   data shapes, sequencing, failure modes, rollout — not a template padded with
   hand-waving.

## Operating principles (these are the whole point)

- **Read the codebase — it is the ground truth. This is paramount.** The research
  corpus tells you what people *thought, intended, and proposed*; the code tells
  you what is *actually true today*. Before and while you write, read the real
  code the spec will touch — entry points, modules, entities, interfaces, call
  sites, schemas, configs, migrations — and ground every structural claim in it
  with a `file:line` citation. A spec built only from the corpus inherits all of
  its drift and wishful thinking. Where the corpus and the code disagree, **the
  code wins** and you record the discrepancy. A spec that doesn't match the
  codebase it will be implemented in is worse than no spec, because it sends
  developers confidently in the wrong direction. Every phase below reads code, not
  just documents.
- **Decisions before prose.** Surface the decisions the spec depends on, resolve
  each one explicitly (an ADR for the settled, a proposal-and-ask for the open),
  and only then write. Writing prose over an unresolved decision produces
  confident fiction that someone discovers is wrong mid-implementation.
- **Cite or refuse.** Every non-trivial claim traces to something — a `file:line`
  in the code (preferred for anything structural), a document in the corpus, a
  ticket, or a named external source. What you cannot back, you mark as an
  assumption or an open question; you do not assert it. This is the IEEE 29148
  verifiability/traceability discipline applied to the spec itself, and it is what
  separates a spec from a wish.
- **Don't invent to fill the template.** A section with nothing real to say is
  omitted or marked "N/A — *why*", never padded. arc42, Spolsky, and Larson all
  converge here: a heavyweight template filled with filler is worse than a short
  doc that says only what is true. Pick the sections the spec actually needs.
- **Implementation-ready means a developer can act on it.** Lead with trade-offs
  and rationale (the parts that are expensive to reconstruct), not with restating
  the obvious. If a reasonable engineer on the team couldn't build the thing from
  your spec, it isn't done.

---

## Phase 0 — Scope the corpus and the spec

Before reading anything in depth, establish these and confirm them with the user
if they're unclear:

- **The corpus.** What research constitutes the input — which docs, folders,
  tickets, threads, notes. If the user hasn't pointed at it, ask. Don't
  reconstruct the research from memory; work from the actual material.
- **The codebase the spec plugs into.** Orient in the real system early: the entry
  points, the modules/services the design touches, the entities and schemas, the
  seams the new work will attach to, and how it's built and deployed. Establish
  the *actual current state* from the code — not from what the corpus says the
  state is. This orientation is what lets you partition the reading sensibly and
  catch corpus-vs-code drift later.
- **The spec's job.** What is being specified, for whom (the audience), the
  boundary (what's in scope vs explicitly out), and — most important — *what
  decision or work the spec must enable*. A spec with no clear job sprawls.

Then **right-size the output**. A spec is worth writing when the design is
ambiguous, reusable by many future projects, user-impacting, or more than ~a
month of work (Larson's thresholds; Google's "write when ambiguous"). Match depth
to that: a 1–3 page mini-spec for incremental work, a fuller 10–20 page spec for a
large or load-bearing design (Google). Over-producing a doc nobody needs is a
failure mode, not thoroughness.

---

## Phase 1 — Fan out the reading

For a corpus too large to hold in one context with care, **partition it and spawn
5–10 subagents in parallel**, one per slice, each running the brief in
`references/reader-brief.md`. You (the lead) do **not** read everything yourself —
you merge what the readers return.

- **Each reader reads code, not just docs.** This is the point of the whole
  phase. A slice is a *subsystem* — its corpus material **and the actual code that
  implements it**. Every reader verifies the corpus claims in its slice against
  the code and reports where they diverge. Prefer partitioning by subsystem/domain
  precisely so each reader owns a coherent chunk of code plus the docs about it.
- **Partition for disjointness.** Slice so the code+doc areas don't overlap and
  leave no gap. Overlap wastes work and breeds contradictions; gaps cause silent
  incompleteness. Make the partition explicit before you fan out.
- **Demand structured notes, not prose.** Each reader returns: key facts with
  citations (`file:line` for anything structural), the real current-state of its
  code area, decisions made or implied, constraints, open questions,
  corpus-vs-code discrepancies, and glossary terms. The brief specifies the exact
  return shape so the slices stitch together.
- **Small corpus / small system?** If it's a handful of documents over a small
  area of code, just read the docs and that code directly and skip the fan-out.
  The machinery is for scale, not ceremony — but the code still gets read.

---

## Phase 2 — Merge and map the decisions

Merge the readers' notes into one consolidated picture (facts, constraints,
glossary, contradictions, **and the verified current-state of the code**). Then do
the step that makes or breaks the spec: **extract the decision list.**

A decision belongs on the list if it "affects the structure, non-functional
characteristics, dependencies, interfaces, or construction techniques" of the
system (Nygard's architectural-significance test). For each decision, classify it:

- **Settled** — the research or the user has already determined it, with clear
  evidence (a recorded decision, an unambiguous constraint, an existing
  commitment). It becomes an ADR.
- **Open** — genuinely undetermined; the spec cannot be written honestly without
  choosing. It needs a proposal and the user's call.

**Check each decision against the code before classifying it.** The code often
moves a decision: one the corpus treats as open may be effectively settled by what
the code already does, and one the corpus records as settled may be contradicted
by the current implementation (in which case it's open again, and the discrepancy
is itself a finding). Don't classify from the corpus alone.

Be ruthlessly honest about the split. A decision you *assume* is settled because
it's convenient is the most dangerous item in the whole process. **Present the
decision list to the user as a checklist** (settled vs open, one line each, with
the code evidence) and let them correct the classification before you start
resolving anything.

---

## Phase 3 — Resolve every decision explicitly

Read `references/decision-records.md` for both templates, then handle each
decision according to its class:

- **Settled → ADR.** Record it: context, decision, alternatives considered, and
  consequences (the canonical Nygard fields; use the richer MADR fields when the
  decision warrants). One decision per record, numbered, and immutable — a later
  reversal supersedes it rather than editing it.
- **Open → proposal, then STOP.** Present **4–5 concrete, reasoned options**, each
  with its trade-offs assessed *against the actual codebase* — what each would cost
  to build given how the code is structured today, what it touches, what it breaks
  — not in the abstract. Name a **recommended option with the reasoning**. Then
  **stop and ask the user to choose** before continuing — use a structured
  question tool if one is available (these are exactly pick-between-options-with-
  tradeoffs decisions). Gather *all* open decisions and ask them in as few rounds
  as possible rather than dripping one at a time. **Do not write the spec over an
  open decision.** Once the user chooses, that option becomes an ADR.

This stop-and-ask is not optional politeness — it's the control that keeps the
spec from encoding a choice the user never actually made.

---

## Phase 4 — Write the spec

Only once every decision is resolved. Use `references/spec-template.md` and adapt
it to the spec type and depth:

- **Requirements-heavy** (what the system must do) → lean on the SRS sections.
- **Design/architecture-heavy** (how it's built) → lean on the design/SDD and
  architecture sections (C4 views, building blocks, data model, interfaces).
- **Proposal/RFC** (should we do this, and how) → lean on context, goals/non-
  goals, proposed design, alternatives, rollout.

Most real specs are a blend; the template tells you which sections to pull.
While writing:

- **Reconcile every part of the design with the real code.** The architecture and
  building-block views map to actual modules/files (cite them, `file:line`); the
  data model matches the real entities and migrations; the interfaces match the
  real call sites. State precisely what changes, what is added, and what stays —
  in terms of the code that exists today. If you find yourself describing
  structure you haven't located in the code, stop and go read it.
- **Embed or link the ADRs** from Phase 3 so the rationale travels with the spec.
- **Make requirements uniquely identified and verifiable**, and use the RFC 2119
  keywords (MUST / SHOULD / MAY, all-caps) for normative statements so there's no
  ambiguity about what is mandatory.
- **Carry a traceability thread**: need → requirement → design element → test.
- **Cover the cross-cutting concerns that genuinely apply** — security, privacy,
  data model & migrations, API contracts, observability, failure modes,
  performance/SLOs, rollout, rollback, testing — and mark the ones that don't as
  "N/A — *why*" rather than omitting them silently.

---

## Phase 5 — Self-check before handoff

Walk this checklist; fix anything that fails:

- [ ] Every structural claim about the system was verified against the code and
      cites `file:line`; every corpus-vs-code discrepancy found is recorded, not
      glossed over.
- [ ] Every architectural decision is either an ADR or an answered open question —
      none are silently assumed.
- [ ] Every requirement is uniquely identified and verifiable (you could write a
      test for it).
- [ ] Every non-trivial claim cites the code (preferred), the corpus, or a named
      source; unbacked statements are marked as assumptions/open questions.
- [ ] Cross-cutting concerns are addressed or explicitly marked N/A with a reason.
- [ ] The traceability thread holds (needs map to requirements map to design map
      to tests).
- [ ] No section is padded with invented detail; sections with nothing to say are
      omitted or marked N/A.
- [ ] A developer on this team could build it without coming back to ask what was
      meant.

Then tell the user where the spec lives, summarize the decisions taken (and any
the spec still rests on as assumptions), and offer to harden it with the
`plan-hardening` skill — this skill produces the spec; that one stress-tests it
against the codebase.

---

## Reference files

- `references/reader-brief.md` — the copy-paste subagent prompt for the Phase 1
  fan-out, with the exact structured-output shape each reader must return.
- `references/decision-records.md` — the ADR template (settled decisions) and the
  open-decision proposal template (the 4–5 options + recommendation + stop-and-ask
  protocol). Read in Phase 3.
- `references/spec-template.md` — the implementation-ready spec structure, with
  per-section guidance and how to adapt it by spec type and depth. Read in Phase 4.
- `references/sources.md` — the authoritative grounding (IEEE/ISO standards,
  arc42, C4, ADR/MADR, RFC 2119, SRE, and the design-doc practitioners) behind
  every template here, with caveats on what is and isn't verified.
