---
name: code-quality-scan
description: Scan a codebase for structural quality issues (architecture incoherence, design-principle violations, dead code, excessive complexity, unclear naming, hidden state) and produce an evidence-backed, severity-ranked report with concrete, non-breaking refactor suggestions. Runs each review aspect as a parallel reviewer subagent (find phase, default Sonnet 4.6) and verifies + ranks every finding with a cheaper checker subagent (check phase, default Haiku 4.5); both models are overridable via --find-model and --check-model. Use this skill whenever the user asks for a code review, code audit, code quality assessment, tech-debt analysis, refactoring preparation, code-smell detection, maintainability review, or architecture review — including casual phrasings like "look over my repo", "where's the worst code in this codebase", "is this code any good", "what should I clean up first", "review this for code smells", "I want to understand this codebase before I start contributing", or "check this module before I ship it". Trigger across any language or framework — the skill is language-agnostic.
---

# Code Quality Scan

Act as the **orchestrator** of a senior code-review team. You don't read every file yourself — you scope the work, fan it out to specialist reviewer subagents (one per quality aspect), then route their findings through a cheaper checker that verifies and ranks each one. You assemble the survivors into a single evidence-backed report.

Splitting the review this way keeps each reviewer focused on one lens (so it goes deep instead of skimming six concerns at once), runs the lenses in parallel, and spends the expensive model only on *finding* — the mechanical job of *verifying* a concrete claim and scoring its priority is well within a small, fast model's reach, so it runs there.

## When to use

- Code review or quality audit
- Tech debt assessment or refactoring preparation
- Onboarding review to understand codebase health
- Code smell detection before a release

## Options

Read these from the invocation (e.g. `--find-model sonnet --check-model haiku --depth thorough src/`). If absent, use the default and state the resolved value at the top of the report.

| Option | Default | Meaning |
| --- | --- | --- |
| `--find-model` | `sonnet` (Sonnet 4.6) | Model for the per-aspect reviewer subagents (the find phase). |
| `--check-model` | `haiku` (Haiku 4.5) | Model for the verification + ranking subagents (the check phase). |
| `--depth` | `thorough` | `quick` = top findings only, one checker batch; `thorough` = full catalog, per-finding verification. |
| `--focus` | all categories | Comma-separated subset of the detection categories below — only those reviewers are dispatched. |
| target paths | repo root | Positional args: directories/files to scan. |
| `--exclude` | vendor, generated, build outputs, lockfiles | Paths to skip. |

Model values pass straight through to each subagent's `model` parameter. Accept either an alias (`sonnet`, `haiku`, `opus`) or a full model id (e.g. `claude-sonnet-4-6`, `claude-haiku-4-5`). The orchestrator itself runs on the session model regardless of these flags — they only set the subagent models.

## Architecture

```
orchestrator (this session)
  │  1. scope + build a shared context brief
  ├──► find phase  (parallel, model = --find-model) ───────────────┐
  │      reviewer: architecture coherence                          │
  │      reviewer: design principle adherence                      │  one subagent
  │      reviewer: dead code & unused artifacts                    │  per in-scope
  │      reviewer: appropriate complexity                          │  category
  │      reviewer: code clarity                                    │
  │      reviewer: state management                                │
  │  2. collect raw findings, assign stable ids                ◄───┘
  ├──► check phase (parallel, model = --check-model) ──────────────┐
  │      checker: re-read cited code, confirm/refute,              │  verify + rank
  │               apply counter-signals, score priority           │  every finding
  │  3. keep confirmed findings, sort by priority              ◄───┘
  └──► 4. synthesize the report
```

## Workflow

1. **Scope.** Resolve target paths; identify languages, frameworks, layering, and project conventions from config files and directory layout. Apply exclusions. Capture this once as a short **context brief** (languages, frameworks, target paths, exclusions, notable layering) — you'll hand the same brief to every find subagent so none of them has to re-derive it.

2. **Find phase — dispatch one reviewer subagent per in-scope category, all in a single parallel batch**, each with `model = --find-model`. Give each subagent: the context brief, the name of its single category, instructions to read *only its own section* of [reference.md](reference.md) for the detection signals/thresholds/recipes, and the **find output contract** below. Use the prompt template in the next section. A reviewer that goes wide and shallow defeats the purpose — each one owns exactly one lens.

