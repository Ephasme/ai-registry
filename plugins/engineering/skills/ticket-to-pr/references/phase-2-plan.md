# Phase 2 — PLAN

Turn the grounded understanding into a concrete, ordered implementation plan. This plan is the
artifact Phases 3, 4, and 5 attack, and the one Phase 6 hands task by task to
`superpowers:subagent-driven-development` — so its job is to be **specific enough to be wrong**.
A plan vague enough that no reviewer can disagree with it is a plan nobody can implement task by
task, either.

## The branch

- **IF `superpowers:writing-plans` is available** → use it. It produces a structured, reviewable
  plan with numbered `### Task N` sections — the exact shape
  `superpowers:subagent-driven-development` reads in Phase 6.
- **ELSE** → enter plan mode and write the equivalent yourself, with the sections below, using
  `### Task N: <title>` headings for each task (Phase 6's tooling extracts tasks by that heading).

Say which path ran.

## What the plan must contain

Whichever path produced it, the plan is only usable by Phase 6 if it carries these. If your plan
skill's output is missing one, add it.

- **Numbered tasks, in order.** What gets done, in what order, and *why that order* — each as its
  own `### Task N` section Phase 6 can hand to one implementer at a time.
- **Files per task.** Which files each task creates or modifies. Be concrete: `src/limits/
  RateLimiter.ts (new)`, not "the rate limiting layer" — a task with a nameable footprint is one a
  reviewer can hold the implementer to.
- **Contracts and interfaces.** Any new type, exported symbol, endpoint, table, or event that a
  later task consumes. **Name them explicitly.** A plan that leaves the interface implicit ("then
  wire it up") produces a task whose implementer has to invent the contract on the spot — often
  wrong, and expensive to unwind once a later task is already built against it.
- **Tests.** What proves each task works, and what proves the whole thing works. Per-task tests
  become the implementer's own self-verification in Phase 6; without them a task can't be checked
  done on its own.
- **Risks.** What could go wrong, what's uncertain, what you're assuming. Phases 3–5 hunt here
  first, and anything you flag yourself is a finding they don't have to re-derive.

## Write it down — and write *only* it

The plan must be a **file**, not a message — Phases 3–5 edit it in place across their
loop-until-clean rounds, and Phase 6 reads it.

The plan file is also the **only** thing this phase writes. Rule Zero
([`rule-zero-no-code.md`](rule-zero-no-code.md)) is in force: a plan step is a paragraph, never
a scaffolded file, a stub, an empty test, or a "starter" implementation. If plan mode is off,
or a plan skill offers to start implementing, that changes nothing — the freeze holds until
Phase 6. Put it wherever the repo keeps plans (check for
`docs/plans/`, `.plans/`, or whatever `superpowers:writing-plans` chose); otherwise
`docs/plans/<ticket-key>-<slug>.md`. Note the path — every later phase refers to it.

**Exit:** a written plan file exists, with steps, per-step files, named contracts, tests, and
risks.

**Exit receipt example:**
`✅ Phase 2 (PLAN) — used superpowers:writing-plans — docs/plans/abc-123-rate-limiting.md (7 steps, 3 contracts named)`
