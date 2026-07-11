// @ts-nocheck — Workflow DSL script: agent()/pipeline()/parallel()/phase()/log()/args are
// injected by the Workflow runtime, which also wraps the body so top-level await/return work.
// It is NOT a standalone ES module, so normal TS/JS module checking misreports it.
//
// Phase-7 implement — runs a ticket-to-pr task graph WAVE BY WAVE.
//
//   Workflow({
//     scriptPath: "${CLAUDE_PLUGIN_ROOT}/skills/ticket-to-pr/scripts/implement-waves.workflow.mjs",
//     args: {
//       graph: { tasks: [...], waves: [["T1"], ["T2","T3"], ["T4"]] },
//       gateCommand: "pnpm typecheck && pnpm build",
//       scriptsDir: "<CLAUDE_PLUGIN_ROOT>/skills/ticket-to-pr/scripts",
//       worktreeSetup: "ln -s ../../../node_modules node_modules",   // provision ignored build deps
//       constraints: "<binding requirements, verbatim from the plan>"
//     }
//   })
//
// PER WAVE:
//   setup  — create one git worktree per task, detached at the wave's base commit (serial: one
//            agent, so concurrent `git worktree add` never races)
//   tasks  — in parallel, each: builder → task reviewer (spec + quality) → [fixer → re-review]*
//   gate   — serial: integrate every task's commits into the main tree, verify, ledger, tear down
//
// WHY A WORKTREE PER TASK. Disjoint write-sets (Phase 6) stop two builders from WRITING the same
// file — but not task B from READING a file task A is midway through rewriting. In one shared
// tree, B's own verify command can fail (or pass) against a torn state that has nothing to do with
// B, and B's reviewer can see A's unreviewed work. Isolation removes that class of ghost entirely:
// each builder sees only the wave's base commit plus its own work.
//
// It also buys back committing. A worktree has its OWN index and HEAD, so builders commit freely
// in parallel — no index.lock race, nothing shared but the content-addressed object database. That
// gives each reviewer a real BASE..HEAD commit range instead of a reconstructed diff.
//
// And integration stays conflict-free: because the write-sets are disjoint, cherry-picking the
// waves' worktrees back into the main tree cannot conflict. The disjointness invariant does the
// same work as before — it has simply moved from "makes shared editing safe" to "makes the N-way
// merge trivial". If a cherry-pick DOES conflict, that is a Phase-6 footprint bug, and it halts.
//
// args:
//   graph          { tasks: [{id, title, brief, briefPath, reads, provides, writes, verify,
//                             builderModel, builderEffort, reviewerModel, reviewerEffort}],
//                    waves: [[taskId, ...], ...] }                             — required
//   gateCommand    string?  — build/typecheck at the wave boundary (light gate, not the full suite)
//   scriptsDir     string?  — where wave-review-package lives; reviewers fall back to raw git
//   worktreeSetup  string?  — command run inside each fresh worktree to provision gitignored build
//                             deps (node_modules, .venv, target/). Without it, tests cannot run.
//   isolation      'worktree' | 'shared'  — default 'worktree'. 'shared' skips worktrees for
//                             projects too expensive to provision; per-task verify then becomes
//                             best-effort and the wave gate is the real check.
//   constraints    string?  — binding requirements from the plan, handed to every reviewer
//   planPath       string?  — scene-setting only; the brief is the source of requirements
//
// returns: { halted, haltedAtWave, reason, waves:[{wave,tasks,gate}], completed, blocked, minors }

export const meta = {
  name: 'implement-waves',
  description: 'Execute a task graph wave by wave: a git worktree per task, a builder then an independent reviewer (spec + quality) with a fix/re-review loop, those chains parallel within a wave; then a gate that integrates, verifies and commits the wave. Halts rather than pushing broken work downstream.',
  phases: [
    { title: 'Setup', detail: 'one isolated git worktree per task in the wave' },
    { title: 'Build', detail: 'one builder agent per task, parallel within the wave' },
    { title: 'Review', detail: 'an independent reviewer per task: spec compliance + code quality' },
    { title: 'Fix', detail: 'one fixer per task carrying the full findings list, then re-review' },
    { title: 'Gate', detail: 'integrate the wave into the main tree, verify, commit, tear down' },
  ],
}

