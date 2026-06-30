#!/usr/bin/env python3
"""
trial_db.py — month-end trial-course cancellation helper for Sherpas.

Subcommands:
  extract   Parse chatroom IDs out of pasted text / a CSV column (safe, offline).
  assess    Read-only: report trial-course status for a list of chatroom IDs.
  cancel    Write: set not-yet-canceled trial courses to 'canceled'
            (gated behind a snapshot id + an explicit CONFIRM_WRITE token).

Credentials are read from an env file in the db-super-admin-access format
(PROD_DB_HOST / PROD_DB_PORT / PROD_DB_NAME / PROD_DB_RO_USER /
PROD_DB_RO_PASSWORD / PROD_DB_RW_USER / PROD_DB_RW_PASSWORD). Values may be
1Password references (op://...) and are resolved at runtime with `op read`.
Passwords are kept in memory only and never printed.

Domain facts (verified against sherpas-api + prod):
  trial            = course row with isFirstCourse = 1
  CR / chatroom id = course.chatRoomId  (FK -> chat_room.id, indexed)
  cancel a trial   = set course.status = 'canceled'   (enum: pending/accepted/canceled/updated)
"""
import argparse
import re
import subprocess
import sys


# --------------------------------------------------------------------------- #
# ID extraction (offline, no DB)
# --------------------------------------------------------------------------- #
def extract_ids(text, min_digits=3, max_digits=9):
    # Drop URLs first so we don't harvest digits out of a Google Sheets link.
    text = re.sub(r"https?://\S+", " ", text)
    raw = re.findall(r"(?<!\d)\d+(?!\d)", text)
    ids, seen = [], set()
    for tok in raw:
        if not (min_digits <= len(tok) <= max_digits):
            continue
        n = int(tok)
        if n in seen:
            continue
        seen.add(n)
        ids.append(n)
    return sorted(ids)


