# Phase 10 — FIX REVIEW FINDINGS

Address every finding, push the fixes, re-review until clean. This is the phase where a pipeline
quietly fails: it's tempting to fix the easy findings, wave at the hard one, and call the PR done.
The loop is what stops that.

## The loop

1. **Fix every finding.** Critical/major are blocking. Minor/nice-to-have don't block, but decide
   each one consciously — fix it, or carry it to the handoff notes. Neither "fixed everything" nor
   "deferred everything" should be the default; the choice per finding is the work.
2. **Re-verify.** Re-run **Phase 7's** build/test/lint after each fix round. A review nit fixed in
   haste is a classic way to break a build you already proved green.
3. **Push the fixes.** Pushing more commits to your *own already-open* PR branch is fine without a
   fresh prompt — the outward-facing decision was made at Phase 6's finishing gate.
4. **Re-review.** Run the reviewer again on the updated PR/diff.
5. **Repeat until a clean pass** — no critical/major findings (loop-until-clean, SKILL Operating
   rules).

## Where fixes go

**A fix that changes real behaviour goes back through Phase 6 → 7, not straight to a push.** The
size of the fix decides the shape:

- **Small and local** (a naming fix, a guard clause, a missed null check) → fix it inline as the
  orchestrator, re-verify, push. No subagent loop needed for a one-liner.
- **Substantial** (a finding that invalidates a task's approach, or spans several tasks) → treat it
  as implementation work: re-open **Phase 6**, and run the fix through its implementer → reviewer
  loop the same way the original task was
  built. Don't hand-roll a large change outside the discipline you built precisely to keep large
  changes honest — a hand-patched fix arrives with none of it.
- **A finding that says the plan was wrong** → back to **Phase 2**, and through hardening again.
  Rare at this point (that's what Phases 3–5 were for), but if it happens, the plan is the thing to
  fix, not the symptom.

Re-open the todos you go back to; don't leave them falsely complete.

## Disagreeing with a finding

Use `superpowers:receiving-code-review` if available. Verify the claim against the code before
acting on it — implementing a reviewer's suggestion you don't understand is how a correct change
becomes a broken one. If you conclude the finding is wrong, **say so with your reasoning** rather
than silently skipping it, and carry the disagreement to the handoff so the human can adjudicate.

## Outward-facing: posting replies

Pushing fix commits to your own PR branch is fine. **Posting comment replies on the PR is
outward-facing** — confirm before posting, unless the human pre-authorized hands-off completion.

## When it won't converge

If the loop plateaus — a round adds no real improvement, or the same findings keep coming back —
**stop and surface what's left**, with what you tried. Don't grind, and don't declare a PR
merge-ready that you know is dirty. A PR that arrives with "here are the two findings I couldn't
resolve, and why" is far more useful than one that arrives claiming to be clean.

**Exit:** a review pass with no critical/major findings (or a plateau reached + surfaced).

**Exit receipt example:**
`✅ Phase 10 (FIX FINDINGS) — 2 rounds: 1 critical + 2 major fixed, re-verified (142 passed), re-reviewed clean — 2 minor carried to handoff`
