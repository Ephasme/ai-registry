# Phase 7 — VERIFY

Phase 6's task reviews were task-scoped, and its finishing step only ran the project's basic
test command before offering the merge/PR/keep/discard menu. This phase proves the **finished
change** is green in full — the complete build, the complete test suite, the complete lint, once,
on the finished branch. That's not redundant with what Phase 6 already ran: no task reviewer ever
saw the whole codebase, and the finishing step's test run may not include lint or a full build.

There is a specific reason not to skip this because Phase 6 "already looked green." A test in a
corner of the repo that no task touched — and that no task reviewer or the finishing step's quick
test run thought to check — is exactly what this phase exists to catch.

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
command that produced it is evidence. This output is reused verbatim in the Phase-8 PR body, so
capture it properly.

If you find yourself writing a summary of a result you didn't actually read, stop and run it.

## GATE — red means go back

**If anything is red, go back to Phase 6 and fix it.** Do not proceed to review on a broken build.
Re-open the Phase 6 todo; don't leave it falsely complete.

- **Small and local** (a naming fix, a guard clause, a missed null check) → fix it inline as the
  orchestrator, re-verify, push.
- **Anything else** → re-run the affected task through `subagent-driven-development`'s
  implementer → reviewer loop rather than hand-patching it.
- **If it can't be made green** — genuinely environmental, a pre-existing failure on the default
  branch, flaky in a way you can demonstrate, or out of scope — **stop and tell the human exactly
  what's failing**, with the output. Say what's yours and what was already broken (check: does it
  fail on the default branch too?). Never paper over it, never disable the test, never `--skip` your
  way to green.

**Exit:** build/test/lint green, with the output shown.

**Exit receipt example:**
`✅ Phase 7 (VERIFY) — ran pnpm build && pnpm test && pnpm lint — build ok, 142 passed / 0 failed, lint clean (output above)`
