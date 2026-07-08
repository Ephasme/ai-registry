---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "[--output=pack|file|chat] [--send=<target>] [--move] What will the next session be used for?"
disable-model-invocation: true
---

# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead — that keeps the handoff short and avoids drift from the source of truth.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed additional arguments beyond the `--output`/`--send`/`--move` flags, treat them as a description of what the next session will focus on and tailor the doc accordingly.

## Output modes

Pass `--output=<mode>` to choose where the handoff goes. Default: `chat`.

- `chat` (default) — output the document directly in the chat response. It's meant to be read or copied right away, not hunted for on disk.
- `file` — save the document to a single markdown file in the temporary directory of the user's OS (not the current workspace), named meaningfully with today's date, e.g. `handoff-<topic>-YYYY-MM-DD.md`. Dependencies stay referenced by path/URL, same as `chat`.
- `pack` — bundle the handoff document together with copies of everything it depends on into one self-contained `.tar.gz`, so the result is still usable after moving to a machine that has no access to the original paths or URLs (a fresh clone, a different laptop, a different session).

## Building a pack

1. Create a staging directory in the OS temp dir, e.g. `handoff-<topic>-YYYY-MM-DD/`.
2. Identify what the handoff depends on, and for each one decide whether it can be bundled or must stay a live reference:
   - The current conversation transcript, if one is accessible on disk — bundle it.
   - Plan documents (e.g. from `superpowers:writing-plans`) relevant to the handed-off work — bundle them.
   - Temporary/scratch files created during the session that the next agent would need (e.g. anything under the session's scratchpad directory) — bundle them.
   - Other local files the handoff depends on (PRDs, ADRs, notes) — bundle only what's referenced, not the whole repo.
   - Remote dependencies (a GitHub issue/PR, a Linear ticket, a Notion doc) — fetch their current content and bundle it as a snapshot file (markdown or JSON) when feasible; that's what makes the pack usable without network/credential access on the other end. If a snapshot isn't feasible, it stays a URL reference.
   Copy each bundled item into the staging directory, preserving enough relative structure to stay unambiguous.
3. Write `handoff.md` directly into the staging directory: reference bundled items by their relative path inside the pack, and unbundled ones by URL with a note that it's a live reference, not a copy. There's no separate "write it plainly, then rewrite the links" pass — you already know each dependency's fate from step 2, so write the real path the first time.
4. Archive and clean up: `scripts/pack.py <staging-dir>` tars the staging directory into the OS temp dir as `<staging-dir-name>.tar.gz`, removes the staging directory, and prints the archive path. Prefer it over re-deriving the tar/cleanup by hand:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/pack.py" <staging-dir>
   ```
5. Tell the user the resulting archive path.

## Sending a pack

Pass `--send=<target>` (e.g. `--send=user@host`) to copy the finished archive to the remote machine after building it. This only makes sense for `--output=pack` — a bare markdown file (`file`) or chat output (`chat`) isn't something you `rsync`/`scp` anywhere. If `--send` is passed with `file`/`chat`, or with no `--output` (which defaults to `chat`), stop and tell the user `--send` requires `--output=pack` rather than silently ignoring it or guessing they meant something else.

`scripts/send.py <archive> <target>` copies the archive into a fresh, private directory on the remote created via `mktemp -d` — deliberately not the shared, world-writable `/tmp` directly, since another local user on that host could otherwise pre-plant a file or symlink at a predictable path. It prefers `rsync` and retries with `scp` whenever the first attempt fails for any reason (not just when `rsync` is locally absent — it also covers the remote lacking `rsync`), and propagates the final attempt's exit status so a failure (bad host, auth failure, no space) surfaces rather than getting glossed over:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/send.py" <archive> <target>
```

This assumes a Unix-like remote (it needs `mktemp`, `ssh`, and `rsync`/`scp`); if the target's OS is unclear, ask rather than guessing. On success it prints `<target>:<remote-dir>/<archive-name>` — treat that path as opaque and pass it through verbatim to whatever comes next (e.g. `unpack_remote.py` below); don't assume it's under `/tmp`. Tell the user that remote path, in addition to the local archive path from step 5 above.

## Moving a pack

Pass `--move` together with `--send=<target>` to go one step further: instead of leaving the archive sitting in its private remote temp directory, unpack it directly into the identical project on that machine (same project name as the current one, e.g. being in `sherpas-api` locally and running `--output=pack --send=nas --move` unpacks into `sherpas-api` on `nas`). `--move` only makes sense together with `--send` (which in turn requires `--output=pack`, per above) — if `--move` is passed without `--send`, stop and tell the user rather than guessing which target they meant.

Resolving *where* to unpack doesn't depend on the pack itself, so do it first — before spending effort building the pack, so a failure here doesn't waste that work:

1. Get the local project name: `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`.
2. Resolve it on the remote:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/resolve_project.py" <target> <project>
   ```
   - Exit 0: the remote path is printed — proceed.
   - Exit 1: no matching project directory exists on `<target>` — **stop and fail**. This is a hard requirement, not a fallback situation: tell the user the project isn't there and let them decide what to do (create it, pick a different target, drop `--move`).
   - Exit 2: multiple candidates were printed (one per line) — ask the user which one is correct, then cache their choice before continuing:
     ```bash
     "${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/record_project.py" <target> <project> <chosen-path>
     ```
   - Exit 64: a usage error (bad arguments) rather than a result — distinct from the 0/1/2 contract above so it can't be mistaken for one. All five scripts in this skill share this convention.
3. Build and send the pack as usual (Building a pack, Sending a pack above). Keep the exact remote archive path `send.py` printed — you'll need it verbatim in the next step.
4. Unpack it into the resolved project directory, which also removes the remote archive once extraction succeeds:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/handoff/scripts/unpack_remote.py" <target> <remote-archive-path-from-send.py> <remote-project-path>
   ```
5. Tell the user the final remote path it printed (`<target>:<remote-project-path>/<archive-name>/`) instead of the private-temp-dir one from step 3.

`resolve_project.py` and `record_project.py` maintain `~/.handoff/projects.tsv` — a local, tab-separated `<target><TAB><project><TAB><remote-path>` cache — so repeat handoffs to the same project skip the remote search. A cache hit is still verified against the remote (a cheap `test -d`) before being trusted, so a renamed or removed remote project triggers a fresh search instead of silently pointing at a stale path.
