# Phase 9 — CODE REVIEW

Get the **whole change** reviewed by a reviewer that is **not you**. You just spent nine phases
becoming invested in this plan being right; that's exactly the state of mind that misses its flaws.
The value here comes from the reviewer's independence, so run one and take its findings seriously.

**This is not a repeat of Phase 6's task reviews.** Those were *task-scoped gates*: each judged
one task's diff against one task's brief, deliberately blind to the rest of the codebase. Every
one of them could pass while the assembled change is still wrong — because no task reviewer ever
saw the whole thing. This is the first pass that looks at the change **as a whole**, across the
task boundaries, which is precisely where this kind of build's characteristic failures live: a
contract two tasks agreed on that neither got quite right, a duplicated helper three tasks each
wrote their own copy of, an abstraction that made sense per task and reads as incoherent
assembled.

Run it on the **most capable model available** (Opus 4.8). This is the last gate before a human's
time is spent.

## The branch

- **IF the PR is already open** (it is, by Phase 8) → use **`/review`** — it reviews the PR on
  GitHub, which is what a human reviewer will be looking at.
- **ELSE / fallback** → use **`/code-review`** on the working diff. Also the right choice for an
  extra local pass before pushing fixes.

Say which reviewer ran. If neither is available, do the review yourself against the diff — and say
that's what happened, since a self-review is materially weaker evidence.

## What to feed it

Give the reviewer the context it can't get from the diff alone:

- The ticket's **acceptance criteria**, and the **plan**. A reviewer that knows what the change was
  *supposed* to do can catch the most dangerous class of bug in this pipeline: code that is
  internally correct but doesn't do what the ticket asked.
- **Any deferred Minor findings** from Phase 6's task reviews, if they were carried forward rather
  than fixed. Hand that list over and ask it to triage: which of
  these must be fixed before merge, now that they can be seen together? Three Minors that each
  looked like polish in isolation can be one Important when they turn out to be the same smell in
  three places. **A roll-up nobody reads is a silent discard** — this is where it gets read.

## Enumerate the findings

End the phase with the findings written out and **triaged by severity**:

- **critical / major** → blocking. These drive Phase 10's loop.
- **minor / nice-to-have** → non-blocking. These go to the Phase-11 handoff notes.

Don't silently drop a finding you disagree with. If you think the reviewer is wrong, say so
explicitly with your reasoning — `superpowers:receiving-code-review`, if available, is exactly the
discipline for this: verify the claim rather than either performatively agreeing or dismissing it.
A finding you reject on inspection is a fine outcome; a finding you quietly ignore is not.

**Exit:** a review with its findings enumerated and triaged.

**Exit receipt example:**
`✅ Phase 9 (CODE REVIEW) — ran /review on PR #456 — 5 findings: 1 critical (unbounded retry loop), 2 major, 2 minor`
