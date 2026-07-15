# Phase 6 — IMPLEMENT  *(the code freeze lifts here — and only here)*

Hand the hardened, reviewed plan to a **per-task build loop that this skill owns outright**: a
fresh implementer subagent per task, an independent task reviewer (spec compliance + code quality)
after each, a fix loop until that task's review is clean, then the next task. One task in flight at
a time — no worktree-per-task swarm, no wave gates, no task graph. Every task is built by one agent
and checked by another before the next one starts.

**Why subagents:** each task goes to an agent with isolated context that you construct exactly —
the task brief, the interfaces it touches, the global constraints, nothing else. It never inherits
your session history, which keeps it focused and preserves your context for coordination.

**Stop after the last task's review comes back clean.** This phase covers task-by-task
implementation only. Do **not** run a broad whole-branch review here, and do **not** offer a
merge/PR/discard menu — Phases 7–11 of *this* skill own verification, the PR, the whole-branch
review, and the handoff. Adding those here duplicates them and hands the integration decision to
the wrong place.

**This is where the Rule Zero code freeze lifts** — and the only place it does. Every line of
product code in this run is written here, by an implementer working one plan task at a time,
reviewed by an independent reviewer. That is the whole point of the phases of restraint that
precede it: nothing reaches the PR that didn't come through this door. (Phases 7–10 stay unfrozen
too — verification fixes and review fixes are code — but they amend what this phase built; they
don't smuggle in what it never saw.)

## The procedure (owned — dispatched via the Agent tool)

