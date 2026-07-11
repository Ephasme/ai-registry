# Phase 7 — IMPLEMENT (wave by wave, builder + reviewer per task)

Execute the Phase-6 task graph. Iterate the waves in dependency order. Within a wave, every task
gets its **own isolated git worktree** and runs its own chain — **builder → task reviewer → (fixer
→ re-review)\*** — and those chains run **in parallel** with each other. Finish the wave — every
task reviewed clean, then integrated, verified and committed — before the next wave starts.

The script is **pre-written and bundled** at `scripts/implement-waves.workflow.mjs`, using the same
`Workflow` machinery Phase 5 uses. Run the file; don't reassemble the fan-out inline.

```
        ┌─ T2: worktree → builder → reviewer → [fixer → re-review]* ─┐
W2 ─────┼─ T3: worktree → builder → reviewer → [fixer → re-review]* ─┼── gate: integrate,
        └─ T4: worktree → builder → reviewer → [fixer → re-review]* ─┘   verify, commit ──▶ W3
```

## The branch

- **IF the `Workflow` tool is available** → run the bundled wave-swarm script.
- **ELSE** → execute the **same task graph** sequentially: one task at a time, in wave order, each
  still going builder → reviewer → fix-loop via the **Agent** tool with the same contracts
  ([`phase-7-builder-prompt.md`](phase-7-builder-prompt.md),
  [`phase-7-reviewer-prompt.md`](phase-7-reviewer-prompt.md)). You lose the parallelism, not the
  discipline — and with one task in flight, worktrees are unnecessary: work in the main tree.
- **ELSE (no subagent dispatch at all)** → implement the graph yourself, task by task in wave order,
  running each task's `verify` as you finish it and the gate command at each wave boundary. Say so —
  a self-reviewed implementation is materially weaker evidence, and the handoff should admit it.

Say which path ran.

## Running the swarm

```
Workflow({
  scriptPath: "${CLAUDE_PLUGIN_ROOT}/skills/ticket-to-pr/scripts/implement-waves.workflow.mjs",
  args: {
    graph: { tasks: [ /* the Phase-6 tasks, verbatim */ ], waves: [["T1"], ["T2","T3","T4"], ["T5"]] },
    gateCommand:   "pnpm typecheck && pnpm build",
    scriptsDir:    "<resolved CLAUDE_PLUGIN_ROOT>/skills/ticket-to-pr/scripts",
    worktreeSetup: "ln -s ../../../node_modules node_modules",
    constraints:   "<binding requirements, copied verbatim from the plan>",
    planPath:      "docs/plans/abc-123-rate-limiting.md"
  }
})
```

Pass `graph` as a real JSON value, not a stringified one. Resolve `${CLAUDE_PLUGIN_ROOT}` yourself
before passing `scriptsDir` — the script can't expand it.

**Before you launch: make sure you're on a feature branch.** Builders commit. Never run the swarm on
the default branch — create the branch first (Phase 9 pushes it; creating it is local and needs no
gate). This is the one thing that is genuinely hard to undo after nine agents have committed.

## Isolation — the resolved rule

**One git worktree per task, detached at the wave's base commit.** Created serially by a setup agent
(concurrent `git worktree add` can race), torn down by the gate.

Phase 6's disjoint write-sets stop two builders from **writing** the same file. They do *not* stop
task B from **reading** a file task A is midway through rewriting — and that is the failure that
actually bites:

- **Read contamination.** In one shared tree, B's own verify command can fail — or worse, *pass* —
  against a torn state that has nothing to do with B. It looks like flakiness, and it isn't.
- **Review contamination.** B's reviewer, inspecting a named risk outside its diff, would see A's
  unreviewed in-progress code and attribute it to B.

Isolation removes both: each builder sees the wave's base commit plus its own work, and nothing else.

It also **buys back committing.** A worktree has its own index and HEAD, so builders commit freely in
parallel — nothing is shared but the content-addressed object database, which is concurrency-safe.
That in turn gives every reviewer a real `BASE..HEAD` commit range instead of a reconstructed diff.
(In a *shared* tree, builders must not commit at all: git's index is the one resource every task
would write, and concurrent commits race on `index.lock` and interleave.)

