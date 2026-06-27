---
name: free-disk-space
description: >-
  Reclaim as much disk space as possible on a machine, aggressively but safely.
  Use this whenever the user is low on disk space or wants to clean up their
  machine — phrasings like "free up space", "my disk is full", "running out of
  space", "clean my mac", "reclaim disk", "make room on this drive", or in French
  "libère de la place", "mon disque est plein", "vide la machine", "nettoie mon
  mac", "j'ai plus de place". Trigger even when the user doesn't name a specific
  folder — the skill figures out where the space went. It distinguishes
  regenerable caches (safe to wipe) from recoverable-with-impact artifacts
  (node_modules, Docker, SDKs) from genuine personal data (back up or confirm
  first), clears the safe tier autonomously, and confirms before anything
  destructive. macOS-first (APFS-aware); see references/linux.md for Linux.
---

# Free disk space

Reclaim disk space by working from the safest wins to the riskiest, never
surprising the user with lost data. On a typical dev machine the easy, fully
**regenerable** caches alone are often 100 GB+ — you rarely need to touch
anything personal to make a huge dent.

The whole game is **classifying what you find** before deleting it. Three tiers:

- 🟢 **Regenerable** — caches and build artifacts the system rebuilds on demand
  (package caches, compiler caches, editor caches). Deleting them costs only a
  one-time "first run is slower". Wipe these freely.
- 🟠 **Recoverable-with-impact** — `node_modules`, Docker images/volumes, SDKs,
  simulators. Re-downloadable or re-buildable, but deleting them interrupts a
  workflow or re-downloads gigabytes. Confirm scope, then act.
- 🔴 **Personal / irreplaceable** — Downloads, Trash, browser profiles, documents,
  databases with real data. Back up or confirm per item. Never bulk-delete.

Be aggressive **within a tier's risk level**, not across it. The user explicitly
wanting "aggressive" cleanup means "don't be timid about caches and clearly-
disposable junk" — it does **not** mean "delete my database without asking".

## Workflow

Work in phases. Measure space before and after each destructive phase so you can
report concrete wins and catch surprises.

1. **Assess (read-only).** Run `scripts/assess.sh`. It reports real free space
   and ranks where the space actually went (home subdirs, Library, caches,
   Developer/Xcode, code, Docker, Trash, Downloads). Read it before deciding
   anything — never guess what's big.
2. **Clear the safe tier (autonomous).** Run `scripts/clean-safe-caches.sh
   --apply`. This wipes only 🟢 regenerable caches and reports freed space. You
   can do this without asking — it's the textbook reversible category and it's
   usually the biggest single win. Announce what you're clearing and the result.
3. **Confirm the 🟠 tier.** Present the recoverable-with-impact items you found
   (with sizes) and let the user pick. Use the AskUserQuestion tool with
   multiSelect so they choose à la carte. Typical items: `node_modules` sweep,
   Android SDK/AVD, extra iOS simulators/runtimes, Docker. Then execute the
   chosen ones (`scripts/reclaim-node-modules.sh`, `scripts/docker-reclaim.sh`).
4. **Handle 🔴 personal data deliberately.** For Downloads / large personal
   folders, **triage** rather than nuke — see the "Downloads & file triage"
   section. Offer to back up to a NAS/external/cloud before deleting anything the
   user can't regenerate.
5. **Report.** Give a before/after table (free space at start vs end, total
   reclaimed, % occupancy) and list what the user must redo later (relaunch
   Docker + reseed DBs, first `npm install` re-downloads, etc.).

Keep the user oriented: short announcements before each phase, a measured result
after. They should always know what you just deleted and what it cost.

## Measuring space correctly (macOS / APFS)

`df -h /` is **misleading** on APFS — volumes share a container and `Avail` can
lag. For the true number use the container free space:

```bash
diskutil info / | grep -i "Free Space"
```

Always report this one. The helper scripts already use it.

## The safe tier (🟢) — what `clean-safe-caches.sh` clears

All of these are regenerated automatically. The script handles them; this list is
so you understand what's being touched and can explain it:

- `~/.cache/*` — `uv` (Python, often the single biggest item), `puppeteer`,
  `pyright`, `pre-commit`, `firebase`, `pip`, `node`, `gh`, …
- `~/Library/Caches/*` — general app caches
- Xcode: `~/Library/Developer/Xcode/DerivedData`, `.../iOS DeviceSupport`
- `~/.npm/_cacache`, `~/.gradle/caches`, `~/Library/Caches/pip`
- Editor Electron caches — for Cursor / Code / Claude desktop, only the
  `Cache`, `Code Cache`, `GPUCache`, `CachedData`, `CachedExtensionVSIXs`, `logs`
  subdirs. **Never** their `backups`, `*-sessions`, `User`, `History`, or
  `workspaceStorage` — those hold real state.
- `xcrun simctl delete unavailable` — removes only orphaned simulators
- `brew cleanup` and `docker builder prune` (build cache only)

The script never touches anything outside this list. If you want to add a target,
add it there with a one-line justification of why it's regenerable.

## The 🟠 tier — recoverable with impact

- **`node_modules`** — `scripts/reclaim-node-modules.sh <dir>` finds and removes
  them. Regenerable via `npm/yarn/pnpm install`, but it breaks those projects
  until reinstalled. Default to a dry-run first to show count + total size.
- **Android** — `~/Library/Android/sdk` (SDK) and `~/.android/avd` (emulators).
  Re-downloadable but large; only remove if the user isn't doing Android dev now.
