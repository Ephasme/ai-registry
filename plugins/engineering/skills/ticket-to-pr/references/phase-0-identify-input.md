# Phase 0 — IDENTIFY INPUT

How to recognize the four ticket/spec sources and pull the work item through the right
channel. The goal of this phase is to get the **full ticket content + any linked context**
into the conversation, grounded enough that Phase 1 (UNDERSTAND) has everything it needs.

Each source below states: how to **detect** it, the **tool** to read it, and the **fallback**
when that tool isn't connected this session — because the available MCP set varies by machine,
and the cross-cutting rule is "check availability, then branch, and say which path you took."

## Detection at a glance

| Looks like | Source | Read with |
|---|---|---|
| `notion.so/…`, a 32-hex page id, or "the Notion ticket / NID-123" | Notion | Notion MCP → fallback |
| `github.com/<org>/<repo>/issues/<n>`, "issue #123", a GH Project item | GitHub | GitHub MCP / `gh` |
| `linear.app/…/issue/ABC-123`, an `ABC-123` key, "the Linear issue" | Linear | Linear MCP |
| pasted text, "here's the spec", or a file path (`.md`, `.txt`, doc) | Raw spec | Read the file / use the pasted text |

If two could match (e.g. a Linear key mentioned inside a pasted spec), prefer the **explicit
artifact the user pointed at**. If nothing identifies a work item, **ask** which to drive.

## Notion ticket

- **Detect:** a `notion.so`/`www.notion.so` URL, a bare 32-char hex id, or the user naming a
  Notion page / a ticket id like `NID-123`.
- **Read:** if a **Notion MCP is connected** (tool names contain `notion`), fetch the page and
  its content — title, body, properties (status, acceptance criteria, links), and any child
  blocks or linked pages that carry requirements. Follow links the ticket leans on.
- **Fallback (no Notion MCP — the common case here):** Notion pages need auth, so you can't
  fetch them blind. Ask the user to **paste the ticket content** (or export it to a file you
  can read). Don't guess at a page you can't see. Note the ticket id regardless — Phase 8 needs
  it for the `[NID-123]` PR-title prefix.

## GitHub Issue or Project item

- **Detect:** a `github.com/<org>/<repo>/issues/<n>` URL, "issue #123", or a reference to a
  GitHub Project card/item.
- **Read:** with the **GitHub MCP** (`mcp__…github…`), read the issue (e.g. `issue_read` /
  `get_issue`), its body, labels, linked PRs, and comment thread for clarifications. For a
  **Project item**, resolve it to the underlying issue/PR and read that; if it's a draft item
  with only a title, treat its text as a raw spec and confirm scope with the user.
- **Fallback:** if the GitHub MCP isn't connected, use the **`gh` CLI**
  (`gh issue view <n> --repo <org>/<repo> --comments`). If neither is available, ask the user
  to paste the issue.
- Note the `<org>/<repo>` and issue number — Phase 8 links the PR back with `Closes #<n>`.

## Linear issue

- **Detect:** a `linear.app/<org>/issue/ABC-123` URL, a bare issue key like `ABC-123`, or the
  user naming "the Linear issue".
- **Read:** with the **Linear MCP** (`mcp__…linear…`), read the issue (e.g. `get_issue`): title,
  description, state, labels, sub-issues, and linked documents/comments that carry acceptance
  detail. Read linked sub-issues if the work spans them.
- **Fallback:** if the Linear MCP isn't connected, ask the user to paste the issue. Keep the
  `ABC-123` key — Linear's GitHub integration auto-links a PR/branch that references the key.

## Raw specification

- **Detect:** the user pastes the spec, says "here's the spec", or gives a file path
  (`.md`/`.txt`/design doc).
- **Read:** if it's a **file path**, read the file (and any sibling docs it references). If it's
  **pasted text**, use it directly. A raw spec has no external ticket id, so there's nothing to
  auto-link — the PR just describes the change and references the spec (attach/quote it if
  helpful).
- This is the simplest path: no MCP needed, so no fallback — but apply the same Phase-1 GATE,
  since hand-written specs are often the *least* precise about acceptance criteria.

## What to carry forward

Whichever source, end this phase with: the **ticket id / number / key** (for PR linking), the
**full requirement text**, and the **linked context** that matters. If you had to fall back to
a paste, say so — it means there may be linked context you couldn't see, which raises the bar
for the Phase-1 open-questions check.

**Exit receipt example:**
`✅ Phase 0 (IDENTIFY INPUT) — Linear MCP — read ABC-123 "Per-tenant rate limiting" + 2 sub-issues`