def cmd_extract(args):
    if args.input:
        with open(args.input, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    ids = extract_ids(text, args.min_digits, args.max_digits)
    if not ids:
        print("No plausible chatroom IDs found.", file=sys.stderr)
        sys.exit(2)
    print(f"COUNT={len(ids)}")
    print("IDS=" + ",".join(map(str, ids)))
    # A couple of cheap sanity hints for the operator.
    yearish = [i for i in ids if 1990 <= i <= 2100]
    if yearish:
        print(f"WARNING: {len(yearish)} value(s) look like years {yearish[:5]}… "
              "— double-check the source column.", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Credential loading
# --------------------------------------------------------------------------- #
def _resolve(val):
    if val and val.startswith("op://"):
        return subprocess.check_output(["op", "read", val], text=True).strip()
    return val


def load_env(path):
    cfg = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def connect(env_path, write=False):
    import pymysql  # imported lazily so `extract` works without pymysql
    cfg = load_env(env_path)
    host = cfg["PROD_DB_HOST"]
    port = int(cfg.get("PROD_DB_PORT") or 3306)
    name = cfg["PROD_DB_NAME"]
    if write:
        user = cfg.get("PROD_DB_RW_USER")
        pwd = _resolve(cfg.get("PROD_DB_RW_PASSWORD"))
        if not user or not pwd:
            sys.exit("ERROR: PROD_DB_RW_USER / PROD_DB_RW_PASSWORD missing — "
                     "the cancel step needs the read-write credentials.")
    else:
        user = cfg["PROD_DB_RO_USER"]
        pwd = _resolve(cfg["PROD_DB_RO_PASSWORD"])
    conn = pymysql.connect(host=host, port=port, user=user, password=pwd,
                           database=name, connect_timeout=15, read_timeout=120,
                           autocommit=False)
    pwd = None  # noqa: F841 — drop the secret from the local frame
    return conn


def _placeholders(ids):
    return ",".join(["%s"] * len(ids))


# --------------------------------------------------------------------------- #
# Assessment (read-only)
# --------------------------------------------------------------------------- #
def run_assessment(conn, ids):
    ph = _placeholders(ids)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT "
            f"(SELECT COUNT(*) FROM chat_room WHERE id IN ({ph})), "
            f"(SELECT COUNT(DISTINCT chatRoomId) FROM course "
            f" WHERE isFirstCourse=1 AND chatRoomId IN ({ph}))",
            ids + ids,
        )
        match_cr, chatrooms_with_trial = cur.fetchone()

        cur.execute(
            f"SELECT status, "
            f"  CASE WHEN status='accepted' AND date >  NOW() THEN 'future' "
            f"       WHEN status='accepted' AND date <= NOW() THEN 'past' END AS bucket, "
            f"  COUNT(*) "
            f"FROM course WHERE isFirstCourse=1 AND chatRoomId IN ({ph}) "
            f"GROUP BY status, bucket ORDER BY status",
            ids,
        )
        breakdown = cur.fetchall()

        cur.execute(
            f"SELECT chatRoomId, COUNT(*) FROM course "
            f"WHERE isFirstCourse=1 AND chatRoomId IN ({ph}) "
            f"GROUP BY chatRoomId HAVING COUNT(*) > 1",
            ids,
        )
        dupes = cur.fetchall()

    print(f"  IDs given:                 {len(ids)}")
    print(f"  Valid as chat_room.id:     {match_cr}/{len(ids)} "
          f"({'OK' if match_cr == len(ids) else 'CHECK — list may be wrong'})")
    print(f"  Chatrooms with a trial:    {chatrooms_with_trial}")
    print("  Trial-course status breakdown:")
    to_cancel = 0
    future_accepted = 0
    for status, bucket, n in breakdown:
        label = status + (f" ({bucket})" if bucket else "")
        print(f"    {label:<22} {n}")
        if status != "canceled":
            to_cancel += n
        if status == "accepted" and bucket == "future":
            future_accepted = n
    print(f"  Not-yet-canceled (would change): {to_cancel}")
    if future_accepted:
        print(f"  ⚠ accepted+future (possibly still-live trials): {future_accepted} "
              f"— review before confirming.")
    if dupes:
        print(f"  ⚠ chatrooms with >1 trial course: {dupes}")
    return {"to_cancel": to_cancel, "future_accepted": future_accepted,
            "coverage_ok": match_cr == len(ids)}


def cmd_assess(args):
    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    conn = connect(args.env_file, write=False)
    try:
        print("=== Trial cancellation — READ-ONLY assessment ===")
        run_assessment(conn, ids)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Cancel (write — gated)
# --------------------------------------------------------------------------- #
def cmd_cancel(args):
    if args.confirm != "CONFIRM_WRITE":
        sys.exit("REFUSED: pass --confirm CONFIRM_WRITE to execute the write.")
    if not args.snapshot_id or not args.snapshot_id.strip():
        sys.exit("REFUSED: --snapshot-id is required (take the RDS snapshot first).")

    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    ph = _placeholders(ids)
    where = (f"isFirstCourse=1 AND chatRoomId IN ({ph}) AND status <> 'canceled'")
    if args.spare_future_accepted:
        where += " AND NOT (status='accepted' AND date > NOW())"
    sql = f"UPDATE course SET status='canceled' WHERE {where}"

    print(f"Snapshot provided: {args.snapshot_id}")
    print(f"SQL: {sql}")
    print(f"IDs: {len(ids)}")

    conn = connect(args.env_file, write=True)
    try:
        with conn.cursor() as cur:
            affected = cur.execute(sql, ids)
        conn.commit()
        print(f"\n✅ Committed. Rows changed: {affected}")
        print("\n=== Post-write verification (read-back on same connection) ===")
        run_assessment(conn, ids)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="parse chatroom IDs from text/CSV (offline)")
    pe.add_argument("--input", help="file to read (default: stdin)")
    pe.add_argument("--min-digits", type=int, default=3)
    pe.add_argument("--max-digits", type=int, default=9)
    pe.set_defaults(func=cmd_extract)

    pa = sub.add_parser("assess", help="read-only status report for IDs")
    pa.add_argument("--ids", required=True, help="comma-separated chatroom IDs")
    pa.add_argument("--env-file", default=".env")
    pa.set_defaults(func=cmd_assess)

    pc = sub.add_parser("cancel", help="write: cancel not-yet-canceled trials (gated)")
    pc.add_argument("--ids", required=True, help="comma-separated chatroom IDs")
    pc.add_argument("--env-file", default=".env")
    pc.add_argument("--snapshot-id", required=True,
                    help="RDS snapshot id created before this write")
    pc.add_argument("--confirm", required=True,
                    help="must be the literal token CONFIRM_WRITE")
    pc.add_argument("--spare-future-accepted", action="store_true",
                    help="leave accepted trials whose date is in the future")
    pc.set_defaults(func=cmd_cancel)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
