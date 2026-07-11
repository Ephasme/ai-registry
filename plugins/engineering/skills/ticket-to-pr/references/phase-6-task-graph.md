# Phase 6 — TASK GRAPH

The plan is now true (Phase 3), unambiguous (Phase 4), and — if it needed it — deeply reviewed
(Phase 5). It is still a *narrative*: a sequence written for one reader working top to bottom.
Phase 7 doesn't have one reader; it has a swarm. This phase converts the narrative into the
structure a swarm can execute: **atomic tasks → a dependency DAG → ordered waves.**

Do this as its own deliberate step, not in your head on the way to implementing. The graph is a
written artifact, like the plan, because it is the last thing a human can cheaply correct. A bad
split costs one conversation to fix here; after the swarm has run, it costs a dozen agents' worth
of wrong code.

---

## Step 1 — Split into atomic tasks

An **atomic task** is one a builder agent can implement **and self-verify** in a single focused
session. Concretely, a task is atomic when all five hold:

1. **Single responsibility.** One coherent change, describable in one sentence with no "and then
   also". If the sentence needs an "and", it's two tasks — unless the two halves are inseparable
   (you cannot verify one without the other), in which case it's one task and the sentence needs a
   better verb.
2. **Independently testable.** It has its own verification — a test file, a test command, a
   typecheck, a runnable check. **If you cannot name the command that proves this task done, it is
   not atomic yet.** This is the sharpest of the five tests; apply it first.
3. **Nameable write-set.** You can list, *up front*, the files it will create or modify. An agent
   that has to go discover which files it needs is an agent whose footprint you cannot schedule.
4. **No mid-flight negotiation.** It never needs to agree an interface with a sibling task while
   both are running. Every contract it consumes is already defined — by the plan, or by an upstream
   task it depends on. (Phase 4 pinned these contracts; this is where that work pays off.)
5. **Fits one session.** Roughly: a handful of files, one layer, one contract. If it spans two
   layers *and* invents the contract between them, split it at the contract.

### Sizing heuristics

- **Split at contracts, not at files.** "Define the `RateLimitPolicy` type + its store interface" is
  one task; "implement the Redis store" and "implement the in-memory store" are two more that both
  depend on it. That shape — one small **contract task** upstream, several independent implementers
  downstream — is the shape that parallelizes.
- **Tests travel with the code they test.** A task writes its own tests. Don't make "write the tests"
  a separate downstream task; that breaks self-verification (test 2) and creates a task that can only
  fail late.
- **Don't over-split.** A task too small to verify on its own (a one-line export, a single type alias)
  isn't a task — it's part of one. Over-splitting inflates the agent count, buys nothing, and
  multiplies the coordination surface.
- **Don't force parallelism.** A genuinely sequential plan yields a graph of single-task waves. That
  is a correct graph; say so and run it. Inventing false independence to widen a wave is how you get
  two tasks fighting over one file.

## Step 2 — Record inputs, outputs, and models

For every task, write down:

| Field | Meaning |
|---|---|
| `id` | `T1`, `T2`, … — stable, referenced by edges and waves |
| `title` | the one-sentence responsibility |
| `briefPath` | the task's brief file (see below) — the builder's and reviewer's single source of requirements |
| `reads` | files / interfaces / symbols it depends on (its **inputs**) |
| `writes` | files it creates or modifies (its **outputs**, as a footprint) — **the only files it may touch** |
| `provides` | what downstream consumes: an exported symbol, a type, an endpoint, a table, an event (its **outputs**, as a contract) |
| `verify` | the command that proves this task done — the builder's self-verification |
| `builderModel` / `builderEffort` | chosen by **difficulty** (see the matrix below) |
| `reviewerModel` / `reviewerEffort` | chosen by **criticality** (see the matrix below) |

`writes` and `provides` are both "outputs" but they do different jobs: `writes` drives the
**collision check** (Step 5), `provides` drives the **dependency edges** (Step 3). Keep both.

### Write one brief file per task

