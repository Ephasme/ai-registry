# Phase 1 — UNDERSTAND

The cheapest phase to get right and the most expensive to get wrong. Everything downstream —
the plan, the hardening, the implementation — compounds whatever you decide here. A misread
requirement doesn't get caught by a green build; it gets caught by a human at review time,
after it's been implemented faithfully.

## 1. Read the ticket in full

All of it, including the parts that look like boilerplate: acceptance criteria hide in
checklists, and scope boundaries hide in throwaway sentences ("we're not doing X yet"). Read
the linked context you pulled in Phase 0 — sub-issues, linked docs, the comment thread. A
comment three replies deep saying "actually, do it per-org, not per-user" outranks the
original description.

## 2. Ground it in the code

The ticket describes the system as its author *remembers* it. Go and see how it actually works
before you believe any of it.

**Read-only, without exception** — this phase is inside the Rule Zero code freeze
([`rule-zero-no-code.md`](rule-zero-no-code.md)). Exploring means reading, searching, and
running existing tests to see what they say. It never means "let me just try the change and
see". If a subagent does the exploring, paste the canonical rule block into its prompt; prefer
`Explore`, which cannot edit at all.

- Use the **Explore** agent for breadth ("where is rate limiting enforced, and what enforces
  it?"), or search + targeted reads when you already know roughly where to look.
- Read every file the ticket names, plus the ones it implies: the callers of what you'll
  change, the tests that currently pin the behaviour, the config that switches it on.
- Note where the ticket and the code **disagree**. That gap is either a stale ticket or a
  misunderstanding, and either way it's an open question — not something to quietly resolve
  in the code's favour.

## 3. Restate

Write it out, concisely:

- **Goal** — the outcome, stated briefly.
- **Scope** — what's in, and explicitly what's out.
- **Acceptance criteria** — how "done" is judged. Each one must be *checkable*: if you can't
  imagine the command or the observation that proves it, it isn't a criterion yet.
- **Affected components** — files/modules/services you expect to touch. This is the first
  rough draft of the plan's per-task files (Phase 2), so be concrete.
- **Open questions** — anything ambiguous, missing, or contradictory.

## GATE — ask, don't invent

If anything is unclear or under-specified — fuzzy acceptance criteria, an undefined term, a
decision the ticket leaves open, a conflict between the ticket and the code — **stop and ask
the human targeted questions.**

Targeted means answerable: not "can you clarify the requirements?" but "the ticket says
per-tenant, but `RateLimiter` keys by API key and one tenant can hold several — do you want
one budget per tenant shared across keys, or per key?" Offer the options you can see and say
which you'd pick. A precise question gets a precise answer; a vague one gets "yes, do it well".

**Do not invent requirements or acceptance criteria to fill a gap.** A confidently wrong
assumption here is the most expensive error in the whole pipeline. If you must proceed on an
assumption (the human is away and pre-authorized hands-off completion), then **state it
explicitly, mark it as an assumption in the plan, and carry it to the Phase-11 handoff** so it
gets reviewed rather than silently shipped.

**Exit:** a written restatement, with the open questions resolved (or explicitly flagged as
assumptions).

**Exit receipt example:**
`✅ Phase 1 (UNDERSTAND) — restated goal/scope/AC, explored src/limits/** — 2 open questions asked & answered (tenant-vs-key keying, 429 vs 503)`
