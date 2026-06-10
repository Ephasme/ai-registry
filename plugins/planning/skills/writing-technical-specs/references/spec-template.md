# Technical specification template

The structure to write the spec against. It is a **synthesis** of the recognized
standards and practice (IEEE/ISO 29148, IEEE 1016, arc42, C4, RFC 2119, Google and
Amazon design-doc practice) — see [Provenance](#provenance). It is a checklist, not
a mandate: **pick the sections the spec actually needs and omit the rest.** A
section with nothing true to say is dropped or marked "N/A — *why*", never padded.

Everything structural in the finished spec is grounded in the real code with a
`file:line` citation. The design describes changes to the system **as it exists
today**, not to an imagined system.

## Contents
- [How to adapt this](#how-to-adapt-this)
- [The template](#the-template)
- [Writing the requirements](#writing-the-requirements)
- [Provenance](#provenance)

## How to adapt this

Pick the emphasis from the spec's job (you set this in Phase 0):

- **Requirements-heavy** (defining *what* the system must do, e.g. an SRS) →
  §§1–5, 8, 12–14. Lean on Requirements.
- **Design / architecture-heavy** (defining *how* it's built, e.g. an SDD) →
  §§1–4, 6–11, 13–14. Lean on Proposed design and Cross-cutting concerns.
- **Proposal / RFC** (deciding *whether and how*) → §§1–4, 6, 9–11, 14. Lean on
  Context, Goals/non-goals, Alternatives, Rollout.

Right-size by depth: a mini-spec might be §§1–4, 6, 9 only; a load-bearing design
spec uses most sections. Don't force all of them.

## The template

```markdown
# <Title> — Technical Specification

## 0. Front matter
- **Status:** draft | in review | approved | superseded
- **Authors / primary contacts**, **Reviewers/approvers**, **Last updated** (date)
- **Change log** — date · author · what changed (the doc is living memory)

## 1. Summary (TL;DR)
The one-screen version: the problem, the chosen approach, and the headline
decisions. A reviewer who reads nothing else should still get the gist.

## 2. Context & scope
Background and the real current state — what exists today, grounded in the code
(file:line) and the verified corpus. A system-context view (C4 Level 1: the system,
its users, and the external systems it talks to). Objective facts only; the
argument comes later.

## 3. Goals and non-goals
- **Goals** — what success means; the quality goals that drive the design (the
  top 3–5).
- **Non-goals** — things that could reasonably be goals but are deliberately out
  of scope. Explicit non-goals are one of the highest-value parts of a spec.

## 4. Constraints & assumptions
Constraints that limit design freedom (technical, regulatory, organizational,
conventions) and the assumptions the spec rests on. Mark any assumption you
couldn't verify as such — don't disguise it as fact.

## 5. Requirements
Uniquely identified, verifiable, normative (see "Writing the requirements" below):
- **Functional requirements** — what the system must do.
- **External interface requirements** — APIs, events, integrations with
  neighboring systems (sketch the contracts; match the real call sites, file:line).
- **Data requirements** — entities, fields, relationships, retention; matched to
  the real schema/entities and any migration implied.
- **Quality / non-functional requirements** — performance, availability, security,
  usability — stated as measurable scenarios, not adjectives.

## 6. Proposed design
The solution. Open with an overview, then detail, with the **trade-offs front and
center**:
- **Solution strategy** — the fundamental approach and why it meets the goals.
- **Building-block view** — decomposition into components/modules (C4 Level 2
  containers, Level 3 components), each mapped to real code (file:line): what's
  new, what changes, what is reused unchanged.
- **Runtime / behavior** — how the pieces interact in the important scenarios
  (sequence of calls, state transitions).
- **Data model & migrations** — the concrete schema changes against the real
  entities, and the migration/backfill plan.
- **API / interface contracts** — the concrete shapes (request/response, events),
  consistent with existing contracts.

## 7. Cross-cutting concerns
Address each that applies; mark the rest "N/A — why":
security & authz · privacy / data protection · observability (logs, metrics,
alerts) · failure modes & resilience · performance / SLOs & capacity · rollout &
feature flags · backout / rollback · testing strategy.

## 8. Architecture decisions
The ADRs from Phase 3 — embedded or linked. Each decision ties to the goals/
concerns it serves and to the code it commits.

## 9. Alternatives considered
The materially different whole-design approaches that were rejected, and why this
one best satisfies the goals. (Per-decision alternatives live in the ADRs; this is
the design-level view.)

## 10. Risks & technical debt
Known risks (likelihood × impact), and any debt this design knowingly takes on,
prioritized. "Risks (must have!)" — don't skip this.

## 11. Rollout & operational plan
Milestones and sequencing, dependencies, the rollout mechanism (flags, phased
%), monitoring during rollout, and the **backout/rollback** plan.

## 12. Verification & validation strategy
How each requirement will be confirmed — inspection, demonstration, analysis, or
test — and the overall test approach.

## 13. Traceability
The thread that proves nothing is dangling: **need → requirement → design element
(file:line) → test**. A short matrix is enough; it's what makes the spec auditable.

## 14. Open questions
What remains undecided or unverified, with an owner where possible. Honest open
questions beat confident guesses.

## 15. Glossary & references
Domain/technical terms (ubiquitous language, mapped to code symbols) and the
source documents, ADRs, and tickets this spec draws on.
```

## Writing the requirements

- **Uniquely identify each requirement** with a stable ID (e.g. `FR-1`, `NFR-3`).
  Assign once; never change or reuse an ID, even if the requirement changes or is
  deleted — IDs are what traceability hangs on (IEEE 29148 §5.2.8).
- **Make each one verifiable** — worded so you could write a test or define an
  acceptance check. "Fast" is not verifiable; "responds within 200 ms at p95 under
  N concurrent users" is.
- **Use RFC 2119 keywords for normative force**, in all-caps, meaning exactly:
  **MUST/SHALL** = absolute requirement; **MUST NOT/SHALL NOT** = absolute
  prohibition; **SHOULD** = do it unless there's a weighed, understood reason not
  to; **MAY** = truly optional. Reserve MUST for genuine requirements; don't
  inflate. Add the BCP 14 boilerplate if the spec relies on these keywords.
- **Each requirement is singular, necessary, and unambiguous** — one capability,
  interpretable only one way (IEEE 29148 §5.2.5). The set is consistent (no
  conflicts, uniform terminology and units) and contains no unresolved TBDs by the
  time the spec is "done" (§5.2.6).

## Provenance

- Section skeleton (front matter, summary, context, goals/non-goals, design,
  alternatives, cross-cutting): Design Docs at Google (Ubl); Pragmatic Engineer /
  Uber RFCs; Sourcegraph/HashiCorp/Monzo patterns; Amazon working-backwards.
- Requirements sections & quality attributes: ISO/IEC/IEEE 29148:2018; IEEE
  830-1998 §§4–5.
- Design/architecture sections, building-block/runtime/deployment views: IEEE
  1016; arc42 §§1–12; C4 model (Brown).
- Cross-cutting checklist: arc42 §8 + Google SRE Production Readiness Review.
- Normative keywords: IETF RFC 2119 / RFC 8174 (BCP 14).
- Traceability (need ↔ requirement ↔ design ↔ test): IEEE 29148 §3.1.24; IEEE
  830 (backward/forward); IEEE 1016 §4.3.

Full URLs and the verified/unverified caveats are in `sources.md`.