A builder must never be handed the whole plan, and must never be handed the session's history. It
gets **its task, the interfaces it touches, and the constraints that bind it — nothing else.** So
extract each task's full requirements into its own file, `.ticket-to-pr/<id>-brief.md`, and put the
path in `briefPath`. The **same file** goes to the builder and to its reviewer — which is what lets
the reviewer judge spec compliance against exactly what the builder was asked for, with no drift.

Exact values — names, signatures, numbers, formats, test cases — live **in the brief**, verbatim,
not in the dispatch prose around it.

## Step 3 — Build the dependency DAG

Draw an edge **A → B** ("B depends on A") when either is true:

- **Contract dependency.** B `reads` something A `provides`. A real dependency: B cannot be written
  correctly until A's contract exists.
- **Footprint dependency.** A and B both `write` the same file. Not a logical dependency — a
  serialization edge, added purely so the two never run in the same wave. Direct it along the natural
  build order (the one whose output the other extends goes first).

**Cycles are a bug in the split, not a fact about the work.** If A depends on B and B on A, one of two
things is true and both are fixable:

- They share a contract neither owns → **extract a contract task** upstream of both (define the
  types/interface in its own task; both then depend on it, and the cycle is gone). This is the standard
  cycle-breaker and it is nearly always the right one.
- They are genuinely inseparable → **merge them** into one task.

Never "resolve" a cycle by dropping an edge. A dropped edge is a task that runs before its dependency
exists, which is a task that invents a stub — and a stub that typechecks is the worst possible failure
mode, because Phase 8 will pass.

## Step 4 — Level into waves

Standard topological leveling (Kahn):

- **W1** = every task with no dependencies.
- **W(n)** = every task whose dependencies are *all* satisfied by waves W1…W(n−1).
- Repeat until every task is placed. If tasks remain but none can be placed, you have a cycle — go back
  to Step 3.

A task goes in the **earliest** wave whose predecessors are all satisfied. Waves are barriers: W(n) does
not start until every task in W(n−1) is reviewed clean, integrated, and gate-green (Phase 7).

## Step 5 — The footprint check (mandatory, and load-bearing)

**Invariant: within a wave, no two tasks may write the same file.**

Verify it explicitly — for each wave, intersect the `writes` sets pairwise:

- **Any overlap → add a footprint edge (Step 3) and re-level (Step 4).** The two tasks land in different
  waves and serialize. Repeat until every wave is clean.
- State in the artifact that you ran this check. "No overlaps in any wave" is a claim you must have
  actually verified, not assumed.

**What the invariant buys.** In Phase 7 each task builds in its own git worktree, so a same-file collision
would not corrupt anything *during* the wave — the tasks can't see each other. The invariant matters at
the **wave boundary**, where the gate cherry-picks every worktree back into the main tree: because no two
tasks in the wave touched the same file, that N-way integration **cannot conflict**. Disjointness is what
makes merging the swarm's work trivial instead of a merge-resolution problem. If a cherry-pick *does*
conflict, that is this check having been wrong, and Phase 7 halts on it.

### Hub files — the usual collision source

Some files attract edits from every task: barrel/index exports, DI containers or service registries, route
tables, `schema.prisma` / migration indexes, i18n catalogs, generated manifests, lockfiles. Naively, every
task writes them, so nothing parallelizes. Pick one per hub file:

- **Owner task** — one task owns *all* edits to the hub file, and everything that must appear there depends
  on it (usual direction: the hub task sits in a later wave and wires up what the earlier waves built).
  Prefer this: the hub file stays coherent, written by one agent that sees all of it at once.
- **Fold in** — if exactly one task in the run needs the hub edit, let that task own it, and give any other
  toucher a dependency edge.

Decide deliberately per hub file, and write the decision into the artifact — an unnoticed hub file is the
single most likely way a wave breaks.

### The worktree decision Phase 6 owes Phase 7

