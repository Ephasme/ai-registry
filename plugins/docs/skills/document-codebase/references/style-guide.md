# Style guide

Hand this to every authoring agent and apply it again in the editorial pass.
Consistency here is what lets many authors read as one. The rules are few on
purpose — follow them exactly so pages are interchangeable in tone.

## Voice & tense

- **Third person, present tense, indicative.** "The `Order` aggregate rejects a
  second confirmation." Not "we reject…", not "you should…", not future tense.
- **Describe what the system does, not how to change it.** This is reference
  documentation of the system as it exists, not a tutorial or a TODO list.
- **Plain and direct.** Short sentences. No marketing adjectives ("powerful",
  "robust", "seamless"). State the fact and cite it.
- **Define a term once**, in the glossary; elsewhere just use it. Don't re-explain.

## Citations — the core convention

Every non-trivial claim is either cited or marked unverified.

- Format: `path/from/repo/root/file.ext:line` (or `:start-end` for a range).
- Put the citation inline right after the claim, in backticks.
- Example: "Cancellation is only allowed before shipment
  (`src/orders/order.rb:142`)."
- If you assert something you could not pin to code, mark it inline:
  `*(unverified — <why>)*` and add it to the page's gaps.

## Cross-references

- Link concepts to the page that owns them using relative markdown links:
  `[bounded context](../contexts/billing/overview.md)`.
- Link to a specific section with an anchor:
  `[invariants](../contexts/billing/aggregates.md#invariants)`.
- The first mention of another area's concept on a page should link; repeats
  needn't.
- When you link to something outside your area, also emit a `crossref_request`
  so the reconciler can confirm the target exists.

## Flagging discrepancies and gaps

These are first-class content, not apologies. Keep them factual.

- **Discrepancy** (doc disagrees with code): document what the **code** does in
  the body, then record the conflict for GAPS.md:
  "Existing doc `<source>` states X; code does Y (`file.ext:line`)."
- **Gap** (couldn't verify / couldn't find): never paper over it. State the
  topic, why it's unresolved, and what would resolve it.

## Formatting

- One `#` H1 per page (its title). Sections use `##`; subsections `###`.
- Use tables for enumerations with parallel structure (events, commands, fields,
  rules). Use bullet lists for everything else short. Reserve prose for the
  "why".
- Code symbols, file paths, event/command/field names: in `backticks`.
- Show real names from the code, not paraphrases — if the class is
  `OrderPlaced`, write `OrderPlaced`, not "the order-placed event".
- Keep pages focused; if a page outgrows its template, that's a signal the area
  should be split (raise it rather than writing a sprawling page).

## What not to do

- Don't invent behavior, defaults, or rationale to fill a gap — flag it.
- Don't copy existing docs verbatim without verifying; they may be stale.
- Don't introduce a synonym for a glossary term — use the preferred term.
- Don't editorialize about code quality; document what is, not what should be.
