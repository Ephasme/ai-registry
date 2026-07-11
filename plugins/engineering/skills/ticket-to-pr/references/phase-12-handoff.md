# Phase 12 — HANDOFF

Close the loop with the human. They handed you a ticket and walked away; this is the artifact they
come back to. Write it so they can pick the work up cold — what shipped, where it is, and what you
left for them.

## The template

```markdown
## ticket-to-pr — <ticket id/title>

**Built:** <what shipped, mapped to the acceptance criteria — criterion by criterion>
**PR:** <url> — <state: checks green? review clean?>
**Verification:** <build/test/lint result from Phase 8, plus the Phase-11 re-verify>
**Left for you:**
- <deferred decisions / open questions you resolved by assumption — flag them>
- <review findings you disagreed with, and why>
- <minor findings carried over, not fixed>
- <follow-up tickets worth filing>
- <anything intentionally out of scope>
- <anything surfaced at a loop plateau>
```

## What earns a place in "Left for you"

Be generous here — this section is the honest part of the report, and it's what makes the rest
trustworthy. Anything that a human would be annoyed to discover later belongs in it:

- **Assumptions.** Every place you filled a gap in the spec yourself (Phase 1's GATE lets you
  proceed on a stated assumption under hands-off pre-authorization — this is where that debt comes
  due). These are the highest-value line items in the whole handoff: they're the decisions a human
  made *implicitly* by not being there.
- **Plateaus.** Anything a loop stopped on without converging (Phases 3, 4, 11).
- **Disagreements.** Review findings you chose not to act on, with your reasoning, so the human can
  overrule you.
- **Scope calls.** Things you consciously left out, and why.

## If the pipeline stopped early

If you didn't finish — a gate you couldn't satisfy, a task that failed twice, a build that wouldn't
go green, a spec that stayed ambiguous — **the handoff says where it stopped and what's blocking**,
instead of implying completion:

```markdown
## ticket-to-pr — <ticket id/title> — STOPPED AT PHASE <N> (<NAME>)

**Blocked by:** <the specific thing, with evidence — the error, the failing task, the question>
**Done so far:** <which phases completed, what's in the working tree / on the branch>
**Options:** <the ways forward you can see, with a recommendation>
```

A pipeline that stops at a real obstacle and says so is doing its job. One that produces a
confidently broken PR is not.

**Exit:** the summary is delivered. Done.

**Exit receipt example:**
`✅ Phase 12 (HANDOFF) — summary posted — PR #456 green & review-clean; 2 minors + 1 assumption (tenant-vs-key keying) flagged for review`