- **Docker** — see the dedicated section; the disk image needs special handling.
- **iOS simulator runtimes** — beyond `delete unavailable`, removing specific
  runtimes (`xcrun simctl runtime delete <id>`) frees more but re-downloads.

## Docker — read this before reclaiming

Docker is the classic trap. Two facts that change everything:

1. **The disk image does not shrink on its own.** On macOS the data lives in a
   sparse `Docker.raw` (e.g.
   `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`).
   Deleting images/volumes frees space *inside* the VM but the `.raw` file stays
   the same size on disk. To actually reclaim the disk you must either compact it
   (Docker Desktop) or do a full reset (delete the `.raw`, which Docker recreates
   empty on next launch).
2. **Volumes can hold real data.** A "13 GB of volumes, 2 active" line can be a
   live dev database. **Always inspect before nuking** — `docker system df -v`,
   `docker ps -a`, `docker volume ls`. A full reset destroys it.

`scripts/docker-reclaim.sh` has three modes:

- `inspect` (default) — prints containers, images, volumes (with sizes), and the
  `Docker.raw` size. Always run this first and show the user.
- `prune-safe` — `docker builder prune` + dangling images only. No data loss.
- `full-reset --yes` — quits Docker Desktop, deletes `Docker.raw`. Reclaims the
  whole image but **destroys all containers/images/volumes**. Only after the user
  confirms with full knowledge of what's in their volumes. Surface any volume
  that looks like a database (size, name) and name it explicitly in the
  confirmation so the user isn't deciding blind.

## Downloads & file triage (🔴)

Downloads is a mix of pure junk and things that matter. Don't bulk-delete — sort
by category, delete the obvious, ask about the rest, and **protect documents**.

1. Run `scripts/assess.sh downloads` (or inventory inline) to see sizes by type.
2. Delete the unambiguous junk autonomously: **installers** (`.dmg`, `.pkg`),
   tool outputs (`iloveimg-*`, generated icon sets, `*.har`, browser captures),
   and dev/session artifacts. Apps are installed; installers re-download.
3. Ask (AskUserQuestion, multiSelect) about the ambiguous-but-bulky categories:
   personal media, data exports (Google Takeout, DB dumps), sideload `.ipa`,
   old project zips.
4. **Always preserve** documents (`*.pdf`), unless the user explicitly says
   otherwise. Invoices, contracts, scans hide here. When in doubt, keep.
5. **Flag sensitive files loudly** and don't quietly delete them: password-
   manager exports (`*.1pux`, `*.csv` from a vault), private keys (`*.pem`,
   `id_rsa`, `*.p12`, `*.keychain`), wallet/seed files. Recommend the user
   secure-delete or relocate them, and confirm.
6. **Dedupe** with `scripts/dedupe-files.py <dir>` — it removes only
   byte-identical copies (by hash), keeping the cleanest name. Two files with the
   same name suffix but **different hashes are not duplicates** — keep both and
   say so (e.g. a signed vs unsigned contract).

### Archiving instead of deleting

When a personal file shouldn't just be deleted but doesn't belong in Downloads
(a contract, an invoice), offer to archive it into the right repo/folder rather
than lose it:

1. Identify what it actually is (read it — filenames lie; a file named
   "Contrat mariage" turned out to be a DJ contract).
2. Copy it to its home with a clear, conventional name.
3. **Verify by hash** that the copy matches the source before removing the
   original (`md5 -q`). Only delete the source once the copy is confirmed.
4. If the destination is a git repo, `git add` just that file and commit it, so
   it's truly archived. Don't push unless asked.

## Safety principles

These are the rules that keep an aggressive cleanup from becoming a disaster:

- **Reversible-first.** Always exhaust 🟢 caches before considering anything that
  loses data. It's usually enough.
- **Confirm the irreversible.** Emptying Trash, deleting volumes, wiping personal
  data — confirm per scope, and for data the user can't regenerate, offer a
  backup first.
- **Look before you delete.** If something is described as junk but inspection
  shows it's a live database, a legal document, or a password export, stop and
  surface it. Filenames and the user's mental model are not always right.
- **Never touch state masquerading as cache.** Editor `workspaceStorage`, app
  `backups`, `*-sessions`, browser `History`/`Login Data`, mail stores — these
  live under Caches/Application Support but are not caches.
- **Measure and report honestly.** Show real freed space (APFS container), and if
  a step freed nothing (e.g. `docker volume prune` skipped in-use volumes), say
  so rather than implying success.

## Scripts

- `scripts/assess.sh [downloads]` — read-only disk assessment. No args: full
  machine scan. `downloads`: inventory the Downloads folder by category/size.
- `scripts/clean-safe-caches.sh [--apply]` — wipe 🟢 regenerable caches. Default
  is a dry-run that lists targets + sizes; `--apply` actually deletes and reports
  freed space.
- `scripts/reclaim-node-modules.sh <dir> [--apply]` — find/remove `node_modules`
  under `<dir>`. Dry-run by default (count + total size).
- `scripts/docker-reclaim.sh {inspect|prune-safe|full-reset --yes}` — Docker
  space reclamation with safety gates (see Docker section).
- `scripts/dedupe-files.py <dir> [--apply] [--ext pdf,jpg]` — remove byte-
  identical duplicate files, keeping one. Dry-run by default.

See `references/categories.md` for the full path-by-path taxonomy and
`references/linux.md` for Linux equivalents of the macOS-specific paths/tools.