Each task builds in its own git worktree — the reasoning is in
[`phase-7-implement.md`](phase-7-implement.md#isolation--the-resolved-rule). What Phase 6 must *decide* is
**`worktreeSetup`**: how to provision a fresh one. It arrives with none of the project's gitignored build
dependencies (`node_modules`, `.venv`, `target/`), so it cannot run a test until it has them — usually a
symlink to the main tree's `node_modules`. Record that command in the artifact.

If the project can't be provisioned cheaply, say so in the artifact and mark the run **sequential**: one
builder at a time in the main tree, which needs no isolation because nothing runs concurrently. Parallel-
but-unisolated is not on the menu — it is the one combination that drops the guarantees and keeps the risk.

## Step 6 — Model selection — two independent axes

Every task gets **two** agents: a builder and an independent reviewer. Their models are chosen by
**different questions**, so they get **different answers**:

- **Builder ← difficulty.** *How hard is this to write?*
- **Reviewer ← criticality.** *How bad would it be if it were wrong?*

| | **Builder** (difficulty) | **Reviewer** (criticality / blast radius) |
|---|---|---|
| **Low** | brief contains the shape; 1–2 files; mechanical → **Haiku**, effort `low` | local, easily-reverted, low blast radius → **Sonnet**, effort `medium` |
| **Medium** | multi-file, real integration, prose spec → **Sonnet**, effort `medium`/`high` | normal product code → **Sonnet**, effort `high` |
| **High** | design judgment, subtle algorithm, broad codebase understanding → **Opus**, effort `high`/`xhigh` | auth/security, data integrity, migrations, money, concurrency, a public contract many tasks depend on → **Opus**, effort `xhigh` |

They are chosen **independently** — that's the point. Worked examples:

- *Add the `X-RateLimit-*` response headers* — trivial to write, but it's the public contract three other
  tasks read. → **Haiku builder, Opus reviewer.**
- *Refactor the in-memory store's eviction loop* — fiddly to get right, but it's internal and a bug shows
  up instantly in its own tests. → **Opus builder, Sonnet reviewer.**
- *Wire the limiter into the DI container* — mechanical, low risk. → **Haiku builder, Sonnet reviewer.**
- *The token-bucket algorithm itself* — hard to write, disastrous if wrong. → **Opus both.**

**Reviewers have a mid-tier floor — never Haiku.** Turn count beats token price: a reviewer that misses a
finding costs a whole extra review round, which costs more than the model you saved on.

Every task carries **four** values into the graph — `builderModel`, `builderEffort`, `reviewerModel`,
`reviewerEffort`. Leaving any of them blank is what the model/effort rule (SKILL Operating rules) exists to
prevent; the graph is where you fill them in, so fill in all four.

## Step 7 — Pre-flight conflict scan and freeze check

### The freeze check (Rule Zero's enforcement point)

Phase 6 is the last phase inside the code freeze, so it is where the freeze gets **verified**, not
just asserted. Run:

```
git status --porcelain
```

The working tree must contain **nothing but** the plan file and the `.ticket-to-pr/` artifacts
(the graph, the briefs, the ledger). Anything else — a source file, a test, a config, a lockfile —
means an agent broke Rule Zero ([`rule-zero-no-code.md`](rule-zero-no-code.md)) somewhere in
Phases 0–6.

If it did: **revert those files** (`git restore <file>` / `git checkout -- <file>`), say plainly
what was reverted and which phase produced it, and fold the change back in where it belongs — as a
plan amendment, and then as a task in this graph. Do **not** let it ride into Phase 7's base
commit. An edit that predates the task graph is owned by no task, reviewed by no reviewer, and
covered by no wave gate; it would enter the PR wearing the pipeline's badge without ever having
passed through it.

State the result of this check in the artifact and in the receipt. "The tree is clean" is a claim
you must have actually run the command to make.

### The conflict scan

Before you hand the graph over, scan the plan once for things that will make the swarm fight itself:

- Tasks that **contradict each other**, or contradict the plan's own constraints.
- Anything the plan **explicitly mandates that a reviewer will call a defect** — a test that asserts
  nothing, a verbatim-duplicated logic block, a swallowed error. The reviewer *will* flag it (correctly),
  the fixer *will* try to change it, and the plan says not to. That's an infinite loop with a token bill.

Batch everything you find into the Phase-6 gate question — each finding beside the plan text that mandates
it, asking **which governs** — rather than discovering it mid-swarm, one interrupt at a time. If the scan
is clean, say nothing and proceed.

## Step 8 — Write the artifact

The graph is a **file**, next to the plan: `<plan-path-without-.md>.task-graph.md`. Phase 7 reads it; the
human reviews it at the gate.

```markdown
# Task graph — <ticket key> <title>
Plan: <path to the plan file>
Gate command: <the build/typecheck Phase 7 runs after each wave>
Worktree setup: <how to provision a fresh worktree, e.g. `ln -s ../../../node_modules node_modules`>

## Tasks

### T1 — <one-sentence responsibility>
- **brief:** `.ticket-to-pr/T1-brief.md`
- **reads:** <files/symbols> — **provides:** `RateLimitPolicy`, `PolicyStore`
- **writes:** `src/limits/policy.ts`, `src/limits/policy.test.ts`
- **verify:** `pnpm vitest run src/limits/policy.test.ts`
- **deps:** —
- **builder:** opus / xhigh — *the token-bucket maths is the subtle part*
- **reviewer:** opus / xhigh — *every downstream task reads this contract*

### T2 — …

## Dependency DAG
T1 → T2   (T2 reads RateLimitPolicy, provided by T1)
T1 → T3   (T3 reads RateLimitPolicy)
T2 → T5   (footprint: both write src/limits/index.ts — serialized)

## Waves
| Wave | Tasks | Rationale |
|---|---|---|
| W1 | T1 | contract task — everything downstream reads the policy type |
| W2 | T2, T3, T4 | independent stores + middleware; disjoint writes |
| W3 | T5 | hub task: wires the stores into the DI container & barrel export |

## Footprint check
Pairwise `writes` intersection is empty within W1, W2 and W3. ✅
Hub files: `src/limits/index.ts` and `src/container.ts` are owned solely by T5 (W3).

## Freeze check (Rule Zero)
`git status --porcelain` → only the plan file and `.ticket-to-pr/` artifacts. No code written
in Phases 0–6. ✅

## Pre-flight scan
<conflicts found, or "clean">
```

## GATE — show the graph before the swarm

**Surface the task graph and the wave plan to the human before Phase 7 spawns anything.** State the tasks,
the waves and their widths, the hub-file decisions, the model choices, the pre-flight findings, the
**freeze-check result** — and the **projected agent count**.

Count it honestly. Per wave: **1 setup + 1 gate**. Per task: **1 builder + 1 reviewer** as the floor, plus
**2 more per fix round** (a fixer and a re-review, up to 2 rounds) and possibly a build retry.

> floor `2T + 2W` · realistic ≈ `2.5–3T + 2W` · worst case ≈ `7T + 2W`

A 9-task / 3-wave graph is therefore ~24 agents at the floor — which already trips the **fan-out cost
guard** (SKILL Operating rules). That's not a flaw in the arithmetic; it's the real price of a
builder+reviewer swarm, and the guard exists so the human sees it before it's spent, not after.

This is **the last cheap checkpoint**. Everything before it is words; everything after it is a dozen agents
writing code. A human who spots "T3 and T4 are going to fight over the router" in this table saves the whole
run.

- **Pause for go-ahead** unless the human pre-authorized hands-off completion.
- **The cost guard applies regardless**: above **~20 agents**, say the number and confirm before launching.
  Hands-off pre-authorization covers *not stopping to ask*, not *spending 40 agents without warning*.

**Exit:** a written task graph with a valid wave ordering — acyclic, every task atomic, every wave
footprint-disjoint, every task's two models chosen — and a verified-clean freeze check.

**Exit receipt example:**
`✅ Phase 6 (TASK GRAPH) — docs/plans/abc-123-rate-limiting.task-graph.md — 9 tasks, 3 waves (1/5/3), footprint check clean, freeze check clean (no code written in 0–6), hub src/container.ts owned by T9, ~24 agents projected — approved by human`
