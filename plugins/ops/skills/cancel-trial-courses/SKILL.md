---
name: cancel-trial-courses
description: >-
  Execute Edouard's recurring month-end "cancel the trials" request against the
  Sherpas production database. Trigger whenever someone asks to cancel / "passer
  en canceled" the trials for a list of chatroom IDs (CR IDs) — list pasted
  inline in a Slack message, linked in a Google Sheet, or attached as a CSV.
  Catch phrasings like "cancel les trials", "passer les trials en canceled",
  "trials à passer en canceled", "la liste des CR ID dont il faut canceled les
  trial", "clean les trials de fin de mois", or any month-end ask to drop
  never-held / archived / swapped trials from the stats — even when "trial" is
  the only clue. The skill extracts the chatroom IDs, runs a read-only
  assessment of each chatroom's trial-course status, then (via the mandatory RDS
  snapshot + CONFIRM WRITE workflow from db-super-admin-access) sets the trial
  course (course.isFirstCourse=1) status to 'canceled' for every not-yet-canceled
  trial. Back-office / DB only; Pipedrive is handled by ops.
---

# Cancel Trial Courses (Sherpas month-end cleanup)

## What this is and why it exists

Every end-of-month, Edouard sends a list of **chatroom IDs** ("CR IDs") and asks
to "passer les trials en canceled". These are chatrooms that were **archived,
swapped, or had their DMR cancelled** — the trial was accepted/scheduled but
**never actually took place**. The trial course is still sitting at an active
status (`accepted`, sometimes `pending`/`updated`), which **inflates the trial /
conversion numbers** in the Tableau dashboards. Flipping those trials to
`canceled` removes them from the stats.

This was a manual job for ~2 years (Edouard did it by hand; later Loup ran a
one-off SQL script). The system's own swap automation
(`cancelOldChatRoomTrialCourse`) deliberately refuses to cancel an `accepted`
trial whose date is in the **past** (to avoid cancelling a trial that genuinely
happened) — which is exactly why these archived-but-never-held trials linger and
need a manual cleanup.

**This skill does the back-office / DB side only.** The Pipedrive `Status Trial`
field is mirrored separately by ops (Olivier), as in previous months.

## Verified domain facts (don't re-derive these)

These were confirmed against `sherpas-api` and the prod DB and are stable:

- A **trial = the first course of a chatroom**: table `course`, column
  `isFirstCourse = 1`. There is no separate "trial" entity or flag.
- The **CR ID / chatroom ID** Edouard lists is `course.chatRoomId`
  (FK to `chat_room.id`, indexed — lookups are cheap).
- The trial's state is `course.status`, an enum with exactly these values
  (toolbox `CourseStatus`): `pending`, `accepted`, `canceled`, `updated`.
- **"Cancel the trial" = set that row's `status = 'canceled'`** (one `l`).
  This is literally what the production swap routine does:
  `UPDATE course SET status='canceled' WHERE chatRoomId=? AND isFirstCourse=true AND (...)`.
- Normally there is **one trial course per chatroom**, but there is **no DB
  unique constraint** guaranteeing it — always check for duplicates (Q3 below).
- `course.date` is the scheduled trial datetime; compare it to `NOW()` to tell a
  future (possibly still-live) trial from a past one.

## Prerequisites

- Read the **`db-super-admin-access`** skill — this skill relies on it for
  credentials, the read-only/read-write users, and the **mandatory pre-write RDS
  snapshot + CONFIRM WRITE** workflow. Do not re-implement credential handling.
- Credentials come from the db skill's env file (`.env`, with `op://`
  refs resolved via `op read`). Read-only assessment uses `PROD_DB_RO_*`; the
  cancellation write uses `PROD_DB_RW_*`.
- The bundled script needs `pymysql`
  (`pip install pymysql --break-system-packages`).

## Workflow

Work through these steps in order. Steps 1–2 are always read-only and safe;
step 3 is the only write and is gated behind the snapshot + confirmation.

### Step 1 — Get the chatroom IDs

Loup will point you at the request (a Slack message and/or a link). The list can
arrive in any of these shapes — handle whichever you're given:

- **Inline in the Slack message** — IDs typed directly (comma/space/newline
  separated, sometimes with noise words around them).
- **A linked Google Sheet** — read it with the Google Drive tool
  (`read_file_content` on the file ID from the URL). The IDs are usually a single
  unlabeled column.
- **A CSV / attachment** — download and read it.

