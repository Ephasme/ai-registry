---
name: plan-hardening
description: Harden an engineering plan against reality — verify every claim it makes against the codebase and the docs, surface the collateral damage it doesn't handle, fix, and re-review until a round finds nothing. Use when the user hands over a plan, design doc, RFC, ADR, refactor proposal, or migration document and asks anything skeptical of it — harden, stress test, poke holes in, sanity check — even without the word "plan". Also when another skill needs a plan verified against code before implementation. For a near-final spec that needs only a structural read (ambiguity, contracts, invariants), prefer spec-handoff-review.
---

# Plan Hardening

Run the plan through rounds of review and fixes until it holds up to reality. Each round verifies claims, surfaces findings, gathers any needed clarifications, applies fixes, and re-reviews — and stops when a round produces no fixes.

## Guardrails

- **Read-only.** Verification means reading: open files, grep, fetch docs, run read-only queries — never write or execute code to settle a claim. A claim that needs more than a read-only lookup is beyond this skill's reach: flag it unverified and route it to Step 2 as a question.
- **The plan stays a plan.** The deliverable is the plan's own text — its prose and its steps — made more accurate and more complete. A few lines of illustrative pseudo-code are fine when that's the clearest way to pin down an algorithm, data shape, or tricky sequencing: non-runnable, no imports, no error handling. Anything longer becomes a plan instruction instead (file, function, expected behavior) for an implementer to act on later.

## Step 0 — Locate the plan

Identify what plan is being hardened. Look in the current conversation and any uploaded files for a plan, design doc, refactor proposal, RFC, ADR, or migration document. If multiple candidates exist, ask the user which one (or which sections) to harden. If nothing is present, ask the user to share or paste the plan.

Work from the literal text. If the plan is a file, edit it in place; if it arrived as conversation text, write it to a file first and harden that file — the loop needs one artifact to converge on across rounds.

## Step 1 — Review the plan against reality

Walk the plan and surface findings of two kinds: claims that don't hold up against reality, and collateral damage the plan doesn't handle. Both feed the same list for Step 2 — capture them as you go, in either order.

**Verify every claim.** A "claim" is anything assertable: file paths, function names, API behaviors, data shapes, sequencing assumptions, performance numbers, library capabilities, configuration values, current-state descriptions ("X currently does Y"), or causal reasoning ("changing A will fix B"). For each, do exactly one of:
- **Read the related code** — open files, trace call sites, inspect schemas — when the claim is about the codebase.
- **Consult official documentation** — fetch the docs page, API reference, or changelog — when the claim is about a third-party library, framework, or platform. Prefer primary sources over blog posts.
- **Run a read-only query** — grep/search, a check-only linter or type-checker, a read-only DB or API query.
- **Flag it as an unverified finding** for Step 2 to ask about, when no read-only lookup can settle it.

Capture the source of each verification (file:line, doc URL, search result) as you go, and cite it in the output — the user shouldn't have to trust you on the verification itself. Judge each claim against its source, never against how plausible it sounds; plausible-sounding wrong claims are exactly what this loop exists to catch. If you have no verification tools at all, every empirical claim falls into the last bullet and goes to the user.

**Assess collateral damage.** For each step in the plan, consider what else it touches and whether the plan handles it:
- other call sites and consumers
- data integrity (migrations, in-flight records, idempotency)
- security and permissions
- backwards compatibility (clients, persisted state, wire formats)
- performance and scaling
- tests and CI
- observability (logs, metrics, alerts)
- rollout and rollback
- operational risk and blast radius

Anything the plan doesn't mention is a finding by default. Anything it does mention but handles in a way you'd push back on is a finding flagged as a judgment call for the user.

## Step 2 — Triage and ask

Rank every finding as **critical**, **major**, or **minor**:
- **Critical** — the plan won't work as written, will cause data loss or outage, or has a security flaw.
- **Major** — the plan will technically work but produces a meaningfully worse outcome or leaves significant risk unhandled.
- **Minor** — wording, polish, nice-to-haves.

For any critical or major finding where there's a real choice to make (tradeoffs, design preferences, scope decisions), ask the user before moving to Step 3. Use a structured question tool when one is available (`AskUserQuestion` in Claude Code). Gather every open question first and ask them in one round rather than dripping them one at a time. For each, state the finding, the options, and the implication of each option concretely.

Findings with a clear right answer don't need a question — they go straight to Step 3. Minor findings are noted for the final summary but not fixed.

If the user pushes back on a finding, re-verify against the source rather than deferring or doubling down. Findings can be wrong, and that's exactly why verification matters.

## Step 3 — Fix critical and major findings

Apply fixes for every critical and major finding from Step 2, incorporating the user's clarifications where given. Every design decision that had a real choice in it should already have been triaged as a question in Step 2 — fix what the user settled, and raise anything new the same way rather than deciding it silently.

Leave minor findings as-is — they get noted in the final summary, not fixed in the plan.

After applying fixes, list what changed — briefly, e.g. "Plan step 3: corrected file path", "Plan step 5: added rollback section", "Plan step 7: removed, superseded by step 6" — so the user can see the diff at a glance.

## Step 4 — Stop or loop

- **If Step 3 applied no fixes this round** → stop. Summarize: what was changed across all rounds, what residual minor items remain, and any explicit assumptions the hardened plan now rests on.
- **Otherwise** → return to Step 1 and run another full pass on the updated plan. The fixes themselves are new claims and new steps that may have introduced new problems or new collateral damage.

If after 3 full rounds critical findings keep emerging, stop the loop and tell the user: the right answer is sometimes "this approach is fundamentally wrong; consider alternative X" rather than another round of patching.

## Output style

- Lead with the findings — they're what the user is here for.
- Present the full updated plan at the end of each round (or a clearly-marked diff if it's very large). The user shouldn't have to mentally reassemble it from deltas.