const BUILD_RESULT = {
  type: 'object',
  properties: {
    status: {
      type: 'string',
      enum: ['DONE', 'DONE_WITH_CONCERNS', 'BLOCKED', 'NEEDS_CONTEXT', 'NEEDS_OUT_OF_SCOPE_WRITE'],
    },
    summary: { type: 'string', description: 'what you changed, 1-3 sentences' },
    commits: { type: 'array', items: { type: 'string' }, description: 'short SHA + subject, made IN YOUR WORKTREE' },
    testSummary: { type: 'string', description: 'one line, e.g. "14/14 passing, output pristine"' },
    concerns: { type: 'string' },
    problem: { type: 'string', description: 'if BLOCKED / NEEDS_CONTEXT / NEEDS_OUT_OF_SCOPE_WRITE: what exactly, and what you tried' },
  },
  required: ['status', 'summary'],
}

const REVIEW_RESULT = {
  type: 'object',
  properties: {
    specCompliance: { type: 'string', enum: ['compliant', 'issues'] },
    specIssues: { type: 'array', items: { type: 'string' }, description: 'missing / extra / misunderstood, with file:line' },
    cannotVerify: { type: 'array', items: { type: 'string' }, description: 'items the orchestrator must resolve — it holds the cross-task context' },
    strengths: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['Critical', 'Important', 'Minor'] },
          where: { type: 'string', description: 'file:line' },
          what: { type: 'string' },
          why: { type: 'string' },
          fix: { type: 'string' },
          planMandated: { type: 'boolean', description: 'true if the plan/brief explicitly mandates this defect' },
        },
        required: ['severity', 'what'],
      },
    },
    quality: { type: 'string', enum: ['approved', 'needs-fixes'] },
    reasoning: { type: 'string' },
  },
  required: ['specCompliance', 'quality'],
}

const SETUP_RESULT = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['ok', 'failed'] },
    base: { type: 'string', description: 'the wave base commit SHA every worktree is detached at' },
    worktrees: {
      type: 'array',
      items: {
        type: 'object',
        properties: { id: { type: 'string' }, path: { type: 'string' } },
        required: ['id', 'path'],
      },
    },
    problem: { type: 'string' },
  },
  required: ['status'],
}

const GATE_RESULT = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['pass', 'fail'] },
    command: { type: 'string' },
    output: { type: 'string', description: 'the real output — errors verbatim if it failed' },
    diagnosis: {
      type: 'string',
      description: 'if failed: which task it is attributable to; "integration" if each task passes alone but they break together; "footprint" if a cherry-pick conflicted (a Phase-6 bug)',
    },
    commits: { type: 'array', items: { type: 'string' }, description: 'short SHA + subject, as integrated into the main branch' },
  },
  required: ['status', 'command', 'output'],
}

const graph = (args && args.graph) || {}
const tasks = graph.tasks || []
const waves = graph.waves || []
const gateCommand = (args && args.gateCommand) || ''
const scriptsDir = (args && args.scriptsDir) || ''
const worktreeSetup = (args && args.worktreeSetup) || ''
const isolation = (args && args.isolation) || 'worktree'
const constraints = (args && args.constraints) || '(none supplied)'
const planPath = (args && args.planPath) || ''

if (!tasks.length || !waves.length) {
  return { halted: true, reason: 'pass args.graph = { tasks: [...], waves: [[ids]] }', waves: [], completed: [], blocked: [], minors: [] }
}

const byId = {}
for (const t of tasks) byId[t.id] = t

const list = (v) => (Array.isArray(v) ? v.join(', ') : v || '—')
const lines = (v) => (Array.isArray(v) ? v : [v]).filter(Boolean).map((x) => `  - ${x}`).join('\n')

