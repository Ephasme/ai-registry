# Phase 5 — DEEP REVIEW (conditional)

A multi-agent pass over the plan, run **only** when the trigger fires. By then the plan has shown
it's error-prone, and a find→verify→score→reconcile fan-out catches what a single linear review
misses — while the independent verifier keeps plausible-but-wrong findings from surviving.

The script is **pre-written and bundled** at `scripts/deep-review.workflow.mjs` — don't reassemble
it inline; run the file.

**Every agent in this fan-out is read-only.** They review a *plan*, and Rule Zero
([`rule-zero-no-code.md`](rule-zero-no-code.md)) forbids them touching code — the bundled script
carries the rule block in each of its prompts. On the fallback path below you must paste it in
yourself: a review subagent with an Edit tool and a confirmed bug in front of it will fix the bug
unless you tell it not to. Its output is findings; the plan is the only thing that changes, and
you change it.

## The trigger — run it, or skip it out loud

- **RUN IF** Phases 3–4 **kept surfacing serious problems** — a steady stream of critical/major
  findings across rounds, saying the plan is genuinely error-prone rather than one-off sloppy —
  **OR** the human asks for a deep review.
- **ELSE SKIP** straight to Phase 6, and say so in the receipt *with the reason*, e.g.
  `✅ Phase 5 (DEEP REVIEW) — skipped: phases 3–4 surfaced no serious findings`. The skip is
  sanctioned; hiding it is not.

## The design (and why each stage)

1. **Split into scopes.** Break the plan into independent review units — by component, step
   cluster, or risk area — as many as the plan naturally has (no target count). Independent
   scopes let reviewers go deep without holding the whole plan in context, and parallelize
   cleanly. The bundled script does this itself unless you hand it scopes.
2. **Find (Sonnet 5, one per scope).** Each agent hunts bugs/risks/gaps in its scope only.
   Sonnet is fast and strong here; the orchestrator model isn't needed to *find*.
3. **Verify (Sonnet 5, one per candidate).** A *second, independent* agent tries to **confirm or
   refute** each candidate against the plan. This is the load-bearing stage — a finding nobody can
   independently confirm shouldn't drive a plan change.
4. **Score (Haiku, one per survivor).** Cheap criticality triage: `critical | major | minor` with a
   one-line justification. Haiku is plenty for a bounded classification.
5. **Reconcile & fix (you, Opus 4.8, in the main session).** The workflow returns the confirmed,
   scored issues; *you* dedupe them, decide what each means for the plan, and edit the plan to
   resolve every confirmed critical/major issue. Reconciliation is judgment work — keep it with the
   orchestrator, not a sub-agent.

Find→Verify run as a **pipeline** so each scope's findings flow to verification as soon as they're
found, rather than waiting on the slowest finder.

## Running it

Hand it the plan text; it splits scopes itself:

```
Workflow({
  scriptPath: "${CLAUDE_PLUGIN_ROOT}/skills/ticket-to-pr/scripts/deep-review.workflow.mjs",
  args: { plan: "<the full plan text>" }
})
```

If you've already split the plan, pass `args.scopes` as `[{ key, focus }]` to skip the splitter
(`plan` is still used by the find/verify stages).

**Cost guard.** This run fans out to roughly one finder per scope, plus a verifier and a scorer per
candidate finding — count that up and apply the **fan-out cost guard** (SKILL Operating rules)
before launching.

## What it returns, and reconciliation

```
{ issues: [ { title, detail, where, scope, verdict, criticality, justification } ],
  counts: { scopes, found, confirmed } }
```

After it returns: dedupe overlaps across scopes, then **fix every confirmed critical/major issue in
the plan**; carry minors to the handoff. Report the `counts` so the human sees how much was found
vs. confirmed. The per-stage output schemas (`SCOPES`, `FIND`, `VERDICT`, `SCORE`) are defined
inside the script.

## Fallback (no Workflow tool)

If the Workflow tool / multi-agent orchestration isn't available, don't skip the scrutiny —
approximate it sequentially: split the plan into scopes and, for each, dispatch a single review
**subagent** (via the Agent tool — `Explore` or a general agent) to find issues; then for each
non-trivial finding, dispatch a second subagent to confirm/refute; reconcile and fix the confirmed
ones yourself. Slower and less parallel, but it preserves the find→verify→reconcile discipline that
makes this phase worth running. Say you used the fallback.

**Exit:** a reconciled plan with every *confirmed* issue fixed — or an explicit, justified skip.

**Exit receipt example:**
`✅ Phase 5 (DEEP REVIEW) — ran deep-review.workflow.mjs (6 scopes, 14 candidates, 5 confirmed) — 2 critical + 3 major fixed in the plan`
