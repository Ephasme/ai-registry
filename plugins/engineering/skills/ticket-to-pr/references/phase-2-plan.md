# Phase 2 — PLAN

Turn the grounded understanding into a concrete, ordered implementation plan. This plan is the
artifact Phases 3, 4, and 5 attack, and the one Phase 6 decomposes into a task graph — so its
job is to be **specific enough to be wrong**. A plan vague enough that no reviewer can disagree
with it is a plan that will produce a task graph nobody can build.

## The branch

- **IF `superpowers:writing-plans` is available** → use it. It produces a structured, reviewable
  plan in the shape the downstream phases expect.
- **ELSE** → enter plan mode and write the equivalent yourself, with the sections below.

Say which path ran.

## What the plan must contain

Whichever path produced it, the plan is only usable by Phase 6 if it carries these. If your plan
skill's output is missing one, add it.

- **Ordered steps.** What gets done, in what order, and *why that order* — the dependency
  reasoning here is the raw material for the Phase-6 DAG.
- **Files per step.** Which files each step creates or modifies. Be concrete: `src/limits/
  RateLimiter.ts (new)`, not "the rate limiting layer". Phase 6 turns these into write-sets, and
  a write-set you can't name is a task you can't parallelize safely.
- **Contracts and interfaces.** Any new type, exported symbol, endpoint, table, or event that a
  later step consumes. **Name them explicitly.** These become the edges of the DAG: step B
  depends on step A precisely when B consumes something A defines. A plan that leaves the
  interface implicit ("then wire it up") produces tasks that must negotiate the contract at
  runtime — which is exactly what parallel agents cannot do.
- **Tests.** What proves each step works, and what proves the whole thing works. Per-step tests
  become the per-task self-verification in Phase 7; without them a task isn't atomic.
- **Risks.** What could go wrong, what's uncertain, what you're assuming. Phases 3–5 hunt here
  first, and anything you flag yourself is a finding they don't have to re-derive.

## Write it down — and write *only* it

The plan must be a **file**, not a message — Phases 3–5 edit it in place across their
loop-until-clean rounds, and Phase 6 reads it.

The plan file is also the **only** thing this phase writes. Rule Zero
([`rule-zero-no-code.md`](rule-zero-no-code.md)) is in force: a plan step is a paragraph, never
a scaffolded file, a stub, an empty test, or a "starter" implementation. If plan mode is off,
or a plan skill offers to start implementing, that changes nothing — the freeze holds until
Phase 7. Put it wherever the repo keeps plans (check for
`docs/plans/`, `.plans/`, or whatever `superpowers:writing-plans` chose); otherwise
`docs/plans/<ticket-key>-<slug>.md`. Note the path — every later phase refers to it.

**Exit:** a written plan file exists, with steps, per-step files, named contracts, tests, and
risks.

**Exit receipt example:**
`✅ Phase 2 (PLAN) — used superpowers:writing-plans — docs/plans/abc-123-rate-limiting.md (7 steps, 3 contracts named)`
