---
name: ticket-to-pr
description: >-
  Drive a single ticket or specification from spec all the way to a reviewed pull
  request — end to end: understand → plan → harden → handoff-review → (conditional
  deep review) → implement → verify → branch/commit/push/PR → code-review →
  fix-until-clean → handoff. Use this when the user hands over a unit of work to be
  taken to completion: a Notion page/ID, a GitHub Issue or Project item, a Linear
  issue, or a raw written spec (pasted or a file path), and says something like
  "take this ticket to a PR", "implement NID-123 end to end", "ship this issue",
  "do this spec and open a PR", or "drive this from spec to merge". It commits,
  pushes, and opens PRs, so it is explicit-invocation only and never auto-triggers.
disable-model-invocation: true
---

# ticket-to-pr — from specification to a reviewed PR

Take one ticket and carry it the whole distance: read and ground the spec, plan it,
harden the plan, implement, prove it works, open a PR, get it reviewed, and fix
findings until the PR is clean — then hand it back with a summary. The value is in
the *gates between phases*: each step refuses to advance on a shaky foundation, so a
misread requirement or a red test never silently rides through to a merged PR.

This skill orchestrates other skills rather than reimplementing them. Where a
specialist skill exists (`superpowers:writing-plans`, `engineering:plan-hardening`,
…), it delegates; where one is missing, it states and uses a fallback. It runs only
when you invoke it explicitly — it pushes branches and opens PRs, which must never
happen on a guess.

## At a glance

```
0  IDENTIFY INPUT   → which ticket/spec, from where
1  UNDERSTAND       → read + ground in code; restate; GATE: ask if unclear
2  PLAN             → writing-plans  (else plan mode)
3  HARDEN           → plan-hardening, loop-until-clean (cap 3)
4  HANDOFF REVIEW   → spec-handoff-review, loop-until-clean (cap 3)
5  DEEP REVIEW      → only if ≥3 critical/major surfaced in 3–4, or asked (multi-agent workflow)
6  IMPLEMENT        → executing-plans  (else implement directly)
7  VERIFY           → build/test/lint must pass, with evidence
8  BRANCH→PR        → GATE: confirm before push & PR; link the ticket
9  CODE REVIEW      → code-review (working diff) / review (open PR)
10 FIX FINDINGS     → address all, push, re-review, loop-until-clean (cap 3)
11 HANDOFF          → summary, PR link, leftovers → back to the human
```

## Operating rules (apply to every phase)

These four behaviours recur throughout; internalize them once so each phase stays short.

- **Loop-until-clean, with a cap.** Whenever a phase says "fix all issues", it means:
  fix every **critical/major** finding, then re-run the reviewer; repeat until a clean
  pass (no critical/major) — capped at **3 rounds**. Minor/nice-to-have findings don't
  block; note them for the handoff. If you hit the cap still dirty, **stop and surface
  the remaining findings to the human** with what you tried. The cap exists to prevent
  thrash and infinite loops; surfacing-not-hiding keeps the human's trust that "clean"
  means clean.

- **Check availability, then branch — and say which path you took.** Several phases read
  "IF skill X is available → use it, ELSE fallback". Actually check whether the named
  skill/command is offered in this session (it appears in the available skills/commands
  list) before assuming it. Use it if present; otherwise use the stated fallback. Either
  way, tell the human which path ran — "used `engineering:plan-hardening`" vs "plan-
  hardening unavailable, did an inline hardening pass" — so they know whether the
  rigorous tool or the substitute did the work.

- **Confirm before anything irreversible or outward-facing.** Pushing a branch, opening a
  PR, and posting review comments leave your fingerprints on shared infrastructure. Pause
  for explicit go-ahead before those, unless the human pre-authorized hands-off completion
  ("just take it all the way", "don't stop to ask"). Local work (reading, planning,
  editing, committing locally) needs no such pause.

- **Evidence before assertions.** Never say a build passed, tests are green, or review is
  clean without showing the command and its output. "Tests pass" is a claim; the pasted
  test summary is evidence. If something failed or you skipped a step, say so plainly.