// An omitted model inherits the orchestrator's (Opus 4.8); an omitted effort inherits the session's
// (xhigh). Either one silently makes a cheap swarm expensive — so both always resolve to something.
const bModel = (t) => t.builderModel || 'sonnet'
const bEffort = (t) => t.builderEffort || 'medium'
const rModel = (t) => t.reviewerModel || 'sonnet'
const rEffort = (t) => t.reviewerEffort || 'high'
const escalate = (m) => (m === 'haiku' ? 'sonnet' : 'opus')   // one tier up, for a retry that must not repeat itself

const wtPath = (t) => `.ticket-to-pr/wt/${t.id}`

const setupPrompt = (waveNo, waveTasks) => [
  `Prepare isolated workspaces for wave W${waveNo} of a parallel implementation run.`,
  `\nWork from the MAIN repository root. Do this serially, in order — concurrent \`git worktree add\``,
  `calls can race, which is exactly why one agent does all of them.`,
  `\n## 1. Record the wave base`,
  `\nRun \`git rev-parse HEAD\` and return it as "base". Every worktree below detaches at it, and the`,
  `reviewers diff against it. It already contains every previous wave's committed work.`,
  `\n## 2. Create one worktree per task`,
  waveTasks.map((t) => `  git worktree add --detach ${wtPath(t)} HEAD    # ${t.id}`).join('\n'),
  worktreeSetup
    ? `\n## 3. Provision each worktree\n\nA fresh worktree has no gitignored build dependencies (node_modules, .venv, target/), so tests\ncannot run in it until you provision them. In EACH worktree directory, run:\n\n    ${worktreeSetup}\n\nIf that command fails in any worktree, return status "failed" and say which — a builder that\ncannot run its tests is worse than no builder.`
    : `\n## 3. Provision each worktree\n\nNo setup command was supplied. Check whether the project needs gitignored build dependencies\n(node_modules, .venv, target/) to run its tests. If it does, provision them in each worktree the\ncheapest correct way for this project (symlinking the main tree's node_modules is usually enough;\nan install per worktree is the fallback). If you cannot, return status "failed" and say so rather\nthan handing builders a tree whose tests cannot run.`,
  `\n## Report`,
  `\nReturn the base SHA and the id→path mapping for every worktree you created.`,
].join('\n')

