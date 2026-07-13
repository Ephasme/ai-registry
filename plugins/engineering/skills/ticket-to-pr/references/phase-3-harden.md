# Phase 3 — HARDEN

The plan is a set of claims about a codebase you only partly read. Hardening checks those claims
against the code and hunts for the collateral damage the plan doesn't mention. This is the phase
that catches "add a column to `users`" when six services read that table.

## The branch

- **IF `engineering:plan-hardening` is available** → run it on the plan file. It verifies the
  plan's claims against the codebase and docs using the available tools, and surfaces failed
  claims and unhandled collateral damage.
- **ELSE** → do an inline equivalent (below).

Say which path ran.

## The inline fallback

Re-read the plan adversarially, against the code, one claim at a time. The discipline that makes
this worth doing is refusing to accept a claim because it sounds right:

- **Every factual claim gets checked.** "The handler already validates the tenant id" — go read
  the handler. "Nothing else calls this" — grep for it. A plan step resting on an unverified claim
  is a step that will fail during implementation, at the least convenient moment.
- **Every "this won't affect X" gets checked hardest.** Negative claims are where plans lie. Trace
  the callers, the tests that pin current behaviour, the config that depends on the shape you're
  changing.
- **Collateral damage.** For each file the plan touches: who else reads it, who imports it, what
  tests cover it, what the type change ripples into. Migrations, serialized formats, public APIs,
  and anything crossing a process boundary deserve extra suspicion.
- **Fix what breaks** — **in the plan file**. This is where Rule Zero
  ([`rule-zero-no-code.md`](rule-zero-no-code.md)) is most tempting to break: hardening's whole
  job is finding real defects, and a found defect *feels* like something to go fix. It isn't —
  not yet. "Fix" in this phase means **amend the plan**, never touch the code. A change you make
  here belongs to no task, so no implementer owns it and no reviewer reviews it. Write the
  paragraph; Phase 6 writes the code. If a subagent does the hardening, paste the canonical rule
  block into its prompt.

## Loop until clean

Fix every **critical/major** finding, then re-run the hardening pass. Repeat until a clean pass
(loop-until-clean, see the SKILL's Operating rules). Watch for a **plateau**: if a round stops
reducing the serious findings, or the same ones keep resurfacing, stop and surface what's left
rather than grinding — a plan that won't converge is telling you something the next round won't
fix.

Minor/nice-to-have findings don't block; carry them to the Phase-11 handoff.

## Feeding Phase 5

Keep count of what each round surfaced. Phase 5's trigger is "Phases 3–4 **kept surfacing serious
problems** — a steady stream of critical/major findings" — so the round-by-round tally *is* the
evidence for running or skipping the deep review. A plan that hardened clean in one round has
earned its skip; one that produced critical findings in three consecutive rounds has earned the
scrutiny.

**Exit:** a hardening pass with no critical/major findings (or a plateau reached and the remainder
surfaced).

**Exit receipt example:**
`✅ Phase 3 (HARDEN) — used engineering:plan-hardening — 3 rounds: 5 major → 2 major → 0; plan amended (migration back-fill, cache invalidation)`