**Integration stays conflict-free** — and this is where the disjointness invariant earns its keep a
second time. Because no two tasks in a wave touch the same file, cherry-picking their worktrees back
into the main tree **cannot conflict**. The invariant has simply changed job: it used to make shared
editing safe; now it makes the N-way merge trivial. If a cherry-pick *does* conflict, that is a
**Phase-6 footprint bug** — the gate aborts and reports it rather than resolving it.

**The cost, stated plainly:** a fresh worktree has none of the project's **gitignored build
dependencies** (`node_modules`, `.venv`, `target/`), so tests cannot run in it until they're
provisioned. Pass `worktreeSetup` with the cheapest correct provisioning for the project — usually
symlinking the main tree's `node_modules`; an install per worktree is the fallback.

**There is no "parallel but unisolated" mode, deliberately.** If a project genuinely can't afford a
worktree per task (a heavy native build, no shared package store), then it can't afford to
parallelize either — without isolation, concurrent builders race on the one git index and read each
other's half-written files, which is the exact failure the worktrees exist to prevent. The honest
fallback is the **sequential path** below: one builder at a time in the main tree, which needs no
isolation because nothing runs concurrently. You lose the parallelism and keep every guarantee. A
shared-tree swarm would lose the guarantees and keep the parallelism — the wrong half.

## The per-task chain

**Builder** ([contract](phase-7-builder-prompt.md)) — a fresh agent per task, given its brief, the
contracts it reads and provides, and its write-set. It writes the test first, implements, runs its
own `verify`, self-reviews, commits in its worktree, and writes a report. It gets **its task and
nothing else**: not the other tasks, not the session history, not a running summary of earlier waves.

**Task reviewer** ([contract](phase-7-reviewer-prompt.md)) — an **independent** agent, on an
**independently chosen model**, that reads the brief, the builder's report, and the diff, and returns
**two verdicts**: *spec compliance* (did it build what was asked — nothing more, nothing less?) and
*code quality* (is what it built any good?). It is told not to trust the report, because a builder's
self-review is the builder grading its own work. **Both verdicts must be clean** for the task to
count as done. The builder's self-review does not substitute for this — it precedes it.

**Fixer** — if the reviewer returns Critical/Important findings, **one** fixer gets the **complete
findings list** (never one fixer per finding — each would rebuild context and re-run suites, and the
fix wave would cost more than the tasks did). It fixes, re-runs the covering tests, appends the
evidence to the report, and the reviewer runs again. **Two fix rounds max**; still not converged →
the task fails, and the halt policy takes over.

Minor findings never block. They're collected across the run and handed to **Phase 10**, which
triages which must be fixed before merge. A roll-up nobody reads is a silent discard.

## Model selection — two independent axes

The builder's model is chosen by **how hard the task is to write**; the reviewer's by **how bad it
would be if it were wrong**. These are genuinely different questions, so they get different answers —
a tiny, trivial diff to the auth guard deserves a cheap builder and an expensive reviewer.

The full matrix, the tiers, and worked examples live in
[`phase-6-task-graph.md`](phase-6-task-graph.md#step-6--model-selection--two-independent-axes) — the graph
carries `builderModel` / `builderEffort` / `reviewerModel` / `reviewerEffort` per task, decided there
so the human can see them at the gate.

- **Never omit the model — or the effort.** An omitted `model` inherits the orchestrator's (Opus
  4.8); an omitted `effort` inherits the session's (`xhigh`). Either silently makes a cheap swarm
  expensive, and the effort trap is the easier to miss: the agent still *looks* like it's on Haiku.
- **Reviewers have a mid-tier floor** — never Haiku. Turn count beats token price: a model that
  misses findings costs a review round, which costs more than the model you saved on.
- **Retries escalate.** A failed builder is re-dispatched one tier up. Re-running the same model on
  the same failure, unchanged, just buys the same failure twice.
- **The gate and setup agents are mechanical** — Sonnet, low/medium effort. They run commands and
  report.
- **Judgment stays with the orchestrator** (Opus 4.8, this session): the graph, the halt decisions,
  ⚠️ items, integration triage, plan-mandated findings. The swarm writes code; you decide what it
  means.

## Builder status handling