const builderPrompt = (t, waveNo, worktree, priorFailure) => [
  `You are implementing exactly one atomic task from an approved, hardened implementation plan.`,
  `Other agents are implementing other tasks of the same plan, in parallel, right now — each in its`,
  `own isolated worktree. You cannot see their work, and they cannot see yours. That is deliberate.`,
  `\n## Work from your worktree`,
  `\n    ${worktree}`,
  `\nEvery command you run and every file you touch is inside that directory. It is a full checkout of`,
  `the repository at this wave's base commit, with all previous waves' work already in it.`,
  `\n## Your task — ${t.id}: ${t.title}`,
  t.briefPath ? `\nRead your brief first — it is your requirements, and its exact values (names, signatures, numbers,\nformats) are to be used verbatim:\n  ${t.briefPath}` : '',
  t.brief ? `\n${t.brief}` : '',
  `\nWhere this fits: wave ${waveNo} of the task graph.${planPath ? ` Plan: ${planPath}.` : ''}`,
  `\n- You depend on / read: ${list(t.reads)}`,
  `- You must provide (downstream tasks consume this — honour the contract exactly): ${list(t.provides)}`,
  `\n## HARD CONSTRAINT — your write-set`,
  `\nYou may create or modify ONLY these files:\n${lines(t.writes) || '  (none declared — stop and report)'}`,
  `\nYour worktree protects other agents from your edits, but the write-set is still binding: it is the`,
  `contract the task graph scheduled this wave on, and the wave's changes are merged back together`,
  `afterwards. Editing outside it will collide at integration. If you cannot complete the task without`,
  `editing a file outside the list, DO NOT edit it — return NEEDS_OUT_OF_SCOPE_WRITE naming the file`,
  `and why. That means the task graph is wrong, and the orchestrator will fix the graph rather than`,
  `let you widen your footprint.`,
  `\n## How to work`,
  `\n1. Write the test first: make it fail, and confirm it fails for the reason you expect.`,
  `2. Implement the minimum that makes it pass.`,
  `3. Run your verify command: ${t.verify || '(the project build/typecheck)'}`,
  `4. Self-review, and fix what you find.`,
  `5. COMMIT your work, in your worktree. Message in the repo's existing style (check \`git log\`):`,
  `   what changed and why. Commit only your write-set — never \`git add -A\`.`,
  `\nWhile iterating, run the focused test for what you're changing — not the whole suite.`,
  `\n- Match the surrounding code's existing style, structure, and idioms.`,
  `- Keep the change scoped to this task. No drive-by refactors, no unrelated cleanups.`,
  `- Build exactly what the brief specifies — nothing extra. An unrequested flag or "nice to have" is`,
  `  a defect: the reviewer will flag it as spec non-compliance and send it back.`,
  `\n## Self-review before reporting`,
  `\n- Completeness: everything in the brief? any requirement missed? edge cases?`,
  `- Quality: is this my best work? do names say what things do?`,
  `- Discipline: did I avoid overbuilding? did I only build what was asked? did I follow existing patterns?`,
  `- Testing: do the tests verify real behaviour, not mocks? did I write the test first? is the test`,
  `  output pristine — no stray warnings or noise?`,
  `\n## In over your head?`,
  `\nIt is always OK to stop and say "this is too hard." Bad work is worse than no work, and you will not`,
  `be penalized for escalating. You have no interactive channel — you cannot ask and wait. If you need`,
  `information you weren't given, return NEEDS_CONTEXT naming exactly what's missing.`,
  `\n## Report`,
  `\nWrite your full report to \`.ticket-to-pr/${t.id}-report.md\` (in the MAIN repo, not your worktree —`,
  `the worktrees are torn down, the report has to outlive them): what you implemented, what you tested`,
  `and the results, TDD evidence (the RED command + failing output and why that failure was expected,`,
  `then the GREEN command + passing output), files changed, self-review findings, concerns.`,
  `\nThen return only the structured result, including the commits you made. Return DONE only if your`,
  `verify command really passed. **A false DONE is worse than a failure** — the next wave builds on it.`,
  priorFailure ? `\n## THIS IS A RETRY — the previous attempt failed with:\n${priorFailure}\n\nDiagnose why before you start. Do not simply repeat the same approach.` : '',
].filter(Boolean).join('\n')

