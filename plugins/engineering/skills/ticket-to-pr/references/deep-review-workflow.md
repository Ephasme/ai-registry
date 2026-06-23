# Phase 5 — Deep review workflow

A multi-agent pass over the plan, run **only** when Phase 5's trigger fires (≥ 3
critical/major findings across Phases 3–4, or the human asks). It exists because at that
point the plan has shown it's error-prone, and a find→verify→score→reconcile fan-out catches
what a single linear review misses — while the independent verifier keeps plausible-but-wrong
findings from surviving.

## The design (and why each stage)

1. **Split into scopes.** Break the plan into independent review units (by component, by step
   cluster, by risk area). Independent scopes let reviewers go deep without holding the whole
   plan in context, and parallelize cleanly.
2. **Find (Sonnet 4.6, one per scope).** Each agent hunts bugs/risks/gaps in its scope only.
   Sonnet is fast and strong here; you don't need the orchestrator model for finding.
3. **Verify (Sonnet 4.6, one per candidate).** A *second, independent* agent tries to
   **confirm or refute** each candidate against the scope. This is the load-bearing stage — a
   finding nobody can independently confirm shouldn't drive a plan change.
4. **Score (Haiku, one per survivor).** Cheap criticality triage: `critical | major | minor`
   with a one-line justification. Haiku is plenty for a bounded classification.
5. **Reconcile & fix (you, Opus 4.8, in the main session).** The workflow returns the
   confirmed, scored issues; *you* dedupe them, decide what each means for the plan, and edit
   the plan to resolve every **confirmed critical/major** issue. Reconciliation is judgment
   work — keep it with the orchestrator, not a sub-agent.

Stages 2–4 run as a **pipeline** so each scope's findings flow to verification as soon as
they're found, rather than waiting for the slowest finder.

## Running it

This phase uses the **Workflow** tool (deterministic multi-agent orchestration). Invoking
`ticket-to-pr` and hitting the trigger is the opt-in. Derive the `scopes` from the plan first
(inline), then run the script below via `Workflow({ script, args: { scopes } })`, where each
scope is `{ key, text }`. When it returns, reconcile `result.issues` into the plan.

```js
export const meta = {
  name: 'plan-deep-review',
  description: 'Scope-split plan review: Sonnet finds bugs/risks, a second Sonnet confirms/refutes each, Haiku scores criticality.',
  phases: [{ title: 'Find' }, { title: 'Verify' }, { title: 'Score' }],
}

const FIND = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          detail: { type: 'string' },
          where: { type: 'string', description: 'plan step / file / component the issue is in' },
        },
        required: ['title', 'detail'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['confirmed', 'refuted'] },
    reasoning: { type: 'string' },
  },
  required: ['status', 'reasoning'],
}

const SCORE = {
  type: 'object',
  properties: {
    level: { type: 'string', enum: ['critical', 'major', 'minor'] },
    justification: { type: 'string' },
  },
  required: ['level', 'justification'],
}

const scopes = args.scopes // [{ key, text }], derived from the plan by the orchestrator

// Find → Verify, pipelined per scope (no barrier between scopes).
const reviewed = await pipeline(
  scopes,
  (s) => agent(
    `Review ONLY this plan scope for bugs, risks, and gaps that would cause an incorrect or ` +
    `incomplete implementation. Be concrete.\n\nScope "${s.key}":\n${s.text}`,
    { label: `find:${s.key}`, phase: 'Find', model: 'sonnet', schema: FIND },
  ),
  (review, s) => parallel(
    (review?.findings || []).map((f) => () =>
      agent(
        `Independently CONFIRM or REFUTE this candidate issue against the plan scope. Default ` +
        `to "refuted" if you cannot substantiate it.\n\nCandidate: ${JSON.stringify(f)}\n\n` +
        `Scope "${s.key}":\n${s.text}`,
        { label: `verify:${s.key}`, phase: 'Verify', model: 'sonnet', schema: VERDICT },
      ).then((v) => ({ ...f, scope: s.key, verdict: v })),
    ),
  ),
)

const confirmed = reviewed.flat().filter(Boolean).filter((x) => x.verdict?.status === 'confirmed')

// Score each survivor.
const scored = await parallel(
  confirmed.map((c) => () =>
    agent(
      `Score the criticality of this CONFIRMED plan issue as critical, major, or minor, with ` +
      `a one-line justification.\n\n${JSON.stringify(c)}`,
      { label: `score:${c.scope}`, phase: 'Score', model: 'haiku', schema: SCORE },
    ).then((sc) => ({ ...c, criticality: sc.level, justification: sc.justification })),
  ),
)

return { issues: scored, counts: { found: reviewed.flat().filter(Boolean).length, confirmed: confirmed.length } }
```

After it returns: reconcile `issues` (dedupe overlaps across scopes), then **fix every
confirmed critical/major issue in the plan**. Minor issues: note them for the handoff. Report
the `counts` so the human sees how much was found vs. confirmed.

## Fallback (no Workflow tool)

If the Workflow tool / multi-agent orchestration isn't available, don't skip the scrutiny —
approximate it sequentially: split the plan into the same scopes and, for each, dispatch a
single review **subagent** (via the Agent tool, `Explore` or a general agent) to find issues;
then for each non-trivial finding, dispatch a second subagent to confirm/refute; reconcile and
fix the confirmed ones yourself. It's slower and less parallel, but preserves the
find→verify→reconcile discipline that makes this phase worth running. Say you used the
fallback.
