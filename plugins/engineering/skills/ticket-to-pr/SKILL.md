---
name: ticket-to-pr
description: >-
  Drive one ticket or spec all the way to a reviewed pull request: understand it, plan it,
  harden the plan, split it into a task graph, implement it with a parallel builder/reviewer
  swarm, verify, open the PR, and fix findings until it is clean. Use when the user hands over
  a unit of work to take to completion — a Notion page/ID, a GitHub Issue or Project item, a
  Linear issue, or a raw spec (pasted or a file path) — and asks to take it to a PR, ship it,
  or drive it end to end. It commits, pushes, and opens PRs, pausing to confirm those unless
  you pre-authorize hands-off completion.
---

# ticket-to-pr — from specification to a reviewed PR

Take one ticket and carry it the whole distance: read and ground the spec, plan it,
harden the plan, break it into a task graph, implement it, prove it works, open a PR, get
it reviewed, and fix findings until the PR is clean — then hand it back with a summary.
The value is in the *gates between phases*: each step refuses to advance on a shaky
foundation, so a misread requirement or a red test never silently rides through to a
merged PR.

This skill orchestrates other skills rather than reimplementing them. Where a specialist
skill exists (`superpowers:writing-plans`, `engineering:plan-hardening`, …), it delegates;
where one is missing, it states and uses a fallback. It runs only when you invoke it
explicitly — it pushes branches and opens PRs, which must never happen on a guess.

## RULE ZERO — no code before Phase 7 (absolute, overrides everything below)

**No agent — the orchestrator included — writes a line of product code before Phase 7
(IMPLEMENT).** Phases 0–6 are a **code freeze**; it lifts at Phase 7 and stays lifted for 7–11.

It outranks every other instruction in this skill, and every mode: plan mode or not,
auto-accept-edits, a hands-off pre-authorization, a subagent that "was only exploring", a fix
that is one obvious line. Nothing licenses an early edit.

Why it is absolute: this pipeline's whole value is that the plan gets attacked (Phases 3–5) and
split (Phase 6) *before* anything is built. Code written earlier skipped both — it belongs to no
task, so no builder owns it, no reviewer reviews it, and no wave gate covers it, and it rides
into the PR as unreviewed work everyone downstream assumes was vetted. A change you are certain
of in Phase 3 costs one paragraph in the plan file; the same change smuggled into the tree costs
the pipeline its guarantees.

**Enforcing it, every run:**

- **Paste the canonical rule block from [`references/rule-zero-no-code.md`](references/rule-zero-no-code.md)
  verbatim into every subagent you dispatch in Phases 0–6**, whatever its job. Assume no agent
  knows this rule unless you tell it.
- **Prefer read-only agents** (`Explore`) for exploration — a tool the agent doesn't have is a
  rule it cannot break.
- **If an agent broke the freeze**, revert the edit, say so, and re-enter the change as a plan
  amendment. It never reaches Phase 7's base commit.
- **Phase 6 verifies the freeze held** — `git status --porcelain` shows nothing but the plan and
  the `.ticket-to-pr/` artifacts.

That reference is the single source for what counts as code, the four things you *may* write, and
what to do when you think you need an exception.

## At a glance

```
                     ┌─────────────── CODE FREEZE (Rule Zero) ───────────────┐
0  IDENTIFY INPUT    │ which ticket/spec, from where                         │
1  UNDERSTAND        │ read + ground in code; restate; GATE: ask if unclear  │
2  PLAN              │ writing-plans  (else plan mode)                       │
3  HARDEN            │ plan-hardening, loop-until-clean                      │
4  HANDOFF REVIEW    │ spec-handoff-review, loop-until-clean                 │
5  DEEP REVIEW       │ only if 3–4 kept surfacing serious findings, or asked │
6  TASK GRAPH        │ atomic tasks → dependency DAG → ordered waves; pick   │
                     │ each task's builder + reviewer models                 │
                     │ GATE: show the graph — last cheap checkpoint, and     │
                     └─ verify the freeze held (working tree clean of code) ─┘
7  IMPLEMENT      ← ─ ─ the freeze LIFTS here, and only here ─ ─
                     run the graph wave by wave. Per task: an isolated worktree, a builder,
                     then an independent reviewer (spec + quality) + fix loop — parallel
                     within a wave
8  VERIFY           → build/test/lint must pass, with evidence
9  PUSH→PR          → GATE: confirm before push & PR; link the ticket
10 CODE REVIEW      → code-review (working diff) / review (open PR)
11 FIX FINDINGS     → address all, push, re-review, loop-until-clean
12 HANDOFF          → summary, PR link, leftovers → back to the human
```