---

## Phase 0 — Identify the input

Determine *what* to work on and *where it lives* before anything else. Accept any of:
a **Notion** page (URL or ID), a **GitHub** Issue or Project item, a **Linear** issue, or
a **raw spec** (pasted into chat or a file path). Detect the source from what was given —
URL shape, ID pattern, or "here's the spec" — and read it through the right channel.

If the user gave nothing to work from, **ask which ticket or spec** to drive; don't pick one.

Source detection, the tool for each, and the fallback when an MCP isn't connected are in
[`references/input-sources.md`](references/input-sources.md) — read it now if the source is
anything other than a spec already pasted in front of you.

## Phase 1 — UNDERSTAND

Read the ticket/spec **in full**, then ground it in reality: explore the relevant code,
folders, and docs so your understanding is anchored in how the system actually works, not
how the ticket imagines it. Use the **Explore** agent (or search + targeted reads) to find
the affected components and read any files the ticket references.

Then **restate**, concisely:
- **Goal** — the outcome in one or two sentences.
- **Scope** — what's in, and explicitly what's out.
- **Acceptance criteria** — how "done" is judged.
- **Affected components** — files/modules/services you expect to touch.
- **Open questions** — anything ambiguous, missing, or contradictory.

**GATE:** if anything is unclear or under-specified — fuzzy acceptance criteria, an
undefined term, a decision the ticket leaves open — **stop and ask the human targeted
questions.** Do not invent requirements or acceptance criteria to fill the gap; a confidently
wrong assumption here is the most expensive error in the whole pipeline, because every later
phase compounds it. **Exit:** a written restatement, with open questions resolved.

## Phase 2 — PLAN

Turn the understanding into a concrete, ordered implementation plan.

- **IF `superpowers:writing-plans` is available** → use it; it produces a structured,
  reviewable plan.
- **ELSE** → enter plan mode and write an equivalent plan yourself: the steps in order,
  the files each touches, the tests, and the risks.

**Exit:** a written plan exists — a plan file, or a plan-mode artifact you can hand to the
next phase.

## Phase 3 — HARDEN

Run the plan through **`engineering:plan-hardening`**, which verifies the plan's claims
against the codebase and surfaces unhandled collateral damage. Fix every critical/major
finding and re-run (loop-until-clean, cap 3 — see Operating rules). If `plan-hardening`
isn't available, do an inline equivalent: re-read the plan adversarially against the code,
checking each claim and each "this won't affect X" assumption, and fix what breaks.

**Exit:** a hardening pass with no critical/major findings (or the cap reached and the
remainder surfaced).

## Phase 4 — HANDOFF REVIEW

Run **`engineering:spec-handoff-review`** — the closing structural pass that hunts for
ambiguity, missing contracts, and unstated assumptions that would let two engineers build
incompatible things. Fix all issues; re-run until clean (cap 3). Fallback if unavailable:
review the plan yourself for two-implementer divergence, hidden assumptions, and unhandled
state transitions, and resolve them.

**Exit:** a clean handoff review (or cap reached + surfaced).

## Phase 5 — DEEP REVIEW (conditional)

This is heavier multi-agent scrutiny, run **only when warranted** — it costs real tokens, so
it's gated:

- **TRIGGER:** phases 3–4 together surfaced a **high volume of serious problems — ≥ 3
  critical/major findings total** — OR the human explicitly asks for a deep review. If
  neither holds, **skip to Phase 6** and say you skipped it and why (the plan was clean
  enough). Invoking this skill is itself the opt-in for the multi-agent work this phase
  uses, so no extra permission is needed when the trigger fires.

- **WHAT:** spawn a dynamic multi-agent workflow that (a) splits the plan into scopes and has
  one **Sonnet 4.6** agent review each scope for bugs/risks; (b) has a **second Sonnet 4.6**
  agent independently **confirm/refute** each candidate bug; (c) scores each surviving bug's
  criticality with a **Haiku** agent; and (d) returns the reconciled findings for **you (the
  Opus 4.8 orchestrator)** to fix in the plan. The find→verify split keeps plausible-but-wrong
  findings from surviving; the independent verifier is the point.

