# PR, review loop & handoff

Conventions for Phases 8–11 — opening the PR, linking it to its ticket, running the review
loop, and handing the result back. The throughline: the PR should let a reviewer (human or
skill) understand *what changed and why* and trust that it works, and it should auto-connect to
the ticket it came from.

## Branch

- Branch off the **default branch** (usually `main`); never commit directly to it.
- Name it for the work, including the ticket key when there is one — e.g. `nid-123-rate-limit`,
  `abc-123-fix-webhook`, `gh-456-csv-export`. A keyed branch name helps Linear/GitHub
  integrations associate the branch with the issue on their own.

## Commit

- Group the work into clear, reviewable commits; write messages that say **what changed and
  why**, in the repo's existing style (look at `git log` — prefix conventions like
  `feat:`/`area:`, imperative mood, etc.).
- Honor any commit trailers or sign-off your environment/repo requires (some setups mandate a
  `Co-Authored-By:` or `Signed-off-by:` trailer). Match the repo; don't invent attribution it
  doesn't use.

## Push & open the PR — confirm first

Pushing and opening a PR are outward-facing (Operating rules) — **get explicit go-ahead unless
the human pre-authorized hands-off completion.** Then open the PR via whatever's available: the
**GitHub MCP** (`create_pull_request`) or **`gh pr create`**.

### PR title — link the ticket per source

The title carries the auto-link for integration bots, so encode the ticket id where the
integration expects it:

- **Notion:** prefix with the bracketed id — `[NID-123] Add per-tenant rate limiting`. The
  Notion↔GitHub integration scans the title for the id and back-links the PR onto the ticket.
- **Linear:** include the issue key — `ABC-123` — in the title or branch; Linear's GitHub
  integration links it automatically. (`Fixes ABC-123` in the body also works.)
- **GitHub issue:** put `Closes #123` / `Fixes #123` in the **body** so merging closes the issue.
- **Raw spec:** no external id — write a plain descriptive title.

### PR body template

```markdown
## What & why
<1–3 sentences: the change and the problem it solves.>

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

Capture the **PR URL** — Phase 11 needs it.

## Review loop (Phases 9–10)

- **Run a reviewer.** Prefer the **`code-review`** skill/command on the working diff
  (`/code-review`); for the **already-open GitHub PR**, use **`/review`**. Fall back to
  `/code-review` on the diff if needed. Say which ran.
- **Fix every finding**, then **re-review until clean** — loop-until-clean, cap 3 (Operating
  rules). Treat **critical/major** as blocking; minor/nice-to-have go to the handoff notes.
- **Re-verify after fixes.** Re-run Phase 7's build/test/lint after each fix round so a review
  nit doesn't quietly break the build.
- **Posting comment replies is outward-facing** — confirm before posting on the PR unless
  pre-authorized. Pushing fix commits to your own PR branch is fine without a fresh prompt once
  the PR exists.
- If round 3 still has critical/major findings, **stop and surface them** with what you tried —
  don't merge-ready a PR you know is dirty.

## Handoff (Phase 11)

Close with a tight summary so the human can pick it up cold:

```markdown
## ticket-to-pr — <ticket id/title>

**Built:** <what shipped, mapped to the acceptance criteria>
**PR:** <url> — <state: checks green? review clean?>
**Verification:** <build/test/lint result>
**Left for you:**
- <deferred decisions / open questions you resolved by assumption — flag them>
- <follow-up tickets worth filing>
- <anything intentionally out of scope>
- <any findings surfaced at a loop cap>
```

Then hand it back. If the pipeline stopped early at a gate, the handoff says **where** it
stopped and **what's blocking**, instead of implying completion.
