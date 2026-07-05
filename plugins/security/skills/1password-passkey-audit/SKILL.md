---
name: 1password-passkey-audit
description: >-
  Audit Loup's 1Password vault(s) for every item that has a saved passkey and
  build/refresh the French Markdown rotation tracker (`PASSKEYS.md` format:
  checkbox table of service/compte/lien/notes). Fetches the 1Password
  service-account API token from the connected Bitwarden vault (an item named
  like "1Password - <name>"), then uses the `op` CLI to enumerate every
  Login/Password item's URL and username, redacting every secret value along
  the way. CRITICAL, VERIFIED LIMITATION: the 1Password CLI / service-account
  API cannot see passkeys at all, under any flag or filter — so this skill
  never tries to auto-detect them, and neither should you; it always asks Loup
  for the ground-truth list of passkey-holding item titles (copied or
  screenshotted from a 1Password app search for "passkey"). Trigger this skill
  whenever Loup asks to audit/list/track which 1Password items have a passkey,
  rebuild or update `PASSKEYS.md`, cross-reference a list of passkey titles
  with their account/URL, or plan a batch passkey rotation — even if he just
  pastes titles from the app and says "make me a list" or "update the
  tracker," and even if he doesn't mention 1Password by name but references
  "passkeys" or "clés d'accès" for his accounts.
---

# 1Password Passkey Audit

## What this is and why it exists

Loup wants a living checklist of every account that has a passkey saved in
1Password, so he can work through rotating them one by one (delete the old
passkey at the service, create a new one). The tracker lives at
`PASSKEYS.md` in the `me` repo (`~/code/perso/global/me/PASSKEYS.md`) —
read it once at the start of a run if it exists, both to match its exact
format and to carry forward checkbox progress (✅ done, 🚫 account deleted)
across re-runs.

## The one fact that makes this skill non-obvious

**The 1Password CLI cannot detect passkeys, at all, via a service account.**
This was verified the hard way in the session that produced this skill: an
item confirmed via the 1Password app UI to have a passkey (created a known
date) showed **zero trace of it** in `op item get --format=json`, even with
`--reveal` and `--long`. Explicitly tried and failed:

- `op item get <id> --fields "type=passkey"` — the CLI accepts `passkey` as a
  known field-type keyword (no "unknown type" error), but reports "item
  doesn't have any fields of the following types: passkey" for items that
  **definitely** have one. 100% false-negative rate on every real passkey
  tested.
- `op item list --categories Passkey` — errors "Unknown item category
  Passkey". Passkeys attach to `Login` items; they are not their own
  category.
