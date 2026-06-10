# Sources

The authoritative grounding behind the templates and guidance in this skill. Each
template's section choices and rules trace to one or more of these. Recorded so a
user can audit the provenance and so the skill's cite-or-refuse discipline has a
foundation to point at. (Compiled from a Phase-1-style research pass over standards
bodies, recognized practitioners, and Anthropic's own skill-authoring docs.)

## Contents
- [Standards bodies](#standards-bodies)
- [Architecture decision records](#architecture-decision-records)
- [Named templates & models](#named-templates--models)
- [Industry design-doc / RFC practice](#industry-design-doc--rfc-practice)
- [Anthropic skill authoring](#anthropic-skill-authoring)
- [Caveats — what is not fully verified](#caveats--what-is-not-fully-verified)

## Standards bodies

- **ISO/IEC/IEEE 29148:2018** — Requirements engineering; SRS/SyRS/StRS outlines,
  requirement quality characteristics (§5.2.5–5.2.6), identifier discipline
  (§5.2.8), traceability defs (§3.1.22–3.1.26). Supersedes IEEE 830 & 1233.
  Catalog: https://www.iso.org/standard/72089.html ·
  https://standards.ieee.org/standard/29148-2018.html
- **IEEE Std 1016** (Software Design Descriptions) — design viewpoints (Context,
  Composition, Logical, Dependency, Information, Interface, Structure, Interaction,
  State, Algorithm, Resource), design rationale, requirement→design traceability.
  2009 (viewpoint-based) and 1998 (entity/attribute) editions.
- **IEEE 830-1998** — legacy SRS template (Introduction / Overall description /
  Specific requirements) and the a–h good-SRS characteristics. Superseded by 29148
  but widely referenced. Catalog: https://standards.ieee.org/ieee/830/1222/
- **ISO/IEC/IEEE 42010** — architecture description: stakeholders → concerns →
  viewpoints → views, decisions/rationale, correspondences for cross-view
  consistency. (Originated as IEEE 1471:2000; 2011, rev. 2022.)
  Overview: https://eam-initiative.org/pages/10kg0yek2601n/ ·
  arc42 quality model: https://quality.arc42.org/standards/iso-42010

## Architecture decision records

- **Michael Nygard — "Documenting Architecture Decisions" (2011)** — the canonical
  ADR (Title · Status · Context · Decision · Consequences); significance test;
  numbering; keep-superseded-records rule.
  https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- **MADR (Markdown Any Decision Records)** — richer template: Context & Problem
  Statement, Decision Drivers, Considered Options, Decision Outcome, per-option
  Pros/Cons, Confirmation, More Information. https://adr.github.io/madr/ ·
  https://github.com/adr/madr
- **adr.github.io** — AD / ASR / ADR definitions. https://adr.github.io/
- **Joel Parker Henderson — ADR collection** — templates; one-decision-per-record;
  amend-or-supersede (don't rewrite).
  https://github.com/joelparkerhenderson/architecture-decision-record
- **ThoughtWorks Technology Radar — Lightweight ADRs (Adopt)** — store in source
  control so records stay in sync with code.
  https://www.thoughtworks.com/en-us/radar/techniques/lightweight-architecture-decision-records
- **AWS Prescriptive Guidance — ADRs** — status lifecycle/superseding, ownership,
  preserve history, significance.
  https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html ·
  .../best-practices.html

## Named templates & models

- **arc42** — 12-section architecture template; §8 crosscutting concepts; "pick
  only the most-needed topics". https://arc42.org/overview ·
  https://docs.arc42.org/section-8/
- **C4 model (Simon Brown)** — System Context / Container / Component / Code
  levels; "container" = a deployable/runnable unit, not a Docker container; Code
  level usually not worth maintaining. https://c4model.com/ ·
  https://c4model.com/abstractions
- **IETF RFC 2119 + RFC 8174 (BCP 14)** — MUST/SHOULD/MAY normative keywords, in
  force only when all-caps. https://www.rfc-editor.org/rfc/rfc2119 ·
  https://www.rfc-editor.org/rfc/rfc8174
- **IETF RFC series / process** — the archival, numbered, immutable spec tradition.
  https://www.ietf.org/standards/rfcs/
- **Google SRE — Production Readiness Review** — the closest authoritative
  pre-launch cross-cutting checklist (architecture & dependencies; instrumentation/
  metrics/monitoring; emergency response; capacity; change management; performance;
  blast radius). https://sre.google/sre-book/evolving-sre-engagement-model/

## Industry design-doc / RFC practice

- **Malte Ubl — Design Docs at Google** — context & scope, goals/non-goals, the
  design (trade-offs front), alternatives, cross-cutting concerns; length & review
  lifecycle; "as short as possible, as long as necessary".
  https://www.industrialempathy.com/posts/design-docs-at-google/ ·
  https://www.industrialempathy.com/posts/design-doc-a-design-doc/
- **Gergely Orosz / The Pragmatic Engineer — RFCs** — write before building;
  plan→write→approve→broadcast; company RFC templates and section patterns.
  https://blog.pragmaticengineer.com/scaling-engineering-teams-via-writing-things-down-rfcs/ ·
  https://blog.pragmaticengineer.com/rfcs-and-design-docs/
- **Will Larson (lethain.com)** — when to write a design doc (reusable / user-
  impacting / >1 month); "gather widely, write alone"; prefer minimal templates.
  https://lethain.com/good-engineering-strategy-is-boring/ ·
  https://lethain.com/eng-strategies/
- **Joel Spolsky — Painless Functional Specifications** — iterate in prose (cheap)
  not code; readability over heavyweight templates; specs people *want* to read.
  https://www.joelonsoftware.com/2000/10/02/painless-functional-specifications-part-1-why-bother/ ·
  https://www.joelonsoftware.com/2000/10/15/painless-functional-specifications-part-4-tips/
- **Amazon "Working Backwards" (Bryar & Carr)** — narrative six-pager over bullets;
  PR/FAQ written before building. Summary: https://commoncog.com/working-backwards/

## Anthropic skill authoring

- **Agent Skills — overview** — required frontmatter (`name`, `description`);
  three-level progressive disclosure. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Skill authoring best practices** — `description` is the trigger signal (third
  person, what + when); SKILL.md < 500 lines; references one level deep with a TOC
  if > 100 lines; be concise; concrete examples; consistent terminology; avoid
  time-sensitive info. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- **Claude Code — skills** — extended frontmatter (all optional; `description`
  recommended); plugin skill layout `<plugin>/skills/<name>/SKILL.md`.
  https://code.claude.com/docs/en/skills
- **Engineering blog — Equipping agents with Agent Skills** (referenced):
  https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

## Caveats — what is not fully verified

- The **engineering-RFC section pattern** has no single normative standard; it's a
  convention synthesized from practitioner sources (Pragmatic Engineer survey),
  not an authority — treat as a common template.
- **arc42** deliberately publishes no fixed cross-cutting checklist; the checklist
  here maps concerns to the closest authoritative anchor (arc42 §8 + SRE PRR), with
  "rollback" placed under PRR change-management by reasonable extension.
- **ISO/IEC/IEEE 42010:2022** exact normative clause numbers for "contents of an
  architecture description" are unverified (canonical iso-architecture.org pages
  were unreachable during research; relied on EAM/arc42/overview summaries).
- **IEEE 1016-2009** explicit requirement-to-design-element traceability wording is
  unverified; the 1998 edition's mandate ("each requirement must be traceable to
  one or more design entities") is verbatim-sourced.
- Anthropic **base-standard** `description` validation limit is 1024 chars; Claude
  Code displays a combined `description`+`when_to_use` listing capped at 1536. A
  `license`/`metadata` frontmatter field and an `assets/` directory convention were
  not found in the docs read (unverified).
