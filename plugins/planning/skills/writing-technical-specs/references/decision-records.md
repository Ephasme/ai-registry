# Decision records & open-decision proposals

Two templates and the protocol for using them. A **settled** decision becomes an
**ADR**. An **open** decision becomes a **proposal** you present before stopping to
ask the user to choose; the chosen option then becomes an ADR. Both are grounded
in what the code actually does — consequences and option costs are stated in terms
of the real codebase, not the abstract.

## Contents
- [Is the decision architecturally significant?](#is-the-decision-architecturally-significant)
- [ADR template (settled decisions)](#adr-template-settled-decisions)
- [ADR rules](#adr-rules)
- [Open-decision proposal template](#open-decision-proposal-template)
- [The stop-and-ask protocol](#the-stop-and-ask-protocol)
- [Provenance](#provenance)

## Is the decision architecturally significant?

Record a decision when it "affects the structure, non-functional characteristics,
dependencies, interfaces, or construction techniques" of the system (Nygard); i.e.
it addresses an architecturally significant requirement — one with a measurable
effect on the architecture or quality of the system (adr.github.io). Skip an ADR
for decisions that are trivial, temporary, or already documented elsewhere
(Henderson). One ADR captures **one** decision.

## ADR template (settled decisions)

The canonical Nygard format — the minimum. Use these five fields:

```markdown
# ADR-NNNN: <short noun phrase naming the decision>

## Status
<proposed | accepted | deprecated | superseded by ADR-MMMM>  ·  <YYYY-MM-DD>

## Context
The forces at play — technical, organizational, regulatory — stated as facts, in
value-neutral language. What is motivating this decision? Ground it in the code:
what does the system do today (file:line) that makes this decision necessary?

## Decision
The response to those forces, in full sentences, active voice: "We will …".
State precisely what changes in the code, what is added, what stays.

## Alternatives considered
The other options that were on the table and why each was not chosen. (For a
decision settled by the research/user, this is the record of what was rejected.)

## Consequences
The resulting context after applying the decision — all of it, positive and
negative. What becomes easier, what becomes harder, what new constraints or risks
appear, and what code/areas it commits you to.
```

**When a decision is richer**, add MADR fields: `Decision Drivers` (the qualities/
constraints forcing the choice), `Considered Options` with per-option **Pros and
Cons**, a `Decision Outcome` ("Chosen option: X, because …"), and `Confirmation`
(how compliance with the decision will be verified — e.g. a test, a review, a lint
rule). MADR's mandatory core is still just Context · Decision · Consequences.

## ADR rules

- **One decision per record**, numbered sequentially; numbers are never reused.
- **Immutable once accepted.** Don't rewrite an accepted ADR — *amend* it with new
  information, or **supersede** it with a new ADR and set the old one's status to
  `superseded by ADR-MMMM`. Keep the superseded record; the history is the point.
- **Store in-repo, next to the code**, under version control, so the record stays
  in sync with what it describes (ThoughtWorks; Nygard `doc/arch/`).
- **Keep it to ~1–2 pages.** An ADR is a decision record, not the spec.

## Open-decision proposal template

For a decision the research/user has **not** settled, present this before writing
any spec that depends on it. Give **4–5 concrete options** — real, distinct
approaches, not strawmen.

```markdown
## Decision needed: <name of the open decision>

**Why this is open:** <what's undetermined, and why the spec can't proceed
without choosing — 1–3 sentences>

**What the code constrains:** <relevant current-state facts, file:line, that bound
the viable options>

### Option A — <name>
- **What it is:** <concrete description>
- **Cost against this codebase:** <what it would take to build given how the code
  is structured today — what it touches, what it breaks, roughly how much work>
- **Trade-offs:** <pros / cons, including non-functional impact: security, perf,
  operability, migration risk, reversibility>

### Option B — <name>
… (same shape)

### Options C, D, [E] …
… (same shape)

### Recommendation
**Option <X>**, because <the reasoning, tied to the goals and the code reality>.
What would change the recommendation: <conditions under which a different option
wins>.
```

Each option's trade-offs must be assessed **against the actual codebase**, not in
the abstract — feasibility and cost are properties of the code as it exists, not of
the idea. (Alternatives-considered framing: Google design docs; HashiCorp
"abandoned ideas".)

## The stop-and-ask protocol

- After presenting the proposal(s), **stop and ask the user to choose.** Do not
  pick for them and proceed; the choice is theirs to make.
- Use a **structured question tool** if one is available — these are
  pick-between-options-with-tradeoffs decisions, which is exactly what those tools
  are for. Lead with your recommended option.
- **Batch the questions.** Gather every open decision and ask them in as few
  rounds as possible rather than dripping one at a time.
- When the user chooses, **convert the chosen option into an ADR** (status
  `accepted`), carrying over its alternatives and consequences. Then continue.

## Provenance

ADR fields and rules: Michael Nygard, "Documenting Architecture Decisions";
the MADR template; ThoughtWorks Technology Radar; AWS Prescriptive Guidance;
Joel Parker Henderson's ADR collection. Significance test: Nygard + adr.github.io.
Full citations in `sources.md`.
