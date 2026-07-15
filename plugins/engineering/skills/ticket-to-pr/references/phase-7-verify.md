# Phase 7 — VERIFY

Phase 6's task reviews were task-scoped, each seeing only one task's diff. This phase proves the
**finished change** is green in full — the complete build, the complete test suite, the complete
lint, once, on the finished branch. That's not redundant with what Phase 6 already ran: no task
reviewer ever saw the whole codebase.

There is a specific reason not to skip this because Phase 6 "already looked green." A test in a
corner of the repo that no task touched — and that no task reviewer thought to check — is exactly
what this phase exists to catch.

## The iron law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Claiming work is done, green, or passing without having run the command **in this message** is
dishonesty, not efficiency — and violating the letter of this rule violates its spirit. Before you
state any status or express any satisfaction ("great", "done", "should pass now"):

1. **Identify** the command that proves the claim.
2. **Run** the full command, fresh and complete.
3. **Read** the whole output — exit code, failure count.
4. **Verify** the output actually confirms the claim. If not, state the real status with evidence.
5. **Only then** make the claim, *with* the evidence.

Skipping any step is claiming, not verifying. "Should work", "I'm confident", "linter passed"
(linter ≠ compiler), "the agent said success" (verify independently — check the VCS diff), "just
this once", "I'm tired" — none of these are evidence. Run the command.

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
- **Anything else** → re-run the affected task through Phase 6's implementer → reviewer loop
  rather than hand-patching it.
- **If it can't be made green** — genuinely environmental, a pre-existing failure on the default
  branch, flaky in a way you can demonstrate, or out of scope — **stop and tell the human exactly
  what's failing**, with the output. Say what's yours and what was already broken (check: does it
  fail on the default branch too?). Never paper over it, never disable the test, never `--skip` your
  way to green.

**Exit:** build/test/lint green, with the output shown.

**Exit receipt example:**
`✅ Phase 7 (VERIFY) — ran pnpm build && pnpm test && pnpm lint — build ok, 142 passed / 0 failed, lint clean (output above)`