- The official `op` CLI changelog
  (https://app-updates.agilebits.com/product_history/CLI2) has exactly one
  changelog line ever mentioning "passkey" (v2.33.1): a warning that editing
  an item via a JSON template will silently destroy its passkey. No version
  has ever added passkey *read* support to `item get`/`item list`.

This isn't a permissions gap to work around — it's a hard capability gap.
**Do not** write code that tries to detect passkeys via the API and do not
report "N passkeys found" based on API output alone. The only reliable
source of truth is the 1Password app itself (desktop or web), searching
`passkey` across all vaults. If Loup hasn't already given you that list for
this run, ask him for it — either as pasted item titles or as screenshots of
the search results (you can read titles/usernames straight off a
screenshot).

Everything this skill *can* safely automate — enumerating vault items,
pulling each one's login URL and username, matching them against the titles
Loup gives you, and formatting the tracker — is handled by the bundled
script. Use it rather than re-deriving the `op`/`bw` plumbing by hand; the
plumbing has a few sharp edges (below) that are already worked out in the
script.

## Prerequisites

- `bw` (Bitwarden CLI) and `op` (1Password CLI) installed and on `PATH`.
- A valid Bitwarden session. The `security` plugin's Bitwarden MCP tools can
  unlock interactively, but that flow only supports a native
  master-password dialog — it cannot take a session token as input. If Loup
  hands you a raw session token directly in chat (the shape `bw unlock
  --raw` produces), that means he's already unlocked the vault elsewhere;
  pass it straight to the script via `--bw-session` (or export it as
  `BW_SESSION`) rather than trying the MCP `unlock` tool.
- The 1Password service-account API token must exist as a Bitwarden item
  whose name contains "1Password" (commonly `1Password - <name>`), in a
  custom field (seen so far as `Api Key` or `service-account` — the script
  tries common names and lists candidates if it can't find one).

## Workflow

### Step 1 — Get the ground-truth passkey title list

Ask Loup (unless he already gave it to you this run) to search `passkey` in
the 1Password app across all vaults and share the results — pasted titles or
screenshots both work. Write the titles to a plain text file, one per line
(`passkey_titles.txt`). Don't skip this step or infer it from anything
API-based — see above.

### Step 2 — Run the scan

```bash
python3 scripts/passkey_audit.py scan \
  --bw-search "1Password" \
  --titles passkey_titles.txt \
  --output PASSKEYS.md \
  --previous /path/to/existing/PASSKEYS.md   # omit if there isn't one yet
```

What it does, in order (see the script's own `--help` and docstrings for
flag details):

1. `bw sync`, then finds the Bitwarden item holding the 1Password token
   (`--bw-search`, default `"1Password"`). If more than one item matches, it
   prints all candidates with their `login.username` and stops — pick the
   right one and re-run with a more specific `--bw-search` (e.g. the exact
   item title) rather than letting it guess.
2. Extracts the token into memory only (never printed, never written to
   disk) and confirms it works (`op whoami`).
3. Enumerates every `Login` and `Password` category item across every vault
   the token can see (`op item list`, no `--vault` filter needed for this
   call), then fetches each item's URL and username in parallel — always
   through a redacting filter that drops password/OTP/concealed values
   before they ever hit stdout, a file, or your context. This is
   non-negotiable: a raw bank password leaked into a chat transcript earlier
   in this skill's development before that redaction discipline existed.
   Username values and URLs are not secrets and are kept, since they're
   needed to tell accounts apart.
4. Matches each title from Step 1 against the enumerated items **by exact
   title**. Zero matches → flagged as not-found (maybe it's in a vault this
   token can't see, e.g. the Personal/Private vault, which 1Password never
   grants to service accounts — say so explicitly rather than silently
   dropping it). More than one match for the same title → all candidates
   are kept and the row's Notes column is auto-filled with a disambiguation
   warning (this happened for real with two "Amazon" items in the vault,
   one of which belonged to someone else entirely) — don't silently pick
   one.
5. If `--previous` is given, carries forward the ✅/🚫 status and any
   hand-written notes for rows matched on the same (title, account) pair, so
   re-running the scan doesn't reset progress Loup already tracked.
6. Writes the Markdown tracker in the established format (see below).

### Step 3 — Review with Loup

Show the generated file (or the diff, if `--previous` was used) before
treating it as final — titles can be ambiguous, an account might have
changed, etc. This is a personal tracker he edits by hand between runs
(checking things off, adding 🚫 for deleted accounts) — don't overwrite his
manual edits if you're unsure whether the new scan output should win;
surface the difference and ask.

## Output format

French, matching the established tracker in the `me` repo:

- An intro blockquote: what this file is, the passkey-detection limitation
  (so nobody re-trusts an API scan for "0 passkeys" again), and that
  passwords are deliberately excluded.
- A legend line: `☐ à faire · ✅ fait (date) · ⚠️ à vérifier · 🚫 compte
  supprimé`.
- A table: `Statut | Service | Compte | Lien (coffre 1Password) | Notes`.
- A total count line, and a short "Suivi" footer explaining how to check
  things off.

The script's `report` output already follows this template — you shouldn't
need to hand-write the Markdown, just review its output for anything
domain-specific worth adding to Notes (e.g. "sécurité gérée depuis l'app
mobile" for services with no web passkey management).

## Failure modes to watch

- **Bitwarden item search returns 0 or >1 candidates** — don't guess; show
  Loup the list (or lack of one) and ask for a more specific `--bw-search`.
- **`op` errors "a vault query must be provided"** — you're calling
  `item get` without a `--vault`; the script always carries the vault name
  forward from the `item list` step, so this should only happen if you've
  bypassed the script and are calling `op` by hand.
- **A title from Step 1 matches nothing** — likely either a typo, or the
  item lives in a vault the service account can't reach (most commonly the
  user's Personal/Private vault, which 1Password structurally excludes from
  service-account access). Say which of these it is, don't just drop the
  row.
- **Scan seems to hang with no output and no visible process** — happened
  once in development with a serial shell loop backgrounded via `run_in_background`;
  root cause was never confirmed (possibly an undocumented service-account
  rate limit — the 1Password community forum mentions 15+ minute blocks with
  no visible backoff signal). The script's built-in parallelism
  (`ThreadPoolExecutor`, not a shell loop) avoided this every time it was
  tried, but if a run does stall, kill it and retry with a lower
  `--max-workers` rather than waiting indefinitely.
