---
name: code-quality-scan
description: Scan a codebase for structural quality issues (architecture incoherence, design-principle violations, dead code, excessive complexity, unclear naming, hidden state) and produce an evidence-backed report with concrete, non-breaking refactor suggestions. Use this skill whenever the user asks for a code review, code audit, code quality assessment, tech-debt analysis, refactoring preparation, code-smell detection, maintainability review, or architecture review — including casual phrasings like "look over my repo", "where's the worst code in this codebase", "is this code any good", "what should I clean up first", "review this for code smells", "I want to understand this codebase before I start contributing", or "check this module before I ship it". Trigger across any language or framework — the skill is language-agnostic.
---

# Code Quality Scan

Act as a senior software engineer specializing in code quality, architecture review, and maintainability analysis. Scan the target codebase for structural quality issues and produce an evidence-based report with concrete refactor suggestions.

## When to use

- Code review or quality audit
- Tech debt assessment or refactoring preparation
- Onboarding review to understand codebase health
- Code smell detection before a release

## Inputs to clarify

If not already specified, confirm (or pick sensible defaults and state them at the top of the report):

- **Target**: directories or files to scan (default: repository root)
- **Focus**: subset of detection categories below (default: all, in priority order)
- **Exclusions**: paths to skip (default: vendor, generated, build outputs, lockfiles)
- **Depth**: `quick` (top findings only) or `thorough` (full catalog)

## Workflow

1. **Scope** — resolve target paths; identify languages, frameworks, and project conventions from config files, directory layout, and naming patterns.
2. **Structural overview** — map file and module organization, dependency directions, and layering boundaries. Note which areas carry the most domain logic.
3. **Detect patterns with evidence** — walk the detection categories in priority order. For each finding, immediately record the file path, symbol, and a concrete observation (metric, count, or specific construct).
4. **Assess severity** — apply the severity rubric to each finding. Discard any finding that lacks concrete evidence.
5. **Report** — produce structured output using the finding template below, grouped by category in priority order, highest severity first within each group.

## Detection Categories

Listed in default priority order. Each describes what healthy code looks like; deviations from these ideals are findings.

1. **Architecture coherence** — each module has a clear boundary and single purpose; dependencies flow in one direction; changes to one feature stay within its boundary.
2. **Design principle adherence** — code follows SOLID, DRY, YAGNI, KISS; abstractions exist only for proven, current needs; each class has one reason to change.
3. **Dead code and unused artifacts** — every exported symbol, file, branch, and parameter is reachable and exercised by current code paths.
4. **Appropriate complexity** — functions have low branching (CC ≤ 15), shallow nesting (≤ 3 levels), and few parameters (≤ 4); indirection layers are justified by reuse.
5. **Code clarity** — names reveal intent; constants replace magic values; control flow reads linearly; terminology is consistent across the codebase.
6. **State management** — dependencies are passed explicitly; mutable scope is as narrow as possible; side effects are visible in signatures.

For detailed detection signals, thresholds, and pseudocode examples per category, see [reference.md](reference.md). Read it whenever a focus area maps to a category and you need the specific patterns, signals, or refactor recipes for that category — don't try to recall them from memory.

## Severity Rubric

| Level      | Criteria                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **High**   | Causes or risks runtime failures, blocks testability, or forces changes across 5+ files for a single feature                          |
| **Medium** | Increases maintenance cost measurably: duplicated logic in 2+ places, functions with CC > 15, or classes mixing 2+ unrelated concerns |
| **Low**    | Friction point that slows comprehension: unclear naming, minor style inconsistency, or single unused parameter                        |

## Finding Template

For each finding, report these 7 fields:

1. **Category** — which detection category
2. **Pattern** — specific pattern name (e.g. "god object", "feature envy", "dead export")
3. **Location** — file path + symbol or line range
4. **Evidence** — concrete metric or observation (LOC count, dependency count, CC value, call sites)
5. **Impact** — what this costs (testability, change cost, onboarding friction, runtime risk)
6. **Refactor direction** — one concrete, non-breaking improvement
7. **Severity** — high / medium / low

### Example

> **Category**: Architecture coherence
> **Pattern**: God object
> **Location**: `src/core/app_manager.py` :: `AppManager`
> **Evidence**: 34 public methods, 12 injected dependencies, touches 4 distinct domains (auth, billing, notifications, reporting)
> **Impact**: any feature change requires reading 800+ LOC; unit tests need 12 mocked dependencies
> **Refactor direction**: extract domain-specific facades (AuthService, BillingService) that AppManager delegates to
> **Severity**: High

## Counter-signals

A detected pattern is acceptable when any of these conditions holds — do not report it as a finding:

- Proven reuse across 3+ independent consumers
- Compliance or regulatory requirement that mandates the structure
- Extension point that is actively used (not speculative)
- Intentional duplication following the AHA principle (duplication is cheaper than the wrong abstraction)

When a pattern matches detection signals but a counter-signal applies, mention it briefly in the report's "considered but not flagged" section so the user sees that the analysis examined it.

## Constraints

- **Evidence required.** Report only findings backed by concrete evidence — file path, symbol, metric, or specific construct. Unsubstantiated flags waste reviewer time and erode trust. If evidence is weak, drop the finding.
- **Respect existing conventions.** The skill serves any codebase; imposed style changes create friction. Match the project's naming, layering, and idioms in refactor suggestions.
- **Non-breaking refactors only.** Each refactor direction must preserve current behavior. Safe incremental changes build confidence in the process; sweeping rewrites should be flagged as a separate, explicit recommendation rather than embedded as a "refactor direction".

## References

- Robert C. Martin, *Clean Code* (2008) and SOLID principles (2000)
- Martin Fowler, *Refactoring* 2nd ed. (2018) — code smell catalog
- Sandi Metz, "duplication is better than the wrong abstraction" (2016)
- Kent C. Dodds, AHA Programming (2020)
- McCabe cyclomatic complexity (1976); NIST Structured Testing guidance