**Phases vs waves.** *Phases* are the thirteen numbered steps above (0–12) — the pipeline.
*Waves* (W1, W2, …) exist only inside Phases 6–7: they are the dependency levels of the
task graph. The two never share a numbering.

## Before you begin — the phase ledger (mandatory)

This pipeline only works if every phase actually runs, in order, with its gate honoured. To
make that auditable instead of best-effort, **do these two things — they are not optional:**

1. **Open the ledger first.** Before Phase 0, call **TodoWrite** with all thirteen phases
   (0–12) as separate items, in order. This is the first action the skill takes — before
   reading the ticket, before any tool call. The ledger stays in front of you for the whole
   run so a phase can't quietly fall off.

2. **Advance one phase at a time, and only on a receipt.** Exactly one phase is
   `in_progress` at any moment. You may mark a phase `completed` **only after** you have
   printed its **exit receipt** (see the operating rule below) — the receipt *is* the
   completion criterion. Then move the next phase to `in_progress`. Do not batch-complete,
   do not skip ahead, and do not mark a phase done because it "probably would have passed".

The only sanctioned deviations from strict 0→12 order are the ones the phases themselves
document: **Phase 5** may be skipped (say so, with the receipt noting *why*), and a failed
gate sends you **back** to an earlier phase — **Phase 7** (a failed task or wave gate) back
to Phase 6 or 2, **Phase 8** (red build) back to Phase 7, **Phase 11** (review findings)
back to Phase 7 and then 8. When you go back, **re-open that todo**; don't leave it falsely
complete. Any other skip is a bug in your execution, not a shortcut.

## Operating rules (apply to every phase)

These behaviours recur throughout; internalize them once so each phase stays short. **Rule Zero,
above, outranks every one of them.**

- **Print an exit receipt before advancing.** Every phase ends with one line of the form
  `✅ Phase N (<NAME>) — <which path ran> — <evidence>`, e.g.
  `✅ Phase 8 (VERIFY) — ran pnpm test+lint+build — 142 passed, 0 failed (output above)`, or
  `✅ Phase 5 (DEEP REVIEW) — skipped: phases 3–4 surfaced no serious findings`, or
  `✅ Phase 7 (IMPLEMENT) — swarm, 9 tasks over 3 waves — all wave gates green (output above)`.
  The receipt names the branch you took (skill vs fallback, run vs skip) and points at the
  concrete evidence that the phase's stated **Exit** condition is met. No receipt → the phase
  isn't done → you may not move on. This is what makes a skipped step impossible to hide.

- **Loop-until-clean — converge, don't count.** Whenever a phase says "fix all issues", it
  means: fix every **critical/major** finding, then re-run the reviewer; repeat until a clean
  pass (no critical/major). Watch for **diminishing returns** — if a round stops reducing the
  serious findings, or the same ones keep resurfacing, you're plateauing: **stop and surface
  what's left to the human** with what you tried, rather than grinding. Convergence (or a clear
  plateau), not a fixed number of rounds, is the stop signal — and it's what keeps "clean"
  meaning clean. Minor/nice-to-have findings don't block; carry them to the handoff.

- **Check availability, then branch — and say which path you took.** Several phases read
  "IF skill X is available → use it, ELSE fallback". Actually check whether the named
  skill/command is offered in this session (it appears in the available skills/commands
  list) before assuming it. Use it if present; otherwise use the stated fallback. Either
  way, tell the human which path ran — "used `engineering:plan-hardening`" vs "plan-
  hardening unavailable, did an inline hardening pass" — so they know whether the
  rigorous tool or the substitute did the work.

