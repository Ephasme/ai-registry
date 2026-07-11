# Phase 4 — HANDOFF REVIEW

Phase 3 asked "is the plan *true*?" This phase asks "is the plan *unambiguous*?" — a plan can be
perfectly accurate about the codebase and still be built two incompatible ways by two competent
engineers. That's the failure this phase exists to catch, and it matters more here than in a
normal pipeline: **Phase 7 hands atomic tasks to independent agents who cannot ask each other
what a term meant.** Ambiguity that a single sequential implementer would silently resolve
becomes, in a swarm, two halves of a feature that don't fit together.

## The branch

- **IF `engineering:spec-handoff-review` is available** → run it on the plan file. It's the
  closing structural pass, built for exactly this moment: the last review before the plan goes to
  an implementer.
- **ELSE** → review the plan yourself against the lenses below.

Say which path ran.

## The lenses (and the fallback checklist)

- **Two-implementer divergence.** Read each step and ask: could two competent engineers read this
  and build incompatible things? If yes, the step is under-specified. This is the master lens —
  the others are ways of finding instances of it.
- **Interface contracts.** Every boundary the plan creates — a function signature, an endpoint, a
  payload, a table — must be pinned down: names, types, nullability, error shape. In Phase 6 these
  contracts become the DAG's edges; an unnamed contract is an edge you can't draw, and a task that
  can't be scheduled.
- **Hidden assumptions.** What is the plan taking for granted that it never says? Ordering,
  idempotency, "there's only ever one of these", "this is always called after auth".
- **Failure-mode coverage.** What does each step do when the thing it depends on fails, is
  missing, is empty, or is slow? A plan that only describes the happy path produces tasks whose
  agents each invent their own error handling.
- **Invariants.** What must stay true throughout? State them, so a task can be checked against
  them.
- **State reachability.** If the change introduces states, can every state be reached and left?
  Are there states the plan creates but never handles?
- **Verifiability.** Can each step be proven done? A step with no test is a task with no
  self-verification — and self-verification is what makes a task atomic in Phase 6.

## Loop until clean

Fix all issues; re-run until clean (loop-until-clean, see the SKILL's Operating rules). Stop and
surface at a plateau instead of grinding.

"Fix" means **edit the plan file** — Rule Zero ([`rule-zero-no-code.md`](rule-zero-no-code.md))
still holds. Pinning down an ambiguous contract means *writing the signature into the plan*, not
creating the file that declares it. Paste the canonical rule block into any subagent you dispatch
here.

As in Phase 3, keep the round-by-round tally of critical/major findings — Phases 3 and 4 together
supply the evidence for Phase 5's trigger.

**Exit:** a clean handoff review (or a plateau reached + surfaced).

**Exit receipt example:**
`✅ Phase 4 (HANDOFF REVIEW) — used engineering:spec-handoff-review — 2 rounds: 3 major (unpinned 429 payload, undefined "tenant") → 0`