const reviewerPrompt = (t, worktree, base) => [
  `You are reviewing one task's implementation: first whether it matches its requirements, then`,
  `whether it is well-built. This is a task-scoped gate, not a merge review — a broad review of the`,
  `whole change happens separately, later.`,
  `\nThe task was built in an isolated worktree, so everything you see is this task's work and nothing`,
  `else. No sibling's half-finished edit can be in your diff or your tree.`,
  `\n## What was requested`,
  t.briefPath ? `\nRead the task brief: ${t.briefPath}` : `\nTask ${t.id}: ${t.title}\n${t.brief || ''}`,
  `\nConstraints from the plan that bind this task:\n${constraints}`,
  `\n## What the builder claims it built`,
  `\nRead the builder's report: .ticket-to-pr/${t.id}-report.md`,
  `\n## The diff under review`,
  `\nGenerate it, then read it once:\n`,
  scriptsDir
    ? `    ${scriptsDir}/wave-review-package ${t.id} ${worktree} ${base}\n`
    : `    git -C ${worktree} log --oneline ${base}..HEAD\n    git -C ${worktree} diff -U10 ${base}..HEAD\n`,
  scriptsDir
    ? `That prints a file path. Read that file — the commit list, the stat summary, and the full diff\nwith surrounding context, in one call.`
    : `(no packager available — run those directly)`,
  `\nThe diff's context lines ARE the changed files: do not Read a changed file separately unless a hunk`,
  `you must judge is cut off mid-function, and say so if you do. Do not crawl the broader codebase.`,
  `Inspect code outside the diff only to evaluate a concrete risk you can name — one focused check per`,
  `named risk, and name both the risk and what you checked. A change to a shared contract, to lock`,
  `ordering, or to shared mutable state IS such a risk: checking the call sites is the right method.`,
  `\nYour review is READ-ONLY. Do not mutate the worktree, its index, HEAD, or any branch state.`,
  `\n## Do not trust the report`,
  `\nTreat the builder's report as unverified claims; verify them against the diff. Design rationales are`,
  `claims too — "left it out per YAGNI" is the builder grading its own work. Judge the code on its`,
  `merits; a stated rationale never downgrades a finding's severity.`,
  `\n## Tests`,
  `\nThe builder already ran the tests and reported results for exactly this code. Do not re-run the suite`,
  `to confirm the report. Run a focused test only if reading the code raises a specific doubt that no`,
  `existing run answers. Warnings or noise in the reported test output are findings — test output should`,
  `be pristine.`,
  `\n## Part 1 — spec compliance`,
  `\nMissing (skipped, or claimed but not implemented) / Extra (anything not requested: unneeded flags,`,
  `speculative abstraction, "nice to haves") / Misunderstood (right feature built the wrong way). If a`,
  `requirement cannot be verified from this diff alone — it lives in unchanged code, or spans tasks —`,
  `report it under cannotVerify rather than broadening your search. The orchestrator holds the`,
  `cross-task context you don't, and will resolve it.`,
  `\n## Part 2 — code quality`,
  `\nCode (separation of concerns, error handling, DRY without premature abstraction, edge cases); tests`,
  `(do they verify real behaviour, not mocks? are the task's edge cases covered?); structure (one clear`,
  `responsibility per file; did this change create already-large files, or significantly grow existing`,
  `ones? judge what this change contributed, not pre-existing size).`,
  `\nCite file:line for every finding, and for any check you would otherwise answer with a bare "yes".`,
  `\n## Calibration`,
  `\nNot everything is Critical. Critical = broken, unsafe, or loses data. Important = the task cannot be`,
  `trusted until it is fixed (incorrect or fragile behaviour, a missed requirement, verbatim duplication`,
  `of a logic block, swallowed errors, tests that assert nothing). Minor = polish, taste, "coverage could`,
  `be broader".`,
  `\nIf the brief or plan explicitly mandates something this rubric calls a defect, that IS a finding:`,
  `report it as Important with planMandated=true. The plan does not get to grade its own work.`,
  `\nAcknowledge what was done well before listing issues. Begin with the verdict — no preamble, no process`,
  `narration, no closing summary.`,
].filter(Boolean).join('\n')

const fixerPrompt = (t, worktree, review, round) => [
  `A reviewer found issues in task ${t.id} (${t.title}). Fix ALL of them.`,
  `\n## Work from your worktree\n\n    ${worktree}`,
  t.briefPath ? `\nYour requirements (unchanged): ${t.briefPath}` : `\nTask: ${t.brief || t.title}`,
  `\n## Findings to fix — this is the complete list, address every one`,
  review.specCompliance === 'issues' ? `\n### Spec compliance\n${lines(review.specIssues)}` : '',
  `\n### Code quality\n${(review.findings || [])
    .filter((f) => f.severity === 'Critical' || f.severity === 'Important')
    .map((f) => `  - [${f.severity}${f.planMandated ? ', plan-mandated' : ''}] ${f.where || ''} — ${f.what}${f.fix ? ` → ${f.fix}` : ''}`)
    .join('\n')}`,
  `\n## HARD CONSTRAINT — the same write-set as the original task`,
  `\nYou may modify ONLY:\n${lines(t.writes)}`,
  `\n## After fixing`,
  `\nRe-run the tests covering what you changed: ${t.verify || '(the project build/typecheck)'}`,
  `Commit the fix in your worktree. Then APPEND your fix report — what you changed, the command you`,
  `ran, and its real output — to \`.ticket-to-pr/${t.id}-report.md\` in the MAIN repo. The reviewer will`,
  `not re-run tests for you: your report IS the test evidence, and the re-review will not proceed`,
  `without the covering tests, the command, and its output.`,
  `\nFix the findings as given. If you believe one is wrong, fix the others and say so explicitly in the`,
  `report with your reasoning — do not silently skip it.`,
  round > 1 ? `\n## This is fix round ${round}. The previous round did not satisfy the reviewer — address the substance\nof its findings, not the surface.` : '',
].filter(Boolean).join('\n')

