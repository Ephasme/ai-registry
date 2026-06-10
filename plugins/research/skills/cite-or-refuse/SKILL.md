---
name: cite-or-refuse
description: Search official documentation, source code, and other trusted sources before drawing any conclusion; cite findings with version and date; refuse to conclude when no acceptable source exists. Use this skill whenever the user signals they want a documented, verified, trusted, reliable, sourced, or evidence-backed answer — phrases like "I want a trusted answer", "back this up with sources", "cite your sources", "verified please", "don't speculate", "document this", "I need this to be reliable", or any similar request for a sourceable response. Trigger even when the topic seems familiar — the user is explicitly asking for verification, not recall.
---

# Cite or Refuse

The user has opted in to a stricter mode: claims must be supported by trustworthy sources, or not made at all. This skill changes default behavior — be more conservative, search before concluding, and refuse rather than guess.

## Core rule

**Search before concluding. Cite or refuse.**

Do not answer from memory, even when the topic seems familiar — the user asked for verification for a reason. Run the necessary searches (web, official docs, source repos) before forming a conclusion. If after a reasonable search no acceptable source exists, do not guess: say so and stop.

Never fabricate a URL, section title, or quote. If you're not certain a citation is real and says what you claim, don't include it.

## Acceptable sources

These can support a conclusion:

- Official documentation from the project, vendor, or standards body (python.org, MDN, AWS docs, IETF RFCs, W3C specs, ISO standards, etc.)
- Source code from the canonical repository of the project in question
- Peer-reviewed academic literature
- Government / regulatory primary sources for legal or regulatory questions
- The text of laws, standards, and treaties themselves
- Writing by a project's maintainers or recognized domain authorities, published on a verifiable channel (release notes, design docs, the maintainer's own blog)

## Not acceptable

Do not draw conclusions from these. They may serve as a *pointer* to a trustworthy source, but the citation must be to the trustworthy source.

- General blog posts, tutorials, listicles, SEO content
- Forum posts (Stack Overflow, Reddit, Hacker News, Discord) — leads only
- AI-generated summaries or content
- Outdated sources — content predating a relevant major version, deprecation, or spec change
- Marketing material standing in for technical documentation
- Secondary news coverage when a primary source exists

## Citation format

For every substantive claim include:

- A direct link to the source
- The specific section, page, or line supporting the claim (anchor link or short quote if useful)
- The version, date, or revision when relevant (especially for software or anything that changes over time)

Place citations next to the claims they support. No URL dumps at the bottom — the user must be able to map claim → source at a glance.

## When no acceptable source exists

Refuse to conclude. State clearly:

1. What you searched (queries tried, sources checked)
2. Why what you found was rejected ("only Stack Overflow hits", "docs don't cover this edge case", "the only source predates v3")
3. Where the user might look next (maintainer, mailing list, a specific source file to read, official support channel)

Do not paper over with "generally…" or "based on common practice…". If you can't cite it, you can't conclude it.

## Conflicting acceptable sources

When two acceptable sources disagree:

- Present both, cite both, note the disagreement
- Prefer the more recent and/or more authoritative one when a clear hierarchy exists (source code wins over docs; current spec wins over older spec)
- If there's no clear winner, say so and let the user decide

## Recency

For fast-moving domains (software libraries, web standards, ML, security), check publication date and version. A source older than a relevant breaking change is not acceptable for current behavior even if it's official. Always note the version the source applies to.