- **Fan-out cost guard — more than ~20 agents, confirm first.** Two phases fan out to a
  multi-agent swarm: **5** (a reviewer per scope + a verifier per finding) and **7** (a builder
  *and* an independent reviewer per task, plus fix rounds, plus a setup and a gate per wave —
  so budget `2T + 2W` at the floor and closer to `3T + 2W` in practice). Invoking this skill
  opts you into multi-agent work in general, but a big fan-out costs real tokens: if a run
  would spawn **more than ~20 agents**, say the number and **confirm with the human before
  launching**. Both phases use the same guard and the same `Workflow` machinery — don't invent
  a second spawning convention. (The runtime also caps concurrency and total agents, but that's
  a backstop, not a substitute for the heads-up.)

- **Always set a subagent's model *and* effort.** An omitted `model` inherits the
  orchestrator's (Opus 4.8); an omitted `effort` inherits the session's (`xhigh`). Either one
  silently turns a cheap swarm expensive — and the effort trap is the easier to miss, because
  the agent still *looks* like it's running on Haiku. Every dispatch names both.

- **Confirm before anything irreversible or outward-facing.** Pushing a branch, opening a
  PR, and posting review comments leave your fingerprints on shared infrastructure. Pause
  for explicit go-ahead before those, unless the human pre-authorized hands-off completion
  ("just take it all the way", "don't stop to ask"). Local work (reading, planning,
  editing, committing locally) needs no such pause.

- **Evidence before assertions.** Never say a build passed, tests are green, or review is
  clean without showing the command and its output. "Tests pass" is a claim; the pasted
  test summary is evidence. If something failed or you skipped a step, say so plainly.

---

## Phase 0 — IDENTIFY INPUT

Determine *what* to work on and *where it lives* before anything else. Accept any of: a
**Notion** page (URL or ID), a **GitHub** Issue or Project item, a **Linear** issue, or a
**raw spec** (pasted or a file path). Detect the source from what was given — URL shape, ID
pattern, or "here's the spec" — and read it through the right channel. If the user gave
nothing to work from, **ask** which ticket or spec to drive; don't pick one.

- **IF the source's MCP is connected** → read the ticket through it.
  **ELSE** → use the CLI (`gh`) where one exists, otherwise ask the user to paste the ticket.

**Exit:** the ticket id/key, its full requirement text, and its linked context are in front
of you. → [`references/phase-0-identify-input.md`](references/phase-0-identify-input.md)

## Phase 1 — UNDERSTAND

Read the ticket **in full**, then ground it in reality: explore the affected code, folders,
and docs so your understanding is anchored in how the system actually works, not how the
ticket imagines it. Then restate the goal, scope (in *and* out), acceptance criteria,
affected components, and open questions.

**GATE:** if anything is unclear or under-specified — fuzzy acceptance criteria, an undefined
term, a decision the ticket leaves open — **stop and ask the human targeted questions.** Do
not invent requirements to fill the gap; a confidently wrong assumption here is the most
expensive error in the pipeline, because every later phase compounds it.

**Exit:** a written restatement, with open questions resolved.
→ [`references/phase-1-understand.md`](references/phase-1-understand.md)

## Phase 2 — PLAN

Turn the understanding into a concrete, ordered implementation plan: the steps, the files
each touches, the tests, and the risks.

- **IF `superpowers:writing-plans` is available** → use it; it produces a structured,
  reviewable plan.
- **ELSE** → enter plan mode and write an equivalent plan yourself.

**Exit:** a written plan exists — a plan file, or a plan-mode artifact you can hand to the
next phase. → [`references/phase-2-plan.md`](references/phase-2-plan.md)

## Phase 3 — HARDEN

Verify the plan's claims against the codebase and surface the collateral damage it doesn't
handle. Fix every critical/major finding and re-run (loop-until-clean). **"Fix" here means amend
the plan file — never the code** (Rule Zero); a real defect found in this phase is exactly the
success case, and it gets written down, not patched.

- **IF `engineering:plan-hardening` is available** → run it on the plan.
- **ELSE** → do an inline equivalent: re-read the plan adversarially against the code,
  checking each claim and each "this won't affect X" assumption, and fix what breaks.

**Exit:** a hardening pass with no critical/major findings (or a plateau reached and the
remainder surfaced). → [`references/phase-3-harden.md`](references/phase-3-harden.md)

