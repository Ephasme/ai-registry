# Phase 8 — PR

Conventions for getting the verified change into a pull request that links back to its ticket. The
throughline: the PR should let a reviewer (human or skill) understand *what changed and why* and
trust that it works, and it should auto-connect to the ticket it came from.

## The branch and the commits already exist

Phase 6's implementers commit — so the **feature branch was created before Phase 6 ran** (never
build on the default branch), and each task's fix loop committed as it went. There is nothing to
create here except the PR itself. Confirm the state before pushing:

- You are **on the feature branch**, not the default one. It's named for the work and carries the
  ticket key where there is one — `nid-123-rate-limit`, `abc-123-fix-webhook` — which is what lets
  the Linear/GitHub integrations associate the branch with the issue by themselves.
- The commits are there, one per task, in plan order (`git log --oneline`).

## Tidy the history — for the reviewer, not for the record

The per-task commit sequence is one-per-task in plan order. That usually reads fine. But the
history exists to serve **the reviewer**, not to document how the work was produced.

So: if the task-by-task sequence tells a clear story, leave it alone. If it doesn't — a task whose
fix rounds left three commits on one file, or a split that made sense during implementation and no
sense to a human — **squash it into the commits a human would have made.** Match the repo's
existing style (check `git log`: prefix conventions like `feat:`/`area:`, imperative mood) and
honour any trailers or sign-off it requires. Don't invent attribution the repo doesn't use.

## Push & open the PR — confirm first

**GATE.** Pushing and opening a PR are outward-facing (SKILL Operating rules) — **get explicit
go-ahead unless the human pre-authorized hands-off completion.** Then open the PR via whatever's
available: the **GitHub MCP** (`create_pull_request`) or **`gh pr create`**.

### PR title — link the ticket per source

The title carries the auto-link for integration bots, so encode the ticket id where the integration
expects it:

- **Notion:** prefix with the bracketed id — `[NID-123] Add per-tenant rate limiting`. The
  Notion↔GitHub integration scans the title for the id and back-links the PR onto the ticket.
- **Linear:** include the issue key — `ABC-123` — in the title or branch; Linear's GitHub
  integration links it automatically. (`Fixes ABC-123` in the body also works.)
- **GitHub issue:** put `Closes #123` / `Fixes #123` in the **body** so merging closes the issue.
- **Raw spec:** no external id — write a plain descriptive title.

### PR body template

```markdown
## What & why
<briefly: the change and the problem it solves.>

## Ticket
<link to the Notion page / GitHub issue (Closes #N) / Linear issue (ABC-123) / "spec: <path>">

## Changes
- <key change 1>
- <key change 2>

## Verification
<the actual build/test/lint commands run, and their result — paste the evidence from Phase 7>

## Notes for the reviewer
<deferred decisions, anything intentionally out of scope, areas wanting a closer look>
```

Write the PR body **for the reviewer, not about the process** — they don't need to know it was
built task by task through a subagent loop, and a PR that explains its own machinery reads like
it's making excuses. What they need is what changed, why, and how you know it works.

Capture the **PR URL** — Phase 11 needs it.

**Exit:** an open PR, its URL captured for the handoff.

**Exit receipt example:**
`✅ Phase 8 (PR) — confirmed by human — pushed abc-123-rate-limiting (7 commits), opened https://github.com/org/repo/pull/456 ([ABC-123] …, Fixes ABC-123)`