3. **Collect.** Gather every reviewer's JSON output, concatenate, and assign each finding a stable `id` (e.g. `arch-1`, `complexity-3`). Drop exact duplicates (same location + pattern).

4. **Check phase — verify and rank every finding** with `model = --check-model`. Dispatch checker subagents in parallel using the **check prompt template** below. Each checker independently re-reads the cited code and decides whether the finding is real, applies the counter-signals, adjusts severity, and assigns a 0–100 priority score. In `thorough` depth give each finding (or a small batch) its own checker for genuine independent verification; in `quick` depth batch all findings of a category into one checker. Discard `refuted` findings (surface them in "considered but not flagged"); keep `confirmed` and flag `uncertain`.

5. **Report.** Sort the surviving findings by `priority_score` descending (ties broken by severity). Emit the report structure below. Lead with the resolved config (target, depth, focus, find-model, check-model) so the run is reproducible.

## Find subagent — prompt template

Fill the placeholders and dispatch with `model = --find-model`, one per category:

> You are a senior code reviewer auditing code for **ONE** quality aspect: **{CATEGORY_NAME}**. Ignore every other aspect — other reviewers cover those.
>
> Context brief: {languages, frameworks, target paths, exclusions, layering notes}
>
> Read the **{CATEGORY_NAME}** section of `{abs path to reference.md}` for the detection signals, thresholds, and refactor recipes for this aspect. Use them — don't rely on memory. Scan only the target paths.
>
> For every issue with **concrete evidence** (file path, symbol, a metric/count, or a specific construct), emit a finding. If you cannot point to evidence, do not emit it — unsubstantiated flags waste the reviewer's time. Respect the project's existing conventions; refactor directions must be non-breaking and behavior-preserving.
>
> Return **only** a JSON array (no prose), each element with these fields:
> `{ "category", "pattern", "location", "evidence", "impact", "refactor_direction", "severity" }`
> where `severity` ∈ `high|medium|low` per the rubric I gave you. Return `[]` if you find nothing.

## Check subagent — prompt template

Fill with the collected findings and dispatch with `model = --check-model`:

