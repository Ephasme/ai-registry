# Phase 6 — IMPLEMENT  *(the code freeze lifts here — and only here)*

Hand the hardened, reviewed plan to a subagent-driven build loop: a fresh implementer per task,
an independent task reviewer (spec compliance + code quality) after each. One task in flight at a
time — no worktree-per-task swarm, no wave gates, no task graph. Simpler, and just as gated: every
task still gets built by one agent and checked by another before the next one starts.

**Stop after the last task's review comes back clean.** This phase covers task-by-task
implementation only — it does **not** run `subagent-driven-development`'s own final whole-branch
review, and it does **not** hand off to `finishing-a-development-branch`. Phases 7–11 of *this*
skill own verification, the PR, the whole-branch review, and the handoff; running the borrowed
skill's own versions of those steps too would duplicate them and hand control (merge vs. PR vs.
discard) to a menu this pipeline doesn't want making that call.

**This is where the Rule Zero code freeze lifts** — and the only place it does. Every line of
product code in this run is written here, by an implementer working one plan task at a time,
reviewed by an independent reviewer. That is the whole point of the five phases of restraint
that precede it: nothing reaches the PR that didn't come through this door. (Phases 7–10 stay
unfrozen too — verification fixes and review fixes are code — but they amend what this phase
built; they don't smuggle in what it never saw.)

## The branch

- **IF `superpowers:subagent-driven-development` is available** → use it, handing it the plan
  file from Phase 2 (as amended by Phases 3–5), but run **only its per-task loop** (read plan →
  dispatch implementer → task reviewer → fix loop → next task). Stop there.
- **ELSE** → dispatch the same loop by hand, via the **Agent** tool: one task at a time, in plan
  order, each still going implementer → reviewer → fix loop. One task in flight needs no worktree
  isolation — work in the main tree.
- **ELSE (no subagent dispatch at all)** → implement the plan yourself, task by task, running
  each task's own verification as you finish it. You are now your own implementer and reviewer,
  so say so — a self-reviewed implementation is materially weaker evidence, and the handoff
  should admit it.

Say which path ran.

## Freeze check, first

Before dispatching anything, verify Rule Zero held through Phases 0–5:

```
git status --porcelain
```

The working tree must show **nothing but the plan file**. Anything else means an agent broke
the freeze somewhere upstream ([`rule-zero-no-code.md`](rule-zero-no-code.md)) — revert it, say
what was reverted and which phase produced it, fold it back in as a plan amendment, and only
then proceed.

## Before you launch: create the feature branch

Implementers commit — so create the feature branch now, before dispatching Task 1. Never run
this phase on the default branch. Naming it `<ticket-key>-<slug>` is what lets the Linear/GitHub
integrations associate the branch with the issue later (Phase 8). Creating the branch is
content-free, so it's fine even this early (Rule Zero, [`rule-zero-no-code.md`](rule-zero-no-code.md)).

## Pre-flight gate — say the cost before you spend it

Count the plan's tasks (its `### Task N` headings). Project the agent count:

- **Floor:** `2T` — one implementer and one task reviewer per task.
- **Realistic:** `~3T` once fix rounds are counted in.

This is the **fan-out cost guard** (SKILL Operating rules): above **~20 agents**, say the number
and confirm before launching, regardless of pre-authorization. Below that, still **pause for
go-ahead** on starting Phase 6 at all unless the human pre-authorized hands-off completion — this
is the last cheap checkpoint before an agent starts writing code against the plan.

## Running it

Give `superpowers:subagent-driven-development` what it needs up front so it doesn't have to ask
mid-run:

- **The plan file path** — its single source of tasks.
- **The branch already created above** — it's already in an isolated, named workspace; it
  shouldn't need to ask `using-git-worktrees`'s consent question.
- **Global constraints**, copied verbatim from the plan's Global Constraints / risks section —
  its own process already asks for this before dispatching reviewers.
- **An explicit instruction to stop after the last task's review is clean** — don't let it walk
  into its own final whole-branch review or `finishing-a-development-branch`; this skill's
  Phases 7–11 take it from there.

Model selection for the implementer and the task reviewers is **that skill's own job** (its
Model Selection section: mechanical tasks cheap, judgment tasks standard) — don't re-pick it
yourself. The model/effort rule (SKILL Operating rules) still binds the **ELSE fallback** path
above, where you are the one dispatching each agent.

## Handling a stuck task

`subagent-driven-development` already defines how to read its implementer's status (DONE,
DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED) — follow its own doc for that. The one thing that
escalates past it: if a task is blocked because **the plan itself is wrong** (not a context gap,
not a sizing problem it can re-split), that's a finding for the orchestrator — stop, go back to
**Phase 2**, and run the change back through hardening. Re-open the todos you go back to.

## Durable progress

`subagent-driven-development` keeps its own ledger (`.superpowers/sdd/progress.md`) and commits
per task. After a compaction, trust that ledger and `git log` over your own recollection — don't
re-dispatch tasks it already marks complete.

**Exit:** every task in the plan implemented and reviewed clean (spec + quality), committed, on
the feature branch — nothing merged, pushed, or opened yet; that's Phase 8.

**Exit receipt example:**
`✅ Phase 6 (IMPLEMENT) — subagent-driven-development (per-task loop only), 7 tasks, all reviewed clean — 7 commits on abc-123-rate-limiting`
