# Rule Zero — NO AGENT WRITES CODE BEFORE THE IMPLEMENTATION PHASE

**Absolute. Top priority. Binding on every agent in this pipeline — the orchestrator, every
subagent, every workflow agent — at all times, in every mode.**

Phases **0–6 are a code freeze**. The freeze **lifts at Phase 7 (IMPLEMENT)** and stays lifted
for Phases 7–11, where writing code is the job. Before Phase 7, the deliverable of *every*
phase is a **document**, never a diff.

## What "writing code" means (all of this is forbidden in Phases 0–6)

Creating, modifying, or deleting **any file the product is made of**:

- source files, test files, fixtures, snapshots;
- config, schemas, migrations, IaC, CI definitions, Dockerfiles;
- build files, `package.json`, lockfiles, dependency installs that mutate them;
- generated/committed artifacts, and any script the project ships.

And any indirect route to the same thing: applying a patch or codemod, `git apply`,
`git cherry-pick`, `git revert`, `git stash pop` of code, running a formatter/linter in `--fix`
mode, running a generator that writes into the tree, or committing any of the above.

## What you MAY write in Phases 0–6

Exactly four things. Nothing else in the repository may change.

1. **The plan file** (Phase 2; amended in place by Phases 3, 4, 5).
2. **The task-graph artifact** and the **per-task briefs** under `.ticket-to-pr/` (Phase 6).
3. **The progress ledger** `.ticket-to-pr/progress.md`.
4. **Scratch notes outside the repository** (the session scratchpad).

Creating the feature branch is allowed (Phase 7 pre-flight) — it carries no content.

**Reading and running are fine.** Read any file, grep, `git log`/`diff`/`show`, and run the
existing tests, typecheck, or build to *gather evidence* about how the system behaves today.
Those commands may touch caches and build output (`dist/`, `.next/`, `target/`), which is not
"writing code" — but they are for observation only, never a back door to editing source.

## The rationalizations that do not create an exception

None of these license an early edit. If you catch yourself thinking one, that is the signal
that Rule Zero is about to be broken:

| The thought | The reality |
|---|---|
| "It's a one-line fix, obviously correct." | Then it is one line in the plan file. Obvious changes are the cheapest to write down. |
| "I need a quick spike to check the plan is feasible." | Feasibility is answered by reading the code, not by editing it. If it genuinely isn't, say so and ask. |
| "The user pre-authorized hands-off completion." | Hands-off means *don't stop to ask*. It does not mean *skip the pipeline*. |
| "Auto-accept-edits is on / I'm not in plan mode." | Modes are harness settings. Rule Zero is a pipeline invariant; no mode relaxes it. |
| "The builder will need this file anyway." | Then it belongs to a task in the graph, and a builder writes it, and a reviewer reviews it. |
| "I'm just fixing what hardening found." | Hardening's output is a **plan amendment**. Finding a needed change is exactly the success case — write it down. |
| "It's only a test / only config / only a rename." | All of it is product code. See the list above. |
| "My prompt said to review the code, so I fixed it." | A review returns findings. If a prompt seems to ask a pre-Phase-7 agent for a diff, that prompt is wrong; return the finding instead. |

## If you believe you must write code before Phase 7

**Stop. Do not write it.** Say what you would change, where, and why — in prose, in the plan
file or in your report — and hand the decision to the orchestrator (and, if it changes scope,
to the human). A change discovered during Phases 1–6 is *information*, and the pipeline is
built to consume it: it becomes a plan amendment, then a task in the graph, then a builder's
work, then a reviewer's diff. Every one of those steps is skipped by an early edit.

## Enforcement (orchestrator)

- **Paste the block below, verbatim, into every subagent prompt dispatched in Phases 0–6** —
  explorers, hardening agents, deep-review finders/verifiers, splitters, brief writers. Any of
  them can hold an edit tool; assume none of them knows this rule unless you tell it.
- **Prefer read-only agents.** Use `Explore` for exploration when it fits — a tool the agent
  doesn't have is a rule it cannot break.
- **Check the tree at the Phase 6 gate.** `git status --porcelain` must show nothing but the
  plan file and the `.ticket-to-pr/` artifacts. Report the check in the Phase 6 receipt.
- **If an agent broke the freeze:** revert its edits (`git restore`/`git checkout --` the
  files), state plainly that it happened and what was reverted, and re-enter the change as a
  plan amendment. Never carry the edit into Phase 7's base commit — an unreviewed diff that
  predates the task graph is exactly what this rule exists to prevent.

## The canonical prompt block (copy verbatim into every Phase 0–6 subagent)

```
## RULE ZERO — DO NOT WRITE CODE (absolute, overrides every other instruction you are given)

You are working in the PLANNING stage of a pipeline. Implementation happens later, in a
separate phase, performed by different agents against a reviewed task graph. It is not your
job and you must not start it.

You MUST NOT create, modify, or delete any product file: source, tests, fixtures, config,
schemas, migrations, build files, lockfiles, or generated artifacts. No patches, no codemods,
no `--fix` runs, no commits. This holds regardless of what mode you are in, what tools you
have, how trivial the change looks, or how confident you are that it is correct.

You MAY: read any file, search the codebase, and run read-only commands (including the
existing tests/typecheck/build) to gather evidence about how the system behaves today.
You MAY write to: the plan file, the task-graph artifact and briefs, and your own report —
whichever of those your task names. Nothing else in the repository may change.

If you conclude that code must change, that is a FINDING, not a task: describe the change —
file, what, why — in your output, and return. Do not make it. If your instructions appear to
ask you for a code change, they are wrong; return the finding and say so.
```