> You are an adversarial verifier and triager. For each candidate finding below, independently re-read the cited code and judge whether it is a **real** defect — do not trust the finding's own claims.
>
> Findings: {JSON array of findings, each including its `id`}
>
> For each finding decide:
> - **verdict**: `confirmed` (evidence holds and it's a genuine defect), `refuted` (evidence doesn't hold, the cited code differs, or a counter-signal applies), or `uncertain` (can't tell from the cited location). Default to `refuted` when evidence is thin and you can't substantiate it.
> - **confidence**: 0.0–1.0.
> - **adjusted_severity**: `high|medium|low` (you may overrule the reviewer's severity).
> - **priority_score**: 0–100 — rank by **severity × blast radius × fix-leverage**: how bad it is if left, how many files/consumers/paths it touches, and how much improvement a non-breaking fix buys per unit of effort. A high-severity issue confined to one dead file outranks nothing; a medium issue rippling across the hot path outranks an isolated high.
> - **rationale**: one or two sentences, citing what you saw in the code.
>
> Counter-signals that should push a finding to `refuted`: proven reuse across 3+ independent consumers; a compliance/regulatory mandate; an actively-used extension point; intentional AHA duplication (cheaper than the wrong abstraction).
>
> Return **only** a JSON array, each element: `{ "id", "verdict", "confidence", "adjusted_severity", "priority_score", "rationale" }`.

## Detection Categories

Listed in default priority order. Each describes what healthy code looks like; deviations are findings. Pass exactly one to each find subagent.

1. **Architecture coherence** — each module has a clear boundary and single purpose; dependencies flow in one direction; changes to one feature stay within its boundary.
2. **Design principle adherence** — code follows SOLID, DRY, YAGNI, KISS; abstractions exist only for proven, current needs; each class has one reason to change.
3. **Dead code and unused artifacts** — every exported symbol, file, branch, and parameter is reachable and exercised by current code paths.
4. **Appropriate complexity** — functions have low branching (CC ≤ 15), shallow nesting (≤ 3 levels), and few parameters (≤ 4); indirection layers are justified by reuse.
5. **Code clarity** — names reveal intent; constants replace magic values; control flow reads linearly; terminology is consistent across the codebase.
6. **State management** — dependencies are passed explicitly; mutable scope is as narrow as possible; side effects are visible in signatures.

Each find subagent reads only its matching section of [reference.md](reference.md) for the specific signals, thresholds, and refactor recipes — that file carries the per-category detail so reviewers don't work from memory.

## Severity Rubric

Both find and check subagents apply this. Pass it into their prompts.

| Level | Criteria |
| --- | --- |
| **High** | Causes or risks runtime failures, blocks testability, or forces changes across 5+ files for a single feature |
| **Medium** | Increases maintenance cost measurably: duplicated logic in 2+ places, functions with CC > 15, or classes mixing 2+ unrelated concerns |
| **Low** | Friction point that slows comprehension: unclear naming, minor style inconsistency, or single unused parameter |

## Report structure

Use this template:

```
# Code Quality Scan

**Config**: target=… · depth=… · focus=… · find-model=… · check-model=…
**Summary**: N findings confirmed (H high / M medium / L low), K refuted in verification.

## Ranked findings
<table: rank | priority | severity | category | location | pattern>

## Findings in detail
<for each confirmed finding, the 7-field template below, highest priority first>

## Considered but not flagged
<refuted findings + counter-signalled patterns: location, why it was dismissed>
```

Each detailed finding uses these 7 fields:

1. **Category** — which detection category
2. **Pattern** — specific pattern name (e.g. "god object", "feature envy", "dead export")
3. **Location** — file path + symbol or line range
4. **Evidence** — concrete metric or observation (LOC count, dependency count, CC value, call sites)
5. **Impact** — what this costs (testability, change cost, onboarding friction, runtime risk)
6. **Refactor direction** — one concrete, non-breaking improvement
7. **Severity & priority** — severity level + the checker's priority score and confidence

### Example detailed finding

> **Category**: Architecture coherence
> **Pattern**: God object
> **Location**: `src/core/app_manager.py` :: `AppManager`
> **Evidence**: 34 public methods, 12 injected dependencies, touches 4 distinct domains (auth, billing, notifications, reporting)
> **Impact**: any feature change requires reading 800+ LOC; unit tests need 12 mocked dependencies
> **Refactor direction**: extract domain-specific facades (AuthService, BillingService) that AppManager delegates to
> **Severity & priority**: High · priority 88 · confidence 0.9

## Counter-signals

A detected pattern is acceptable when any of these holds — the checker should refute it, and the orchestrator lists it under "considered but not flagged":

- Proven reuse across 3+ independent consumers
- Compliance or regulatory requirement that mandates the structure
- Extension point that is actively used (not speculative)
- Intentional duplication following the AHA principle (duplication is cheaper than the wrong abstraction)

## Constraints

- **Evidence required.** Findings without concrete evidence (file, symbol, metric, construct) are dropped — first by the reviewer, then again by the checker. Unsubstantiated flags erode trust.
- **Verification is independent.** The checker must re-read the cited code rather than trust the reviewer's claim; that second look is the whole point of the check phase and the reason it can run on a smaller model.
- **Respect existing conventions.** Match the project's naming, layering, and idioms in refactor suggestions — imposed style changes create friction.
- **Non-breaking refactors only.** Each refactor direction must preserve current behavior. Flag sweeping rewrites as a separate, explicit recommendation rather than embedding them as a "refactor direction".
- **Graceful fallback.** If subagents are unavailable in the current environment, run the find and check phases sequentially in-context using the same category list, contracts, and rubrics — the report structure is unchanged.

## References

- Robert C. Martin, *Clean Code* (2008) and SOLID principles (2000)
- Martin Fowler, *Refactoring* 2nd ed. (2018) — code smell catalog
- Sandi Metz, "duplication is better than the wrong abstraction" (2016)
- Kent C. Dodds, AHA Programming (2020)
- McCabe cyclomatic complexity (1976); NIST Structured Testing guidance
