# Phase 2 — PLAN

Turn the grounded understanding (and the design file you were handed, if the work came in as one)
into a concrete, ordered implementation plan. This plan is the artifact Phases 3, 4, and 5 attack,
and the one Phase 6 hands task by task to its per-task build loop — so its job is to be **specific
enough to be wrong**. A plan vague enough that no reviewer can disagree with it is a plan nobody
can implement task by task, either.

## Write the plan yourself — in plan mode, no code

This phase owns its own planning procedure; it does not hand off to a plan-writing skill. Enter
plan mode (or otherwise commit to writing only the plan file) and write the plan to the structure
below. Announce that you're writing the implementation plan. Rule Zero
([`rule-zero-no-code.md`](rule-zero-no-code.md)) is in force: the plan file is the **only** thing
this phase produces — a plan step is a paragraph, never a scaffolded file, a stub, an empty test,
or a "starter" implementation.

Write the plan for an engineer who is skilled but knows almost nothing about this codebase, this
toolset, or the problem domain — and don't assume they have good test-design instincts. Document
what they need: which files to touch per task, the actual code, how to test it, what to check. DRY,
YAGNI, TDD, frequent commits.

## Plan document header

**Every plan starts with this header** — the Global Constraints block is load-bearing: Phase 6's
task reviewer is handed those constraints verbatim as its attention lens, so a constraint that
isn't written here is a constraint no reviewer enforces.

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about the approach]

**Tech Stack:** [Key technologies/libraries]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

---
```

## File structure, then tasks

Before defining tasks, map which files each task creates or modifies and what each is responsible
for — this is where decomposition gets locked in. Design units with clear boundaries: one clear
responsibility per file, files that change together living together, split by responsibility not by
layer. In an existing codebase, follow the established patterns; don't unilaterally restructure, but
if a file you must modify has grown unwieldy, folding a split into the plan is reasonable.

**Right-size each task.** A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. Fold setup, config, scaffolding, and docs into the task whose deliverable
needs them; split only where a reviewer could meaningfully reject one task while approving its
neighbor. Each task ends with an independently testable deliverable.

## Task structure

Each task is its own `### Task N` section — Phase 6's `task-brief` extracts tasks by that heading,
so the heading format matters. Steps are checkboxes (`- [ ]`), each one action (2–5 min): write the
failing test → run it, see it fail → minimal implementation → run it, see it pass → commit.

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.ts`
- Modify: `exact/path/to/existing.ts:123-145`
- Test: `tests/exact/path/to/test.ts`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact names, parameter and return
  types. A task's implementer sees only their own task; this block is how
  they learn the names and types neighboring tasks expose.]

- [ ] **Step 1: Write the failing test**

```ts
test('specific behavior', () => {
  expect(fn(input)).toEqual(expected)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `<test command for this file>`
Expected: FAIL with "fn is not defined"

- [ ] **Step 3: Write minimal implementation**

```ts
export function fn(input) {
  return expected
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `<test command for this file>`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add <paths>
git commit -m "feat: <specific feature>"
```
````

## No placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never
write them:

- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without the actual test code)
- "Similar to Task N" (repeat the code — the engineer may read tasks out of order)
- Steps that say what to do without showing how (code steps need code blocks)
- References to types, functions, or methods not defined in any task

## What the plan must carry (checklist)

Beyond the structure above, the plan is only usable by Phase 6 if each task carries:

- **Numbered tasks, in order** — what gets done, in what order, and *why that order*.
- **Files per task** — concrete: `src/limits/RateLimiter.ts (new)`, not "the rate limiting layer."
- **Named contracts and interfaces** — every new type, exported symbol, endpoint, table, or event a
  later task consumes, named explicitly. Leave the interface implicit ("then wire it up") and the
  implementer invents the contract on the spot — often wrong, expensive to unwind later.
- **Tests** — what proves each task works, and what proves the whole thing works.
- **Risks** — what could go wrong, what's uncertain, what you're assuming. Phases 3–5 hunt here
  first; anything you flag yourself is a finding they don't have to re-derive.

## Self-review before you exit

After writing the complete plan, read it with fresh eyes against the spec — a checklist you run
yourself, not a subagent dispatch:

1. **Spec coverage** — skim each requirement in the spec; can you point to a task that implements
   it? List any gaps and add tasks for them.
2. **Placeholder scan** — search the plan for the red flags above. Fix them.
3. **Type consistency** — do the types, signatures, and property names used in later tasks match
   what earlier tasks defined? A function called `clearLayers()` in Task 3 but `clearFullLayers()`
   in Task 7 is a bug.

Fix issues inline — no need to re-review, just fix and move on.

## Write it down — as a file

The plan must be a **file**, not a message — Phases 3–5 edit it in place across their
loop-until-clean rounds, and Phase 6 reads it. Put it wherever the repo keeps plans (check for
`docs/plans/`, `.plans/`); otherwise `docs/plans/<ticket-key>-<slug>.md`. Note the path — every
later phase refers to it.

**Exit:** a written plan file exists, with the header + Global Constraints, numbered `### Task N`
sections, per-task files, named contracts, tests, and risks.

**Exit receipt example:**
`✅ Phase 2 (PLAN) — wrote plan in plan mode — docs/plans/abc-123-rate-limiting.md (7 tasks, Global Constraints set, 3 contracts named)`