1. **Read the plan once.** Note the scene-setting context and the **Global Constraints** section
   (you'll hand those to every reviewer). Create a todo per task.
2. **Pre-flight plan scan.** Before dispatching Task 1, scan the plan once for conflicts: tasks that
   contradict each other or the Global Constraints, or anything the plan mandates that the review
   rubric treats as a defect (a test that asserts nothing, verbatim duplication of a logic block).
   Present everything you find as **one batched question** — each finding beside the plan text that
   mandates it, asking which governs — before execution begins, not one interrupt per discovery
   mid-plan. If the scan is clean, proceed without comment.
3. **Per task, in plan order,** run the loop below. One task in flight; never dispatch two
   implementers in parallel (they conflict).
4. **Last-resort fallback (no subagent dispatch available at all):** implement the plan yourself,
   task by task, running each task's verification as you finish it — and **say so**. You are then
   your own implementer and reviewer, which is materially weaker evidence, and the handoff should
   admit it.

## Freeze check, first

Before dispatching anything, verify Rule Zero held through Phases 0–5:

```
git status --porcelain
```

The working tree must show **nothing but the plan file**. Anything else means an agent broke the
freeze upstream ([`rule-zero-no-code.md`](rule-zero-no-code.md)) — revert it, say what was reverted
and which phase produced it, fold it back in as a plan amendment, and only then proceed.

## Create the feature branch

Implementers commit — so create the feature branch now, before dispatching Task 1. Never run this
phase on the default branch. Name it `<ticket-key>-<slug>` so the Linear/GitHub integrations can
associate the branch with the issue later (Phase 8). Creating a branch is content-free, so it's
fine this early (Rule Zero).

## Pre-flight gate — say the cost before you spend it

Count the plan's tasks (its `### Task N` headings). Project the agent count:

- **Floor:** `2T` — one implementer and one task reviewer per task.
- **Realistic:** `~3T` once fix rounds are counted in.

This is the **fan-out cost guard** (SKILL Operating rules): above **~20 agents**, say the number and
confirm before launching, regardless of pre-authorization. Below that, still **pause for go-ahead**
on starting Phase 6 at all unless the human pre-authorized hands-off completion — this is the last
cheap checkpoint before an agent starts writing code against the plan.

## The per-task loop

For each task, everything moves as **files**, not pasted text — anything you paste into a dispatch,
or a subagent prints back, stays resident in your context for the rest of the session. The bundled
scripts live at `${CLAUDE_PLUGIN_ROOT}/skills/ticket-to-pr/scripts/`.

1. **Record BASE.** `git rev-parse HEAD` — the commit before this task. You need it for the review
   package; never use `HEAD~1`, which silently drops all but the last commit of a multi-commit task.
2. **Extract the brief.** Run `scripts/task-brief PLAN_FILE N` — it writes the task's full text to a
   file and prints the path. The brief is the single source of requirements; exact values (numbers,
   magic strings, signatures, test cases) live only there.
3. **Dispatch the implementer** using [`prompts/implementer.md`](prompts/implementer.md). Your
   dispatch carries: one line on where this task fits; the brief path ("read this first — it is your
   requirements, with the exact values to use verbatim"); interfaces/decisions from earlier tasks
   the brief can't know; your resolution of any ambiguity you saw in the brief; and the report-file
   path. Name the report file after the brief (`…/task-N-brief.md` → `…/task-N-report.md`). Do **not**
   paste prior-task summaries — a fresh subagent needs its task, its interfaces, and the constraints,
   nothing else.
4. **Handle the implementer's status** (see below) until it reports DONE.
5. **Build the review package.** `scripts/review-package BASE HEAD` — writes the commit list, stat
   summary, and full diff to one file and prints the path. It never enters your context.
6. **Dispatch the task reviewer** using [`prompts/task-reviewer.md`](prompts/task-reviewer.md),
   handing it three paths — the same brief, the implementer's report, and the review package — plus
   the Global Constraints that bind this task, copied verbatim.
7. **Fix loop.** Dispatch a fix subagent for **Critical and Important** findings (one fixer with the
   complete findings list, not one per finding). The fix subagent carries the implementer contract:
   re-run the tests covering its change and append results to the report file. Then re-review (a
   fresh `review-package` for the new range). Repeat until the reviewer returns spec ✅ and quality
   Approved. Record Minor findings in the ledger for the Phase 9 whole-branch review to triage.
8. **Mark the task complete** in the todo list and append one line to the ledger (see Durable
   progress). Then move to the next task.

## Handling implementer status

Implementers report one of four statuses:

- **DONE:** proceed to the review package and task reviewer.
- **DONE_WITH_CONCERNS:** read the concerns first. If they're about correctness or scope, address
  them before review; if they're observations ("this file is getting large"), note them and proceed.
- **NEEDS_CONTEXT:** provide the missing information and re-dispatch.
- **BLOCKED:** assess the blocker — context problem → provide more and re-dispatch same model;
  needs more reasoning → re-dispatch a more capable model; task too large → split it; **the plan
  itself is wrong** → escalate (see Handling a stuck task). Never force the same model to retry
  unchanged, and never ignore an escalation.

**Reviewer ⚠️ items.** The task reviewer may report "⚠️ Cannot verify from diff" — requirements that
live in unchanged code or span tasks. These don't block, but resolve each yourself before marking
the task complete (you hold the cross-task context the reviewer lacks). A confirmed gap is a failed
spec review — send it back to the implementer and re-review.

## Model selection

Use the least powerful model that can handle each role — **always set it explicitly** (an omitted
model inherits the session's, usually the most expensive). Turn count beats token price: the
cheapest models often take 2–3× the turns on multi-step work.

- **Transcription implementer** (the plan text contains the complete code to write; single-file
  mechanical fix): cheapest tier.
- **Prose-description implementer / reviewer:** mid-tier as the floor.
- **Integration/judgment implementer** (multi-file coordination, debugging): standard model.
- **Reviewer:** scale to the diff — a small mechanical diff doesn't need the top model; a subtle
  concurrency change does.

The model/effort operating rule binds every dispatch here — this loop is the one you dispatch.

## Constructing reviewer prompts — the discipline

Per-task reviews are task-scoped gates; the broad review happens once, at Phase 9. When you fill
the reviewer template:

- **Copy the Global Constraints verbatim** from the plan into the reviewer's constraints block —
  exact values, formats, and stated relationships between components ("same layout as X"). That
  block is the reviewer's attention lens; the template already carries the process rules.
- **Never pre-judge.** Don't tell a reviewer what not to flag, don't pre-rate a finding's severity
  ("at most Minor"), don't ask it to skip an issue. If a prompt you're writing contains "do not
  flag," "the plan chose," or "treat as Minor" — stop; you're sparing yourself a review loop. Let
  the reviewer raise it and adjudicate in the loop.
- **Don't ask it to re-run tests** the implementer already ran on the same code — the report carries
  that evidence. Don't add open-ended directives ("check all uses") without a concrete reason.
- **A plan-mandated finding is the human's call.** If a finding conflicts with what the plan's text
  requires, present both and ask which governs — don't dismiss it, and don't dispatch a fix that
  contradicts the plan without asking.

## File handoffs

- **Task brief** (`scripts/task-brief`) — the implementer's and reviewer's single source of
  requirements.
- **Report file** — the implementer writes its full report there and returns only status, commits, a
  one-line test summary, and concerns. Fix dispatches append their fix report (with test results) to
  the same file.
- **Review package** (`scripts/review-package`) — the reviewer's view of the diff, in one Read.

## Durable progress

Conversation memory does not survive compaction; controllers that lost their place have
re-dispatched entire completed task sequences — the single most expensive failure. Keep a ledger
file, not only todos.

- At phase start, check for one: `cat "$(git rev-parse --show-toplevel)/.ttpr/build/progress.md"`.
  Tasks marked complete there are DONE — don't re-dispatch; resume at the first not marked complete.
  (`scripts/build-workspace` creates `.ttpr/build/` as git-ignored scratch.)
- When a task's review comes back clean, append one line:
  `Task N: complete (commits <base7>..<head7>, review clean)`.
- The ledger is your recovery map: the commits it names exist in git even when your context no
  longer remembers creating them. After compaction, trust the ledger and `git log` over recollection.

## Handling a stuck task

Most stuck states resolve via the status handling above (more context, a stronger model, a smaller
split). The one thing that escalates past this loop: a task blocked because **the plan itself is
wrong** — not a context gap, not a sizing problem. That's a finding for the orchestrator — stop, go
back to **Phase 2**, run the change through hardening, and re-open the todos you went back to.

**Exit:** every task in the plan implemented and reviewed clean (spec + quality), committed, on the
feature branch — nothing merged, pushed, or opened yet; that's Phase 8.

**Exit receipt example:**
`✅ Phase 6 (IMPLEMENT) — owned per-task loop, 7 tasks, all reviewed clean — 7 commits on abc-123-rate-limiting`