const gatePrompt = (waveNo, waveTasks, base, wts) => [
  `You are the WAVE GATE for wave W${waveNo}. ${waveTasks.length} task(s) built in isolated worktrees and`,
  `each passed its own task review. Your job is to bring them together in the MAIN working tree, prove`,
  `they still work as a whole, and commit them.`,
  `\nWork from the MAIN repository root. Do everything below serially, in the order given, and STOP at the`,
  `first failure — do not carry on to the next step.`,
  `\n## 1. Integrate — cherry-pick each task's commits, in task order`,
  `\nWave base: ${base}`,
  waveTasks.map((t) => `  git cherry-pick ${base}..$(git -C ${wts[t.id]} rev-parse HEAD)    # ${t.id}`).join('\n'),
  `\nThese CANNOT conflict: the task graph proved the tasks' write-sets are disjoint, so no two of them`,
  `touch the same file. If a cherry-pick DOES conflict, that is a footprint bug in the task graph, not`,
  `something for you to resolve: abort the cherry-pick (\`git cherry-pick --abort\`), stop, and report`,
  `status "fail" with diagnosis "footprint", naming the two tasks and the file.`,
  `\n## 2. Verify the wave integrates`,
  gateCommand ? `\nRun the gate: \`${gateCommand}\`` : `\nRun the project's build/typecheck (discover it from package.json / Makefile / justfile / CI config).`,
  `\nThen run the tests these tasks touched:`,
  waveTasks.map((t) => `  - ${t.id}: ${t.verify || '(none declared)'}`).join('\n'),
  `\nThis is a LIGHT gate, not the full suite — build/typecheck plus the touched tests. The full`,
  `build+test+lint runs once, later, in the VERIFY phase. What you are here to catch is a BROKEN`,
  `CONTRACT that dependent waves would otherwise build on top of. Note that each task's own tests`,
  `passed in ISOLATION; this is the first moment they meet, so an integration break is exactly the`,
  `failure this gate exists for.`,
  `\nIf anything fails: STOP. Report status "fail" with the real error output, and say in "diagnosis"`,
  `which task it is attributable to — or "integration" if each task passes alone but they break in`,
  `combination. Leave the cherry-picked commits in place for the orchestrator to inspect; do NOT reset`,
  `or force-fix. Do not tear down the worktrees — they are the evidence.`,
  `\n## 3. Only if everything passed: record and tear down`,
  `\nAppend one line per task to \`.ticket-to-pr/progress.md\` (create it if absent):`,
  `\n    W${waveNo} <task-id>: complete (commit <sha7>, review clean)`,
  `\nThat ledger is the run's durable recovery map — it survives a context compaction that the`,
  `orchestrator's memory will not, and the commits it names exist in git regardless.`,
  `\nThen remove this wave's worktrees:`,
  waveTasks.map((t) => `  git worktree remove ${wts[t.id]}`).join('\n'),
  `\nReturn the commits as they now exist on the main branch.`,
].join('\n')

// ── One task: build → review → (fix → re-review)* ─────────────────────────────────────────────
// The whole chain lives in one thunk, so tasks advance independently across the wave: T2 can be in
// its fix loop while T3 is still building. The only barrier is the wave gate.
const MAX_FIX_ROUNDS = 2