- **DONE** → proceed to review.
- **DONE_WITH_CONCERNS** → read the concerns *before* reviewing. If they bear on correctness or
  scope, address them. If they're observations ("this file is getting large"), note them and proceed.
- **NEEDS_CONTEXT** → the dispatch didn't carry something the builder needed. It cannot ask and wait
  (there's no interactive channel inside a swarm), so it returns instead. **Supply the context and
  re-dispatch.** Never let a builder guess.
- **NEEDS_OUT_OF_SCOPE_WRITE** → the builder would have to edit outside its write-set. This is a
  **graph bug**, not a flaky agent: retrying cannot help, only re-graphing can. Halt, go back to
  Phase 6. Treat this as valuable — it's the invariant catching a bad split before it corrupts a wave.
- **BLOCKED** → assess. Missing context → supply it. Needs more reasoning → re-dispatch one tier up.
  Too large → it isn't atomic; back to Phase 6 to split it. The plan is wrong → back to Phase 2.
  **Never force the same model to retry unchanged** — if it says it's stuck, something has to change.

## Failure handling — the resolved rule

1. **Retry once, escalated,** with the failure fed back to a fresh agent. A transient stumble is
   worth a second shot; a second failure is not bad luck — it says the **task or the plan is wrong**,
   and a third agent fails the same way.
2. **On a second failure — halt and report.** No further wave starts. A failed task **blocks its
   dependents** by construction, and running the rest of the graph around it produces exactly what
   this pipeline exists to prevent: work built on a foundation that isn't there, which typechecks,
   looks done, and is wrong. Sibling tasks already in flight in the same wave are allowed to finish —
   they're independent, and isolated, so their work stands.
3. **A red wave gate is a wave failure.** Attributable to one task → that task's failure (rule 1).
   A break between tasks that each passed *in isolation* — the classic "both were right, together
   they're wrong" — is a **contract bug**, i.e. a Phase-6 or Phase-2 bug. Small, obvious seams you
   may fix inline and re-run the gate; anything else, halt and report.
4. **A cherry-pick conflict is a footprint bug.** It means two same-wave tasks touched one file and
   Phase 6's disjointness check was wrong. Halt; fix the graph.
5. **The report** names: the failed task, the evidence (real error output), what completed and is
   committed, which downstream tasks are blocked, where the worktrees are (they're left in place as
   evidence), and the options.
6. **Where to go back to.** A failed *task* (bad brief, wrong write-set, not actually atomic) → back
   to **Phase 6**; a failed *contract* (the plan was wrong about how the pieces fit) → back to
   **Phase 2**, and through hardening again. Re-open the todos you go back to.

**Never push a failure downstream.** Not with a stub, not with a `TODO`, not with a swallowed error.

## Durable progress

Conversation memory doesn't survive compaction; a controller that loses its place can re-dispatch
work it already completed. So the wave gate appends to a **ledger** — `.ticket-to-pr/progress.md` —
one line per task: `W2 T3: complete (commit a1b2c3d, review clean)`.

- **Check it before launching.** Tasks it marks complete are done — don't re-dispatch them; resume at
  the first task that isn't.
- **After a compaction, trust the ledger and `git log` over your own recollection.** The commits it
  names exist in git even when your context no longer remembers creating them.
- The `Workflow` tool's `resumeFromRunId` is the cheap resume (cached agent results, same session);
  the ledger is the durable one (survives anything).

## Scope discipline (every path)

Follow the **existing repo conventions** — match the surrounding code's style, structure, and idioms
— and keep the diff **scoped to the ticket**. No drive-by refactors, no unrelated cleanups: they make
review harder, dilute the PR, and are the easiest way for an agent to drift outside its write-set.
This is in the builder contract; keep it there.

**Exit:** every task in the graph is built, reviewed clean on both verdicts, integrated, and
committed; every wave gate green.

**Exit receipt examples:**
`✅ Phase 7 (IMPLEMENT) — swarm via implement-waves.workflow.mjs — 9 tasks / 3 waves, worktree-isolated; 9 builders + 11 reviews (2 fix rounds on T4, T7), all 3 gates green — 9 commits on abc-123-rate-limiting`
`✅ Phase 7 (IMPLEMENT) — Workflow unavailable → sequential fallback, same graph & contracts via Agent — 9 tasks in wave order, gate green at each boundary`
