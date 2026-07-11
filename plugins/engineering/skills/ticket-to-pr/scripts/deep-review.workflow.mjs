// @ts-nocheck — Workflow DSL script: agent()/pipeline()/parallel()/phase()/log()/args are
// injected by the Workflow runtime, which also wraps the body so top-level await/return work.
// It is NOT a standalone ES module, so normal TS/JS module checking misreports it.
//
// Phase-5 deep review — a pre-written Workflow script for ticket-to-pr.
//
// Run it with the Workflow tool by path, handing it the plan:
//   Workflow({
//     scriptPath: "${CLAUDE_PLUGIN_ROOT}/skills/ticket-to-pr/scripts/deep-review.workflow.mjs",
//     args: { plan: "<the full plan text>" }            // or { scopes: [{key, focus}], plan }
//   })
//
// Pipeline: split → Sonnet finds bugs/risks per scope → a SECOND Sonnet confirms/refutes
// each candidate → Haiku scores criticality. Returns the confirmed, scored issues; the
// orchestrator (Opus 4.8, in the main session) reconciles them and fixes the plan.
//
// args:
//   plan    string  — the implementation plan text (required unless scopes are supplied)
//   scopes  [{key, focus}]?  — optional; skip the splitter when the orchestrator pre-split
//
// returns: { issues: [{title, detail, where, scope, verdict, criticality, justification}],
//            counts: { scopes, found, confirmed } }

export const meta = {
  name: 'plan-deep-review',
  description: 'Scope-split plan review: split the plan, Sonnet finds bugs/risks per scope, a second Sonnet confirms/refutes each, Haiku scores criticality. Returns confirmed, scored issues for the orchestrator to fix.',
  phases: [
    { title: 'Split', detail: 'split the plan into independent review scopes' },
    { title: 'Find', detail: 'one Sonnet 5 agent per scope hunts bugs/risks' },
    { title: 'Verify', detail: 'a second Sonnet 5 agent confirms/refutes each candidate' },
    { title: 'Score', detail: 'Haiku scores criticality of survivors' },
  ],
}

const SCOPES = {
  type: 'object',
  properties: {
    scopes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string', description: 'short scope name' },
          focus: { type: 'string', description: 'what a reviewer should scrutinize in this scope' },
        },
        required: ['key', 'focus'],
      },
    },
  },
  required: ['scopes'],
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

// RULE ZERO — this phase reviews a PLAN, before any code exists. Every agent below is read-only.
// The rule is appended to each prompt because a review agent that holds an Edit tool and finds a
// real bug will fix the bug unless told not to — and a fix made here belongs to no task in the
// Phase-6 graph, so no builder owns it and no reviewer reviews it. Findings only; the orchestrator
// amends the plan. Keep this text in sync with references/rule-zero-no-code.md.
const RULE_ZERO = `

## RULE ZERO — DO NOT WRITE CODE (absolute, overrides every other instruction you are given)

You are working in the PLANNING stage of a pipeline. Implementation happens later, in a separate
phase, performed by different agents against a reviewed task graph. It is not your job and you
must not start it.

You MUST NOT create, modify, or delete any product file: source, tests, fixtures, config, schemas,
migrations, build files, lockfiles, or generated artifacts. No patches, no codemods, no \`--fix\`
runs, no commits. This holds regardless of what mode you are in, what tools you have, how trivial
the change looks, or how confident you are that it is correct.

You MAY: read any file, search the codebase, and run read-only commands (including the existing
tests/typecheck/build) to gather evidence about how the system behaves today.

If you conclude that code must change, that is a FINDING, not a task: describe the change — file,
what, why — in your structured output, and return. Do not make it.`

const plan = (args && args.plan) || ''
let scopes = (args && args.scopes) || []

if (!plan && !scopes.length) {
  return { issues: [], counts: { scopes: 0, found: 0, confirmed: 0 }, error: 'pass args.plan (and/or args.scopes)' }
}

// 1. Scopes — use what the orchestrator passed, else derive them from the plan.
if (!scopes.length) {
  phase('Split')
  const split = await agent(
    `Split this implementation plan into INDEPENDENT review scopes — by component, ` +
    `step-cluster, or risk area — as many (or few) as the plan naturally warrants; don't pad ` +
    `to a target count. For each scope give a short \`key\` and a one-line \`focus\` naming ` +
    `what a reviewer should scrutinize there.\n\nPlan:\n${plan}\n${RULE_ZERO}`,
    { label: 'split', phase: 'Split', model: 'sonnet', effort: 'medium', schema: SCOPES },
  )
  scopes = (split && split.scopes) || []
}
if (!scopes.length) return { issues: [], counts: { scopes: 0, found: 0, confirmed: 0 } }

// 2. Find → 3. Verify, pipelined per scope (a scope's findings verify as soon as they're found).
const reviewed = await pipeline(
  scopes,
  (s) => agent(
    `Review this implementation plan, focusing on the "${s.key}" scope: ${s.focus}\n\n` +
    `Find bugs, risks, and gaps that would cause an incorrect or incomplete implementation. ` +
    `Be concrete — point at the specific plan step or component. If the scope is sound, return ` +
    `an empty findings list.\n\nPlan:\n${plan}\n${RULE_ZERO}`,
    { label: `find:${s.key}`, phase: 'Find', model: 'sonnet', effort: 'high', schema: FIND },
  ),
  (review, s) => parallel(
    ((review && review.findings) || []).map((f) => () =>
      agent(
        `Independently CONFIRM or REFUTE this candidate issue against the plan. Default to ` +
        `"refuted" if you cannot substantiate it from the plan text — an issue nobody can ` +
        `confirm should not drive a plan change.\n\nCandidate: ${JSON.stringify(f)}\n\n` +
        `Plan:\n${plan}\n${RULE_ZERO}`,
        { label: `verify:${s.key}`, phase: 'Verify', model: 'sonnet', effort: 'high', schema: VERDICT },
      ).then((v) => ({ ...f, scope: s.key, verdict: v })),
    ),
  ),
)

const all = reviewed.flat().filter(Boolean)
const confirmed = all.filter((x) => x.verdict && x.verdict.status === 'confirmed')

// 4. Score the survivors. agent() returns null if a scorer dies or is skipped — dereferencing that
// would throw inside the promise, reject the whole parallel(), and discard every confirmed issue the
// expensive Find/Verify stages just produced. A dead scorer costs its issue a criticality label, not
// the run: fall back to 'major' so the issue still reaches the orchestrator, and say the label is
// unscored rather than pretending it was triaged.
const issues = (await parallel(
  confirmed.map((c) => () =>
    agent(
      `Score the criticality of this CONFIRMED plan issue as critical, major, or minor, with a ` +
      `one-line justification.\n\n` +
      JSON.stringify({ title: c.title, detail: c.detail, where: c.where, scope: c.scope }) +
      `\n${RULE_ZERO}`,
      { label: `score:${c.scope}`, phase: 'Score', model: 'haiku', effort: 'low', schema: SCORE },
    ).then((sc) => ({
      ...c,
      criticality: (sc && sc.level) || 'major',
      justification: (sc && sc.justification) || 'scorer returned no result — defaulted to major, triage this one yourself',
    })),
  ),
)).filter(Boolean)

log(`deep-review: ${scopes.length} scopes, ${all.length} candidates, ${confirmed.length} confirmed, ${issues.length} scored`)
return { issues, counts: { scopes: scopes.length, found: all.length, confirmed: confirmed.length } }
