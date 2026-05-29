---
name: plan-hardening
description: Iteratively review and harden an engineering plan by verifying claims against the codebase and docs using available tools, surfacing failed claims and unhandled collateral damage, then fixing and re-reviewing until no critical or major findings remain. Use when the user asks to harden, review, audit, stress test, verify, sanity check, or "poke holes in" a technical plan, design doc, RFC, ADR, refactor proposal, or migration document — even without the word "plan". Also trigger when handed a step-by-step engineering proposal and asked anything skeptical before implementation. Prefer this over ad-hoc review whenever such a plan exists in the conversation.
---

# Plan Hardening

Run the plan through rounds of review and fixes until it holds up to reality. Each round verifies claims, surfaces findings, gathers any needed clarifications, applies fixes, and re-reviews — and stops when a round produces no fixes.

## Preparing step — Locate the plan

Before doing anything else, identify what plan is being hardened. Look in the current conversation and any uploaded files for a plan, design doc, refactor proposal, RFC, ADR, or migration document. If multiple candidates exist, ask the user which one (or which sections) to harden. If nothing is present, ask the user to share or paste the plan.

Do not invent or summarize the plan from memory — work from the actual text.

## Step 1 — Review the plan against reality

Walk the plan and surface findings of two kinds: claims that don't hold up against reality, and collateral damage the plan doesn't handle. Both feed the same list for Step 2 — capture them as you go, in either order.

**Verify every claim.** A "claim" is anything assertable: file paths, function names, API behaviors, data shapes, sequencing assumptions, performance numbers, library capabilities, configuration values, current-state descriptions ("X currently does Y"), or causal reasoning ("changing A will fix B"). For each, do exactly one of:
- **Read the related code** — open files, trace call sites, inspect schemas — when the claim is about the codebase.
- **Consult official documentation** — fetch the docs page, API reference, or changelog — when the claim is about a third-party library, framework, or platform. Prefer primary sources over blog posts.
- **Run a tool** — search, query, computation — when the claim is empirically testable with what's available.
- **Flag it as an unverified finding for Step 2 to ask about** if you can't verify it with available tools.

Capture the source of each verification (file:line, doc URL, search result) as you go so it can be cited in the output. Do not accept a claim because it sounds plausible — plausible-sounding wrong claims are exactly what this loop exists to catch. If you have no verification tools at all, every empirical claim falls into the last bullet and goes to the user.

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

For any critical or major finding where there's a real choice to make (tradeoffs, design preferences, scope decisions), ask the user before moving to Step 3. Use a structured question tool when one is available (e.g. `ask_user_input_v0`) — these decisions are typically pick-between-options with tradeoffs, which is what those tools are built for. Gather every open question first and ask them in one round rather than dripping them one at a time. For each, state the finding, the options, and the implication of each option concretely.

Findings with a clear right answer don't need a question — they go straight to Step 3. Minor findings are noted for the final summary but not fixed.

If the user pushes back on a finding, re-verify against the source rather than deferring or doubling down. Findings can be wrong, and that's exactly why verification matters.

## Step 3 — Fix critical and major findings

Apply fixes for every critical and major finding from Step 2, incorporating the user's clarifications where given. Do not silently make design decisions that should have been triaged as questions in Step 2.

Leave minor findings as-is — they get noted in the final summary, not fixed in the plan.

After applying fixes, list what changed — briefly, e.g. "Plan step 3: corrected file path", "Plan step 5: added rollback section", "Plan step 7: removed, superseded by step 6" — so the user can see the diff at a glance. If no critical or major findings were found this round, this step results in no changes — that's the signal Step 4 uses to stop the loop.

## Step 4 — Stop or loop

- **If Step 3 applied no fixes this round** → stop. Summarize: what was changed across all rounds, what residual minor items remain, and any explicit assumptions the hardened plan now rests on.
- **Otherwise** → return to Step 1 and run another full pass on the updated plan. The fixes themselves are new claims and new steps that may have introduced new problems or new collateral damage.

If after 3 full rounds critical findings keep emerging, stop the loop and tell the user: the right answer is sometimes "this approach is fundamentally wrong; consider alternative X" rather than another round of patching.

## Output style

- Lead with what you found, not what you did. The user cares about the findings first.
- Show your verification work for non-obvious claims — cite the file and line, doc URL, or search result. Don't ask the user to trust you on the verification itself.
- When the plan changes, present the full updated plan at the end of each round (or a clearly-marked diff if it's very large). The user shouldn't have to mentally reassemble it from deltas.
- Be direct about uncertainty. "I couldn't verify X — please confirm" is more useful than a confident guess.