## Phase 4 — HANDOFF REVIEW

The closing structural pass: hunt for ambiguity, missing contracts, and unstated assumptions
that would let two engineers build incompatible things. Fix all issues; re-run until clean.

- **IF `engineering:spec-handoff-review` is available** → run it on the plan.
- **ELSE** → review the plan yourself for two-implementer divergence, hidden assumptions, and
  unhandled state transitions, and resolve them.

**Exit:** a clean handoff review (or a plateau reached + surfaced).
→ [`references/phase-4-handoff-review.md`](references/phase-4-handoff-review.md)

## Phase 5 — DEEP REVIEW (conditional)

Heavier multi-agent scrutiny of the plan — a find → verify → score → reconcile fan-out where
an independent agent must confirm or refute every candidate finding before it can change the
plan. Every agent in it is **read-only** (Rule Zero): they return findings, and *you* amend the
plan. It costs real tokens, so it's gated.

**TRIGGER:** Phases 3–4 **kept surfacing serious problems** — a steady stream of critical/major
findings that says the plan is genuinely error-prone, not a one-off — **OR** the human asks for
a deep review. If neither holds, **skip to Phase 6** and say you skipped it and why.

- **IF the `Workflow` tool is available** → run the bundled script as-is, handing it the plan.
- **ELSE** → approximate it with sequential subagents, preserving the find→verify→reconcile
  discipline.

Subject to the **fan-out cost guard** (Operating rules).

**Exit:** a reconciled plan with every *confirmed* issue fixed — or an explicit, justified skip.
→ [`references/phase-5-deep-review.md`](references/phase-5-deep-review.md)

## Phase 6 — TASK GRAPH

Turn the hardened, reviewed plan into an executable structure. Split it into **atomic tasks** —
each sized so *one* builder agent can implement **and self-verify** it in a single focused session:
single responsibility, independently testable, with a write-set you can name up front. Record each
task's **inputs** (files/interfaces it depends on) and **outputs** (what downstream consumes), build
the **dependency DAG** from those, and level it into ordered **waves** (W1 = no dependencies; each
later wave's dependencies are met entirely by prior waves). Enforce the invariant the whole design
rests on: **tasks in the same wave must have disjoint file footprints** — if two would write the same
file, add a dependency edge so they serialize. Pick **each task's two models** (a builder chosen by
*difficulty*, a reviewer chosen by *criticality* — independently). Emit it all as a **written,
reviewable artifact**, the way the plan is.

**GATE:** surface the task graph, the wave plan, the model choices and the **projected agent count**
to the human **before the swarm runs**. This is the last cheap checkpoint before spawning a dozen
agents — a bad split is far cheaper to fix here than after they've written code against it. Pause for
go-ahead unless hands-off completion was pre-authorized; the **fan-out cost guard** applies regardless.

**Also verify the freeze held.** Phase 6 is the last phase inside the Rule Zero code freeze, so it is
where the freeze is checked, not merely asserted: `git status --porcelain` must show nothing but the
plan and the `.ticket-to-pr/` artifacts. Anything else is an early edit — revert it, say so, and fold
it back in as a plan amendment and a task in this graph.

**Exit:** a written task graph with a valid wave ordering (acyclic, footprint-disjoint per wave, both
models chosen per task), and a clean freeze check.
→ [`references/phase-6-task-graph.md`](references/phase-6-task-graph.md)

## Phase 7 — IMPLEMENT  *(the code freeze lifts here — and only here)*

Execute the task graph **wave by wave**, in dependency order. Each task gets its **own git worktree**
and runs its own chain — **builder → independent task reviewer → (fixer → re-review)\*** — and those
chains run **in parallel** across the wave. The reviewer returns **two verdicts, both of which must be
clean**: *spec compliance* (did it build what was asked — nothing more, nothing less?) and *code
quality*. A builder's self-review precedes that review; it never replaces it. The wave then **gates**:
integrate every worktree into the main tree, verify it still builds, commit. Only then does the next
wave start.

Worktrees are what make this safe. Disjoint write-sets stop two builders **writing** the same file, but
not one **reading** a file another is mid-rewrite in — isolation removes that, lets builders commit in
parallel, and keeps a reviewer from ever seeing a sibling's unreviewed work. Integration can't conflict,
because the footprints are disjoint.