Once you have the raw text/file, normalise it with the helper rather than
parsing by eye (it dedupes, drops non-IDs, and sanity-checks):

```bash
# from pasted text:
echo "<pasted text or column>" | python3 scripts/trial_db.py extract
# or from a file you fetched/downloaded:
python3 scripts/trial_db.py extract --input /path/to/list.csv
```

It prints a clean comma-separated `IDS=...` line and the count. Carry that exact
list forward. **Echo the count back to Loup and confirm it matches what Edouard
said** (he often states "~50 CR" / "72 CR") before going further.

### Step 2 — Read-only assessment (RO user)

Before touching anything, show what's actually there. This both verifies the IDs
really are chatroom IDs and tells Loup how much will change:

```bash
python3 scripts/trial_db.py assess --ids "<comma,separated,ids>" \
  --env-file /path/to/.env
```

This runs three read-only queries and prints a report:

- **Q1 coverage / disambiguation** — how many of the IDs exist as
  `chat_room.id`, and how many distinct chatrooms have a trial course. If
  coverage is far below 100%, stop and tell Loup — the list may not be chatroom
  IDs (or the sheet column was wrong).
- **Q2 status breakdown** — count of trial courses by `status`, with `accepted`
  split into **past** (`date <= NOW()`, the normal never-held case) and
  **future** (`date > NOW()`, *possibly a still-scheduled live trial*).
- **Q3 multiplicity** — any chatroom carrying more than one trial course.

Present the breakdown plainly. **Call out the `accepted`-future count
explicitly** — those are the only risky ones (a trial that may still be planned
to happen). Ask Loup whether to include or exclude them before the write
(default: include, since Edouard's lists are archived/never-held CRs).

### Step 3 — Cancel (the only write — follow the safety workflow)

Target set: **every trial course for the listed chatrooms whose status is not
already `canceled`** (`accepted` + `pending` + `updated` → `canceled`).
Already-`canceled` rows are left untouched.

The exact statement (one trial per chatroom is normal; this is keyed on
chatroom + first-course so duplicates are handled too):

```sql
UPDATE course
SET    status = 'canceled'
WHERE  isFirstCourse = 1
  AND  chatRoomId IN (<ids>)
  AND  status <> 'canceled';
-- If Loup chose to spare future-dated accepted trials, append:
--   AND NOT (status = 'accepted' AND date > NOW())
```

Run it **only** via the db-super-admin-access write workflow:

1. **Snapshot first.** Create the timestamped RDS snapshot and wait for it to be
   `available` (see db-super-admin-access "Mandatory Pre-Write Snapshot
   Workflow"). Share the snapshot identifier with Loup. If the snapshot fails,
   **stop** — do not write.
2. **Show the exact UPDATE** (with the resolved ID list) and the expected
   affected-row count from Step 2's breakdown.
3. Require an explicit **`CONFIRM WRITE`** from Loup.
4. Execute. The helper enforces all of this — it refuses to run without both a
   snapshot id and the confirmation token, and it runs inside a transaction:

```bash
python3 scripts/trial_db.py cancel --ids "<comma,separated,ids>" \
  --env-file /path/to/.env \
  --snapshot-id "<snapshot-id-from-step-1>" \
  --confirm CONFIRM_WRITE \
  # [--spare-future-accepted]   # only if Loup chose to exclude them
```

### Step 4 — Verify and report

The `cancel` command automatically re-runs the Step 2 breakdown afterwards.
Confirm **0 not-yet-canceled trials remain** for the list, then report to Loup:

- how many trials were just cancelled,
- how many were already `canceled` (no-op),
- how many `accepted`-future were spared (if any),
- the snapshot id used.

Give Loup a one-line summary he can forward to Edouard, e.g.
*"Done — 100 trials passés en canceled (7 déjà canceled). Snapshot pris avant
write."* Edouard usually wants the count so he can reconcile Tableau.

Reminder: **do not** touch Pipedrive — ops handle the `Status Trial` mirror.

## Failure modes to watch

- **Coverage < 100%** in Step 2 → the IDs probably aren't chatroom IDs (wrong
  sheet column, or they're course IDs). Don't write; show Loup the mismatch.
- **Unexpected statuses** (e.g. lots of `accepted`-future, or Q3 duplicates) →
  surface them; don't silently fold them into the write.
- **Snapshot not `available`** → stop; never write without a completed snapshot.
- **op / creds missing** → fall back to db-super-admin-access setup; the RW user
  is required for the write specifically.