async function runTask(t, waveNo, worktree, base) {
  const P = { build: `W${waveNo} build`, review: `W${waveNo} review`, fix: `W${waveNo} fix` }
  const fail = (why, extra) => ({ id: t.id, title: t.title, status: 'failed', problem: why, worktree, ...extra })

  // 1. Build. Retry once, escalated — never re-run the same model on the same failure unchanged.
  let build = await agent(builderPrompt(t, waveNo, worktree), {
    label: t.id, phase: P.build, model: bModel(t), effort: bEffort(t), schema: BUILD_RESULT,
  })

  if (build && build.status === 'NEEDS_OUT_OF_SCOPE_WRITE') {
    // A graph bug, not a flaky agent. Retrying cannot help — only re-graphing can.
    log(`W${waveNo} ${t.id}: needs out-of-scope write — ${build.problem || ''}`)
    return fail(`needs a write outside its footprint: ${build.problem || ''}`, { status: 'graph-bug', build })
  }
  if (build && build.status === 'NEEDS_CONTEXT') {
    // The swarm cannot invent the missing context; the orchestrator must supply it and re-dispatch.
    log(`W${waveNo} ${t.id}: needs context — ${build.problem || ''}`)
    return fail(`needs context the dispatch didn't carry: ${build.problem || ''}`, { status: 'needs-context', build })
  }

  const ok = (b) => b && (b.status === 'DONE' || b.status === 'DONE_WITH_CONCERNS')
  if (!ok(build)) {
    const why = (build && (build.problem || build.summary)) || 'builder returned no result'
    log(`W${waveNo} ${t.id}: build failed — retrying once on ${escalate(bModel(t))}`)
    build = await agent(builderPrompt(t, waveNo, worktree, why), {
      label: `${t.id} (retry)`, phase: P.build, model: escalate(bModel(t)), effort: 'high', schema: BUILD_RESULT,
    })
    if (!ok(build)) {
      return fail(
        `failed twice.\nattempt 1: ${why}\nattempt 2: ${(build && (build.problem || build.summary)) || 'no result'}`,
        { build },
      )
    }
  }
  if (build.status === 'DONE_WITH_CONCERNS') log(`W${waveNo} ${t.id}: done with concerns — ${build.concerns || ''}`)

  // 2. Review → fix → re-review, until both verdicts come back clean.
  const minors = []
  for (let round = 0; round <= MAX_FIX_ROUNDS; round++) {
    const review = await agent(reviewerPrompt(t, worktree, base), {
      label: round === 0 ? `review:${t.id}` : `review:${t.id} (r${round + 1})`,
      phase: P.review, model: rModel(t), effort: rEffort(t), schema: REVIEW_RESULT,
    })
    if (!review) return fail('reviewer returned no result', { build })

    for (const f of review.findings || []) if (f.severity === 'Minor') minors.push({ task: t.id, ...f })

    const blocking = (review.findings || []).filter((f) => f.severity === 'Critical' || f.severity === 'Important')
    const clean = review.specCompliance === 'compliant' && review.quality === 'approved' && !blocking.length

    if (clean) {
      return {
        id: t.id, title: t.title, status: 'done', worktree, build, review, minors,
        fixRounds: round, cannotVerify: review.cannotVerify || [],
      }
    }
    if (round === MAX_FIX_ROUNDS) {
      return fail(
        `review did not converge after ${MAX_FIX_ROUNDS} fix round(s). Outstanding: ` +
        `${review.specCompliance === 'issues' ? `spec — ${(review.specIssues || []).join('; ')}. ` : ''}` +
        blocking.map((f) => `[${f.severity}] ${f.where || ''} ${f.what}`).join('; '),
        { build, review, minors },
      )
    }

    // ONE fixer with the COMPLETE findings list — never one fixer per finding. Per-finding fixers
    // each rebuild context and re-run suites, and cost more than the tasks they are fixing.
    log(`W${waveNo} ${t.id}: review round ${round + 1} — ${blocking.length} blocking finding(s), dispatching fixer`)
    const fix = await agent(fixerPrompt(t, worktree, review, round + 1), {
      label: `fix:${t.id} (r${round + 1})`,
      phase: P.fix,
      model: round === 0 ? bModel(t) : escalate(bModel(t)),
      effort: round === 0 ? 'high' : 'xhigh',
      schema: BUILD_RESULT,
    })
    if (!fix || fix.status === 'BLOCKED') {
      return fail(`fixer could not resolve the review findings: ${(fix && fix.problem) || 'no result'}`, { build, review, minors })
    }
  }
}