The ready-to-adapt workflow script, the per-stage output schemas, and the fallback for when
the Workflow tool isn't available are in
[`references/deep-review-workflow.md`](references/deep-review-workflow.md).

**Exit:** a reconciled plan with every *confirmed* issue fixed.

## Phase 6 — IMPLEMENT

- **IF `superpowers:executing-plans` is available** → use it to work the plan with its
  built-in review checkpoints.
- **ELSE** → implement the plan directly. Follow the **existing repo conventions** (match the
  surrounding code's style, structure, and idioms) and keep the diff **scoped to the ticket** —
  resist drive-by refactors and unrelated cleanups; they make review harder and dilute the PR.

**Exit:** the plan is implemented in the working tree.

## Phase 7 — VERIFY

Run the project's **build, tests, and lint** and confirm they pass **before claiming
anything**. Use `superpowers:verification-before-completion` if available; otherwise run the
project's own commands (discover them from `package.json` / `Makefile` / `justfile` / CI
config) and read the output. Evidence before assertions (Operating rules).

**GATE:** if anything is red, go back to Phase 6 and fix it — do **not** proceed to a PR on a
broken build. If it can't be made green (environmental, flaky, out of scope), stop and tell
the human exactly what's failing rather than papering over it.

**Exit:** build/test/lint green, with the output shown.

## Phase 8 — BRANCH / COMMIT / PUSH / PR

**GATE — confirm before push and PR** unless the human pre-authorized hands-off completion.
Then:

1. Create a **feature branch** (never commit straight to the default branch).
2. Commit with a clear message; match the repo's commit conventions (prefix style, any
   required trailers/sign-off).
3. **Push** the branch and **open a PR** with a description that links the ticket, summarizes
   the change, and includes the Phase-7 verification evidence.
4. For a **Notion** ticket, prefix the PR title with the ticket ID — e.g. `[NID-123] …` — so
   the Notion↔GitHub integration auto-links the PR to the ticket.

Branch naming, the PR body template, ticket-linking per source, and which tool opens the PR
(GitHub MCP vs `gh`) are in [`references/pr-and-review.md`](references/pr-and-review.md).

**Exit:** an open PR, its URL captured for the handoff.

## Phase 9 — CODE REVIEW

Get the change reviewed:
- **Prefer the `code-review` skill/command** on the working diff (`/code-review`).
- For the **already-open GitHub PR**, use **`/review`** (it reviews the PR on GitHub).
- **Fall back to `/code-review`** on the diff if the others aren't available.

State which reviewer ran. **Exit:** a review with its findings enumerated.

## Phase 10 — FIX REVIEW FINDINGS

Address **every** finding, push the fixes, and **re-review until clean** (loop-until-clean,
cap 3). Re-run Phase 7's verification after fixes so you don't trade a review nit for a broken
build. If posting review-comment replies, that's outward-facing — confirm first unless
pre-authorized. **Exit:** a review pass with no critical/major findings (or cap reached +
surfaced).

## Phase 11 — HANDOFF

Close the loop with the human:
- **What was built** — a short summary tied back to the acceptance criteria.
- **The PR** — link, and its current state (green checks? review clean?).
- **Leftovers** — deferred decisions, follow-up tickets worth filing, anything you
  consciously left out of scope, and any findings surfaced at a loop cap.

Then hand it back. The handoff template is in
[`references/pr-and-review.md`](references/pr-and-review.md). Done.

---

## If a phase can't proceed

Honesty beats a clean-looking result. If a gate can't be satisfied (the spec stays
ambiguous after questions, a loop hits its cap, the build won't go green, an MCP/skill you
need is absent with no workable fallback), **stop at that phase and report** where you are,
what's blocking, and the options — rather than forcing past it. A pipeline that stops at a
real obstacle is more useful than one that produces a confidently broken PR.
