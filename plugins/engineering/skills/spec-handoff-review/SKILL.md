---
name: spec-handoff-review
description: Run a single closing structural review of a spec or engineering plan right before it is handed to an implementer, using design-quality lenses (two-implementer divergence, hidden assumptions, failure-mode coverage, invariants, interface contracts, state reachability, coherence, verifiability). Trigger on "final pass", "final hardening", "final review", "last round before implementation", "pre-handoff review", "structural review before handoff", or indirect phrasings like "stress test this once more before I send it", "anything still ambiguous in here", or "what would break if I gave this to an engineer tomorrow" — whenever a spec exists in the conversation and the user signals it is near-final. Distinct from iterative plan-hardening, which verifies claims against code and docs — this skill assumes claim verification is done and instead hunts for ambiguity, missing contracts, unstated assumptions, and unhandled state transitions that would let two competent engineers build incompatible systems.
---

# Spec Handoff Review

This is a **single, closing structural sweep** of a spec or plan, run right before an implementing agent (or engineer) starts building from it. Anything ambiguous, missing, or contradictory that survives this pass ships into the implementation.

This skill is deliberately different from iterative `plan-hardening`:

- `plan-hardening` verifies claims against code and docs across multiple rounds and stops when no fixes remain.
- This skill assumes that work has already happened (or isn't the priority right now) and instead probes the spec's **structural integrity** through design-quality lenses. It surfaces the kinds of defects that survive claim-verification: latent ambiguity, hidden assumptions, missing failure paths, unstated invariants.

Both can exist in the same workflow: run `plan-hardening` to convergence, then run `final-plan-hardening` as the closing pass before handoff.

## Guardrails

- **Read-only.** This pass reasons about the spec's text — cross-referencing sections, checking terms against each other, comparing against documentation or established principles when a lens calls for it. It does not run tools, execute code, or perform empirical verification against a live system; that's `plan-hardening`'s job, and it's assumed done by the time this pass starts. If a claim surfaces here that actually needs empirical checking, note it as a finding pointing back to a plan-hardening round rather than trying to verify it yourself.
- **The spec stays a spec.** Every fix is a textual edit to the spec — a sentence, a section, a definition, a table — or a specific open question for the user. A short pseudo-code snippet is fine when it's the clearest way to pin down an algorithm or a tricky sequencing rule — keep it illustrative (a few lines, non-runnable), not a working implementation. Never insert actual runnable code, diffs, or scripts into the document. The interface signatures used under the Interface/contract lens are a related tool: a one-line `(inputs) -> (outputs) {pre, post}` shape is a specification device, not code.

## The plan you're reviewing

Find the actual plan before doing anything else — current conversation, uploaded files, attached docs. If multiple candidates exist, ask the user which one (or which sections) to harden. Do not summarize or reconstruct it from memory; work from the literal text. If nothing is present, ask the user to paste or share it.

If the spec is structured around the convention of distinguishing **hard constraints** from **open proposals** (a common pattern, and one the user may be using), treat those two categories asymmetrically:

- Hard constraints are the load-bearing rules. Coherence findings between them are critical.
- Open proposals are not yet decided. They become findings when *some* allowable choice within the proposal would violate a hard constraint or another proposal, or when leaving them open creates downstream divergence risk.

If the spec doesn't use this convention, treat everything as a hard constraint by default unless the text explicitly marks it as tentative.

## Step 1 — Coverage delta

Before picking lenses, produce a short coverage delta. Identify the spec sections that received the **least** attention in any prior review rounds and explain why (e.g., "Sections on retry behavior and DB transaction boundaries were lightly touched in rounds 1–2 because reviewers focused on the agentic loop control flow"). Plan to spend disproportionate attention on those sections in this pass.

How to identify prior coverage:

- Scan the conversation history for prior review outputs, finding lists, or summaries.
- Check uploaded files for round-N reports.
- If the conversation contains no signal of prior rounds, ask the user: *"Have prior review rounds happened? If yes, what lenses or angles did they emphasize, and which sections of the spec did they cover lightly?"* Adapt the rest of the pass to the answer.

Output the coverage delta as a short paragraph at the top of the review — not a buried footnote. It's the justification for which lenses you pick next and where you focus.

## Step 2 — Pick at least two lenses you haven't already leaned on

This is a non-repetition rule. The point of a final pass is to find what the prior rounds *missed*, not to re-run them. Pick at least two lenses that prior rounds did not lean on, prioritized by relevance to the under-covered sections you just identified.

If there have been no prior rounds, all eight lenses are fair game — pick the two-to-four most relevant to the spec's risk profile (e.g., a spec heavy on state machines pulls state-reachability and invariant; a spec heavy on external integrations pulls failure-mode coverage and interface/contract).

State explicitly which lenses you're using and why, before producing findings. This makes the pass auditable and prevents silent drift back to lenses you've already exhausted.

## The eight lenses

Each lens is a way of looking at the spec. They overlap, but each has a distinct "what it catches" signature. The parenthetical examples below are illustrative — adapt them to the spec in front of you.

### 1. Two-implementer divergence

**The question:** If two competent engineers built independently from this spec, where would they produce incompatible systems?

**What it catches:** Ambiguity about data shapes, ordering, naming, types, default values, edge-case behavior. Implicit "obvious" choices that aren't actually obvious. Underspecified interfaces between components. Anywhere the spec leaves a choice but doesn't acknowledge it as a choice.

**How to apply:** For each major component or interface, write down the smallest decision the implementer must make to write the first line of code. If the spec doesn't answer it, that's a finding.

### 2. Hidden-assumption

**The question:** What does the plan rely on without stating?

**What it catches:** Ordering guarantees ("messages arrive in send order"), idempotency of upstream calls, clock behavior (monotonic vs. wall-clock, skew across nodes), message uniqueness, exactly-once vs. at-least-once delivery, network reliability, transaction isolation level, default character encodings, timezone assumptions.

**How to apply:** Read each step and ask "what must be true about the world for this to work?" Any answer the spec doesn't state is a finding. The classic tell is a verb that quietly assumes a property — "process", "store", "send", "retry" — each of which has multiple semantically different implementations.

### 3. Failure-mode coverage

**The question:** For each external dependency, tool call, and DB transaction, what does the plan say happens when it fails, times out, or returns partial results?

**What it catches:** Silent fallthrough on errors. Missing retry / backoff specification. Unhandled timeouts. Partial-write recovery. What state the system is in after a failure. Whether failures are observable.

**How to apply:** Enumerate every external boundary in the spec (HTTP calls, DB writes, tool invocations, file I/O, IPC). For each, locate the spec's handling of: timeout, transient error, permanent error, partial success, malformed response. Silence on any of these is a finding by default. Note: "silence is a finding" is the rule — don't accept "this is obvious" as an answer.

### 4. Invariant

**The question:** What must always be true across the system, and who enforces it?

**What it catches:** Assumed-but-unstated invariants (e.g., cursor monotonicity, task-index ↔ GUID consistency, summary-vs-chunk alignment, terminal-action finality). Invariants the spec asserts but doesn't assign an enforcer to. Invariants that can be broken by an explicitly allowed operation.

**How to apply:** List every invariant the system relies on. For each, locate the component or step responsible for maintaining it. Unowned invariants are findings. Also: trace each invariant against every operation that mutates relevant state — if any operation could violate it, the spec must say how that's prevented.

### 5. Interface / contract

**The question:** Between each pair of components, are inputs, outputs, preconditions, and postconditions fully specified? Are shared concepts defined identically wherever they appear?

**What it catches:** Components referenced from multiple places with subtly different signatures. Shared terms (e.g., NO_OP, terminal action, retry, idempotent) used with drift in meaning across sections. Missing preconditions ("X assumes Y is already true") or postconditions ("after X, Z holds"). Return values that are described in one place and not in another.

**How to apply:** For each shared concept, grep (or visually scan) every occurrence in the spec. If the definitions don't match exactly, that's a finding. For each component boundary, write a one-line signature `(inputs) -> (outputs) {pre: ..., post: ...}` and check the spec supports every field. Gaps are findings.

### 6. State-reachability

**The question:** Enumerate the states the system can be in. Is every transition explicitly handled? Are there unreachable or trap states?

**What it catches:** Missing transitions on NO_OP, retry, terminal, or error events. States the spec implies but doesn't name. States that can be entered but not exited (traps). States that are defined but never reached (dead code in the design).

**How to apply:** Draw the state graph from the spec (mentally or on paper). For each state, list every event the spec allows. For each event, confirm the destination state is defined. Any unhandled (state, event) pair is a finding. Bonus: do a reachability analysis from the initial state — anything unreachable or any state with no exit is a finding.

### 7. Coherence

**The question:** Do any hard constraints conflict with each other, or with the open proposals? Does any open proposal, if chosen a certain way, violate a hard constraint?

**What it catches:** Constraints that are individually reasonable but jointly unsatisfiable. Proposals whose acceptable answer space includes options that violate a stated invariant or constraint. Drift between sections written at different times.

**How to apply:** Pair-check the hard constraints. For each pair, ask: is there any system state in which both can simultaneously hold? Then for each open proposal, enumerate plausible resolutions and check each against the hard constraints. Any conflict — actual or potential — is a finding.

### 8. Verifiability

**The question:** For each requirement in the spec, can the implementer (or a reviewer) tell from the built system whether it was satisfied?

**What it catches:** Requirements written so vaguely that no test, observation, or code review could decide whether they hold. Performance targets without a measurement procedure. "Should be efficient", "must be robust", "handles concurrency safely" without operational definition.

**How to apply:** For each requirement, propose the test or observation that would falsify it. If you can't, the requirement is unverifiable and is a finding. The proposed fix is usually "rewrite as a measurable statement" rather than "delete".

## Step 3 — Report findings

For each finding, produce four pieces of information. Don't skip any of them.

1. **Exact location.** Spec section, heading, or paragraph. Pinpoint, not "somewhere in section 3".
2. **The lens that surfaced it.** Name the lens explicitly. This makes the pass auditable and helps the user see lens-level coverage at a glance.
3. **Concrete evidence.** Either: quote the offending text, cite the conflicting section, or reference official documentation / an established design principle (e.g., a specific consistency model, the CAP theorem, a documented behavior of the library being used). **No opinion-only findings.** If you can't back the finding with evidence, drop it.
4. **Severity and proposed fix.** Severity is one of:
   - **Critical** — the spec is wrong, contradictory, or unimplementable as written; implementer cannot proceed without resolving it.
   - **Major** — the spec is implementable but the gap will produce divergent implementations or unhandled failure modes.
   - **Minor** — the spec is implementable; the gap is wording or polish.

   The fix is either a concrete edit to the spec text, or a specific question the spec must answer before handoff. Vague fixes ("clarify section 3") are not acceptable — say what to write or what to ask.

## Meta-rule on challenging design decisions

The user's working convention is that challenges to existing design decisions are welcome only when backed by **scientific evidence or official documentation**, not preference. Honor this strictly.

- "The spec uses pattern X; I'd prefer pattern Y" is not a finding.
- "The spec uses pattern X; per [official doc / paper / RFC], pattern X has property Z that conflicts with hard constraint W in section 5" is a finding.

When you're tempted to raise something on stylistic or preference grounds, either find the evidence or don't raise it. The skill optimizes for high-signal output; padding with preference-based suggestions reduces signal.

## Padding is a failure mode

If you find nothing under a given lens, say so explicitly and move on. **"No issues found under the coherence lens" is a valid and useful result.** It tells the user that lens was checked and came up clean — which is information they need to know the pass was thorough.

Resist the urge to manufacture findings to fill out the report. A short, high-signal review is the goal. A long review padded with preference-based or speculative findings is worse than a short one — it dilutes the critical findings and trains the user to skim.

## Output structure

Produce the report in this order:

```
## Coverage delta
[Short paragraph: which sections got the least attention before, and why this pass focuses where it does.]

## Lenses selected for this pass
- [Lens name] — [one-line reason]
- [Lens name] — [one-line reason]
(at least two, more if warranted)

## Findings

### [Lens name 1]
[Either a list of findings in the format below, or "No issues found under this lens."]

**Finding 1** — [Severity]
- Location: [section / heading / paragraph]
- Evidence: [quoted text / cited section / documentation reference]
- Fix: [concrete edit or specific question]

### [Lens name 2]
[...]

## Summary
[Count by severity. Any cross-lens patterns worth naming. Final recommendation: is the spec ready for handoff, or are there critical findings that must be resolved first?]
```

## Hard rules recap

- Pick at least two lenses; name them explicitly before producing findings.
- Don't repeat lenses prior rounds already exhausted (unless you've confirmed there were no prior rounds).
- Every finding needs evidence — code, cited spec section, or official documentation / established principle.
- Empty lens results are valid and welcome.
- Don't pad. Don't raise preference-based findings.
- Each fix is either a concrete textual edit to the spec (small illustrative pseudo-code is fine) or a specific question it must answer — never actual runnable code, diffs, or scripts inserted into the document.
- Distinguish hard constraints from open proposals if the spec uses that convention.
- Stay read-only: this is a text-level review, not empirical verification (that's `plan-hardening`'s job).