A task that fails blocks its dependents: retry once (escalated), and if it still fails, **stop and
report** rather than pushing broken work downstream.

- **IF the `Workflow` tool is available** → run the bundled wave-swarm script (the same machinery
  Phase 5 uses), handing it the Phase-6 graph.
- **ELSE** → execute the *same graph* with the *same contracts* sequentially — one task at a time in
  wave order, still builder → reviewer → fix loop, via the **Agent** tool.

Subject to the **fan-out cost guard** and the model/effort rule (Operating rules).

**Exit:** every task built, reviewed clean on both verdicts, integrated and committed; every wave gate
green. → [`references/phase-7-implement.md`](references/phase-7-implement.md)

## Phase 8 — VERIFY

Run the project's **full build, tests, and lint** — the whole suite, not the per-wave subset —
and confirm they pass **before claiming anything**. The wave gates proved the pieces integrate;
this proves the finished change is green. Evidence before assertions (Operating rules).

- **IF `superpowers:verification-before-completion` is available** → use it.
- **ELSE** → run the project's own commands (discover them from `package.json` / `Makefile` /
  `justfile` / CI config) and read the output.

**GATE:** if anything is red, go **back to Phase 7** and fix it — do **not** proceed to a PR on
a broken build. If it can't be made green (environmental, flaky, out of scope), stop and tell
the human exactly what's failing rather than papering over it.

**Exit:** build/test/lint green, with the output shown.
→ [`references/phase-8-verify.md`](references/phase-8-verify.md)

## Phase 9 — PUSH / PR

The branch and its commits already exist — Phase 7 created the feature branch before any builder ran
(they commit), and its wave gates committed each task. So this phase tidies the history if it needs it,
**pushes**, and opens a PR whose description links the ticket, summarizes the change, and carries the
Phase-8 verification evidence.

**GATE — confirm before push and PR** unless the human pre-authorized hands-off completion. Pushing and
opening a PR are outward-facing (Operating rules); the local branch and commits were not.

**Exit:** an open PR, its URL captured for the handoff.
→ [`references/phase-9-branch-and-pr.md`](references/phase-9-branch-and-pr.md)

## Phase 10 — CODE REVIEW

Get the change reviewed, and say which reviewer ran.

- **IF the PR is already open** → use **`/review`** (it reviews the PR on GitHub).
- **ELSE / fallback** → use **`/code-review`** on the working diff.

**Exit:** a review with its findings enumerated.
→ [`references/phase-10-code-review.md`](references/phase-10-code-review.md)

## Phase 11 — FIX REVIEW FINDINGS

Address **every** finding, push the fixes, and **re-review until clean** (loop-until-clean).
Re-run Phase 8's verification after each fix round so you don't trade a review nit for a broken
build. Posting review-comment replies is outward-facing — confirm first unless pre-authorized.

**GATE:** critical/major findings block; minor/nice-to-have go to the handoff notes. A fix that
touches real behaviour goes back through **Phase 7 → 8**, not straight to a push.

**Exit:** a review pass with no critical/major findings (or a plateau reached + surfaced).
→ [`references/phase-11-fix-findings.md`](references/phase-11-fix-findings.md)

## Phase 12 — HANDOFF

Close the loop with the human: **what was built** (tied back to the acceptance criteria), **the
PR** (link + current state: checks green? review clean?), and **leftovers** (deferred decisions,
follow-up tickets worth filing, anything consciously left out of scope, any findings surfaced at
a plateau). Then hand it back.

**Exit:** the summary is delivered. Done.
→ [`references/phase-12-handoff.md`](references/phase-12-handoff.md)

---

## If a phase can't proceed

Honesty beats a clean-looking result. If a gate can't be satisfied — the spec stays ambiguous
after questions, a review loop plateaus without converging, the task graph won't come out
acyclic, a task fails twice and blocks its dependents, the build won't go green, an MCP/skill
you need is absent with no workable fallback — **stop at that phase and report** where you are,
what's blocking, and the options, rather than forcing past it. A pipeline that stops at a real
obstacle is more useful than one that produces a confidently broken PR.