// ── The wave loop ─────────────────────────────────────────────────────────────────────────────
const waveReports = []
const completed = []
const allMinors = []

for (let i = 0; i < waves.length; i++) {
  const waveNo = i + 1
  const waveTasks = (waves[i] || []).map((id) => byId[id]).filter(Boolean)
  if (!waveTasks.length) continue

  const stop = (reason, extra) => {
    // A failed task blocks its dependents, and every later wave depends transitively on this one — so
    // nothing further starts. This is the whole point: no work is pushed downstream onto a foundation
    // that isn't there. The worktrees are deliberately left in place as evidence.
    const blocked = waves.slice(i + 1).flat()
    log(`W${waveNo}: HALT (${reason}) — ${blocked.length} downstream task(s) blocked`)
    return { halted: true, haltedAtWave: waveNo, reason, waves: waveReports, completed, blocked, minors: allMinors, ...extra }
  }

  // Setup: one agent, serially creating the worktrees — concurrent `git worktree add` can race.
  let base = ''
  const wts = {}
  if (isolation === 'worktree') {
    phase(`W${waveNo} setup`)
    const setup = await agent(setupPrompt(waveNo, waveTasks), {
      label: `setup:W${waveNo}`, phase: `W${waveNo} setup`, model: 'sonnet', effort: 'low', schema: SETUP_RESULT,
    })
    if (!setup || setup.status !== 'ok' || !setup.base) {
      waveReports.push({ wave: waveNo, tasks: [], gate: null, setup })
      return stop('setup-failed', { setup })
    }
    base = setup.base
    for (const w of setup.worktrees || []) wts[w.id] = w.path
    for (const t of waveTasks) if (!wts[t.id]) wts[t.id] = wtPath(t)
  } else {
    // Shared-tree mode: no isolation. Per-task verification becomes best-effort (a builder may
    // observe a sibling's mid-edit state) and the wave gate is the real check. Only choose this
    // when provisioning a worktree per task is genuinely too expensive for the project.
    log(`W${waveNo}: shared-tree mode — no per-task isolation`)
    for (const t of waveTasks) wts[t.id] = '.'
  }

  phase(`W${waveNo} build`)
  log(`W${waveNo}: ${waveTasks.length} task(s) in parallel — ${waveTasks.map((t) => t.id).join(', ')}`)

  const results = (await parallel(waveTasks.map((t) => () => runTask(t, waveNo, wts[t.id], base)))).filter(Boolean)
  for (const r of results) allMinors.push(...(r.minors || []))

  const failed = results.filter((r) => r.status !== 'done')
  if (failed.length) {
    waveReports.push({ wave: waveNo, tasks: results, gate: null })
    return stop('task-failed', { failed })
  }

  phase(`W${waveNo} gate`)
  const gate = await agent(gatePrompt(waveNo, waveTasks, base, wts), {
    label: `gate:W${waveNo}`, phase: `W${waveNo} gate`, model: 'sonnet', effort: 'medium', schema: GATE_RESULT,
  })
  waveReports.push({ wave: waveNo, tasks: results, gate })

  if (!gate || gate.status !== 'pass') return stop('gate-failed', { gate })

  completed.push(...results.map((r) => r.id))
  log(`W${waveNo}: ${results.length} task(s) built, reviewed, integrated & committed; gate green`)
}

log(`implement-waves: ${completed.length} task(s) across ${waveReports.length} wave(s), all reviews clean, all gates green`)
return { halted: false, waves: waveReports, completed, blocked: [], minors: allMinors }
