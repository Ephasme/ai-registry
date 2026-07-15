# Phase 1.5 — BRAINSTORM (conditional)

Phase 1 settles *what* the ticket asks for. This phase settles *how* — the shape of the solution —
but only when that is actually an open question. It sits between UNDERSTAND and PLAN on purpose:
the plan (Phase 2) is where a design gets locked into an ordered task list, and Phases 3–5 then
harden *that* plan. None of them reconsiders the approach; they sharpen the one you brought. So a
wrong-but-well-planned design sails through every downstream gate. This step is the one place
built to catch it — before it's a plan.

It is conditional because most tickets don't need it, and running it on a prescriptive ticket
just burns tokens restating the obvious. The judgement about when it's worth it is yours, and
making that call well *is* the phase.

## Deciding: run it, or skip it

**Run it** when the ticket fixes an outcome but leaves the road there open. Concretely:

- Several viable approaches exist with real trade-offs (sync vs. queue, extend an existing
  abstraction vs. add a new one, store-then-project vs. compute-on-read).
- A choice made now ripples through every later task — a data model, an API/interface shape, a
  boundary between components. Cheap to decide on paper, expensive to unpick once tasks assume it.
- The ticket says "improve/redesign/rethink X" — open by construction.
- Phase 1 left you with two defensible readings of *how* even though *what* is clear.

**Skip it** when there's nothing to diverge on:

- The ticket is already prescriptive ("add field `Y` to table `Z`, expose it in the `/foo`
  response").
- The change is small and well-bounded — a bug fix, a copy change, a config toggle.
- There is one obvious way to build it and no reviewer would argue for another.

When you're genuinely unsure, lean toward a short brainstorm. Getting the approach wrong is the
failure mode this pipeline is *worst* at catching — the hardening phases assume the design is
sound and attack the details. A few minutes of divergence here is cheap insurance; a re-plan
after Phase 6 discovers the approach was wrong is not.

## Running it

- **IF `superpowers:brainstorming` is available** → use it. It's designed for pre-planning
  divergence: drawing out intent, generating options, and pressure-testing them before any plan
  exists — which is exactly this phase's job. Say you used it.
- **ELSE** → do an inline equivalent, and say you did: lay out 2–3 candidate approaches, and for
  each name the trade-offs, the risk it carries, and what it costs to reverse. Then pick one and
  write down *why* — the reason is what Phase 2 plans against and what a reviewer can later check.

Either way the deliverable is small: a chosen direction and the reasoning behind it, concrete
enough that Phase 2 can turn it into tasks without re-litigating the design.

## The freeze still holds (Rule Zero)

This phase is inside the code freeze ([`rule-zero-no-code.md`](rule-zero-no-code.md)).
Brainstorming is discussion, not construction — its output is a *direction*, never code and never
an edit to the tree. A "quick spike to see if it works" is still writing code before Phase 6, and
it's forbidden here like everywhere in 0–5. If you need evidence that an approach is feasible,
gather it read-only: read the code, run existing tests, trace the call paths — the same tools
Phase 1 used.

If the brainstorm turns up a new open question about the **requirement** (not just the design) —
you realise the *what* was ambiguous after all — don't resolve it here. Loop back to Phase 1's
GATE and ask the human, then come back and finish choosing the approach.

## Exit

A chosen approach with its rationale, ready to plan against — or an explicit, justified skip.

**Exit receipt examples:**
`✅ Phase 1.5 (BRAINSTORM) — ran superpowers:brainstorming — chose per-tenant token bucket over per-key (shared budget matches the AC), 2 approaches weighed`
`✅ Phase 1.5 (BRAINSTORM) — skipped: ticket is prescriptive (add nullable column + expose in response), one obvious approach`
