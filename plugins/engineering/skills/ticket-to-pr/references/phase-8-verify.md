# Phase 8 — VERIFY

The wave gates in Phase 7 proved the pieces integrate as they landed. This phase proves the
**finished change** is green — the full build, the full test suite, the full lint, once, on the
completed branch. The two are not redundant: the wave gate is a fast typecheck-shaped check run
many times to stop a broken contract propagating; this is the slow, complete one, run once, because
it's what the PR claims.

There is a specific reason not to trust the wave gates here. Every task's tests passed **inside its
own worktree**, in isolation, and each wave gate then ran only build/typecheck plus *that wave's*
touched tests. Nothing so far has run the **whole suite against the whole change**. A test in a
corner of the repo that no task touched — and that no wave gate thought to run — is exactly what
this phase exists to catch.

## The branch

- **IF `superpowers:verification-before-completion` is available** → use it. Its whole point is
  refusing to let "done" be asserted without evidence, which is this phase's point.
- **ELSE** → run the project's own commands and read the output.

Say which path ran.

## Discovering the commands

Don't guess them. Look, in roughly this order:

- `package.json` scripts (`build`, `test`, `lint`, `typecheck`), `Makefile`, `justfile`, `Taskfile`.
- The **CI config** (`.github/workflows/*.yml`, etc.) — the most reliable source, because it's what
  actually gates the PR you're about to open. If CI runs it, run it.
- The repo's `CONTRIBUTING.md` / `README.md`.

Run **build, tests, and lint** — all three. A lint failure is a red PR just as surely as a failing
test.

## Evidence, not claims

Paste the command and its real output. "Tests pass" is a claim; `142 passed, 0 failed` under the
command that produced it is evidence. This output is reused verbatim in the Phase-9 PR body, so
capture it properly.

If you find yourself writing a summary of a result you didn't actually read, stop and run it.

## GATE — red means go back

**If anything is red, go back to Phase 7 and fix it.** Do not proceed to a PR on a broken build.
Re-open the Phase 7 todo; don't leave it falsely complete.

- A failure inside one task's area → fix it (as the orchestrator, or by re-dispatching that task).
- A failure across a seam between tasks → that's a contract bug; see Phase 7's failure policy, and
  consider whether the *plan* was wrong (back to Phase 2).
- **If it can't be made green** — genuinely environmental, a pre-existing failure on the default
  branch, flaky in a way you can demonstrate, or out of scope — **stop and tell the human exactly
  what's failing**, with the output. Say what's yours and what was already broken (check: does it
  fail on the default branch too?). Never paper over it, never disable the test, never `--skip` your
  way to green.

**Exit:** build/test/lint green, with the output shown.

**Exit receipt example:**
`✅ Phase 8 (VERIFY) — ran pnpm build && pnpm test && pnpm lint — build ok, 142 passed / 0 failed, lint clean (output above)`
