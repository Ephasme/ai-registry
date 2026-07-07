---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "[--pack] [--file] What will the next session be used for?"
disable-model-invocation: true
---

# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

By default, output the document directly in the chat response — it's meant to be read or copied right away, not hunted for on disk. Pass `--file` to instead save it to a file in the temporary directory of the user's OS (not the current workspace), named meaningfully with today's date, e.g. `handoff-<topic>-YYYY-MM-DD.md`.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead — that keeps the handoff short and avoids drift from the source of truth. Pass `--pack` to override this: embed the full content of those dependencies directly in the document instead of referencing them, so the result is self-contained and still useful after moving to another machine that won't have access to the original paths or URLs (a fresh clone, a different laptop, etc). `--pack` and `--file` are independent — combine them to get a self-contained file.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed additional arguments beyond the flags, treat them as a description of what the next session will focus on and tailor the doc accordingly.
