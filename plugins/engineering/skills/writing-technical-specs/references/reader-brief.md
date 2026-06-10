# Reader brief — Phase 1 corpus + code fan-out

The copy-paste prompt for the parallel reader subagents, plus how the lead drives
them. The whole point of this phase is that readers **read the actual code**, not
just the documents — the corpus is a set of claims, the code is ground truth.

## Contents
- [How the lead uses this](#how-the-lead-uses-this)
- [The brief (fill in and paste)](#the-brief-fill-in-and-paste)
- [Required structured output](#required-structured-output)

## How the lead uses this

- **Partition into subsystem slices.** A slice is a coherent area of the
  *codebase* plus the corpus material about it — not a doc on its own. Aim for
  5–10 disjoint slices of comparable size; no overlap, no gaps. Partitioning by
  subsystem/domain is preferred precisely because it gives each reader a coherent
  chunk of code to own.
- **Spawn one subagent per slice, in parallel**, pasting the brief below with the
  slice's parameters filled in.
- **Merge, don't re-read.** Each reader returns structured notes; the lead
  consolidates them. The lead should not try to read the whole corpus or whole
  codebase itself — that's what the fan-out is for.
- **Re-slice if a reader reports its area is far bigger than scoped** — split it
  and spawn a follow-up rather than letting one reader sprawl and skim.

## The brief (fill in and paste)

> You are a reader subagent contributing to a technical specification. Your slice
> is **{{slice name}}**.
>
> - **Code to read:** {{code paths / modules / entities for this slice}}
> - **Corpus to read:** {{doc paths, tickets, notes, threads for this slice}}
>
> Your job is to establish the **real current state** of this area of the system
> and extract the technically relevant content for the spec. **Read the code — it
> is ground truth. The documents are claims you verify against the code.**
>
> Do this:
> 1. **Read the listed code** and follow imports / call sites / schema definitions
>    as needed *within your area*. Determine what the code actually does today —
>    its modules, entities, interfaces, data shapes, key control flow.
> 2. **Read the listed corpus material.** For every claim in it that touches your
>    area, check it against the code. When they disagree, the code wins — record
>    the discrepancy.
> 3. **Cite everything.** Use `file:line` for structural facts about the system;
>    use document name + section for corpus facts.
>
> Cite-or-refuse: if you cannot verify something with the code or a source, mark
> it as unverified / open — do not assert it as fact. Inventing plausible detail
> is the worst outcome here; a flagged unknown is useful.
>
> Return **only** the structured notes specified below — this is raw data for the
> lead agent to merge, not a human-facing write-up. No preamble.

## Required structured output

Each reader returns exactly these sections:

- **Slice & coverage** — what you were assigned and what you actually covered
  (name anything you did not get to).
- **Current state of the code** — what exists today in this area: key modules,
  entities, interfaces, data shapes, important control flow — each with
  `file:line`. This is the most important section; be concrete.
- **Key facts** — the technically relevant facts for the spec, each with a
  citation (`file:line` or doc§).
- **Decisions made or implied** — architectural/technical decisions visible in
  this slice, and whether the **code confirms, contradicts, or is silent** on each.
- **Constraints** — technical, regulatory, organizational, or performance
  constraints, with their source.
- **Corpus-vs-code discrepancies** — each place a document disagrees with the
  code: the claim, what the code actually shows, and the `file:line`.
- **Open questions / unknowns** — what's undetermined or couldn't be verified.
- **Glossary terms** — domain/technical terms used here: term → one-line meaning →
  the code symbol or file it maps to.
- **Gaps** — what you couldn't find, couldn't reach, or ran out of room to cover.
