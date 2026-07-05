#!/usr/bin/env python3
"""1Password passkey-rotation audit helper.

Fetches a 1Password service-account token from Bitwarden, enumerates every
Login/Password item's URL and username across all vaults the token can see
(always redacting secret values), matches those items against a
user-supplied list of passkey-holding item titles, and writes/updates a
French Markdown rotation tracker.

IMPORTANT: this script cannot detect which items have a passkey. The
1Password CLI does not expose that information via any API call, flag, or
field filter, for a service account (verified empirically — see SKILL.md).
The list of passkey titles is always an input, sourced from the 1Password
app's own "passkey" search, never derived here.

Subcommands (run `scan` for the full pipeline, or the individual steps when
iterating/debugging so you don't re-hit the API every time):

    token      resolve + sanity-check the 1Password token from Bitwarden
    enumerate  dump redacted Login/Password item metadata for all vaults
    match      match target titles against an enumerate dump
    report     render the Markdown tracker from a match result
    scan       token -> enumerate -> match -> report, in one go
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

CANDIDATE_TOKEN_FIELD_NAMES = [
    "api key", "service-account", "service account", "token",
    "service account token", "credential", "api token",
]
PASSKEY_CAPABLE_CATEGORIES = {"LOGIN", "PASSWORD"}


class CliError(RuntimeError):
    pass


def run_cli(args, env, timeout=20, retries=1):
    """Run a CLI command, retrying once on transient failure. Never logs env."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            proc = subprocess.run(
                args, env=env, capture_output=True, text=True, timeout=timeout,
            )
            if proc.returncode == 0:
                return proc.stdout
            last_err = proc.stderr.strip() or f"exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            last_err = f"timed out after {timeout}s"
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise CliError(f"{' '.join(args[:2])} failed: {last_err}")


def bw_env(bw_session):
    env = dict(os.environ)
    env["BW_SESSION"] = bw_session
    return env


def op_env(token):
    env = dict(os.environ)
    env["OP_SERVICE_ACCOUNT_TOKEN"] = token
    return env


def resolve_bw_session(args):
    session = args.bw_session or os.environ.get("BW_SESSION")
    if not session:
        raise CliError(
            "No Bitwarden session available. Pass --bw-session or export "
            "BW_SESSION (the value from `bw unlock --raw`)."
        )
    return session


def find_bw_candidates(env, search_term, exact_title=None):
    run_cli(["bw", "sync"], env, timeout=30)
    raw = run_cli(["bw", "list", "items", "--search", search_term], env, timeout=20)
    items = json.loads(raw)
    candidates = [it for it in items if "1password" in it.get("name", "").lower()]
    if exact_title:
        candidates = [it for it in candidates if it.get("name") == exact_title]
    return candidates


def extract_token_field(item, field_hint=None):
    fields = item.get("fields", [])
    if field_hint:
        for f in fields:
            if (f.get("name") or "").strip().lower() == field_hint.strip().lower():
                return f.get("value")
        raise CliError(
            f"Field '{field_hint}' not found on '{item.get('name')}'. "
            f"Available field names: {[f.get('name') for f in fields]}"
        )
    for f in fields:
        name = (f.get("name") or "").strip().lower()
        if name in CANDIDATE_TOKEN_FIELD_NAMES:
            return f.get("value")
    if len(fields) == 1 and fields[0].get("value"):
        print(
            f"[warn] no field matched known names, using the only custom "
            f"field present ('{fields[0].get('name')}')",
            file=sys.stderr,
        )
        return fields[0]["value"]
    raise CliError(
        f"Could not find the API token field on '{item.get('name')}'. "
        f"Available field names: {[f.get('name') for f in fields]}. "
        f"Re-run with --bw-field <name>."
    )


def cmd_token(args):
    """Resolve the 1Password service-account token and confirm it works.
    Never prints the token itself."""
    session = resolve_bw_session(args)
    env = bw_env(session)
    candidates = find_bw_candidates(env, args.bw_search, args.bw_item)
    if len(candidates) != 1:
        print(
            f"Found {len(candidates)} Bitwarden item(s) matching "
            f"'{args.bw_search}':",
            file=sys.stderr,
        )
        for c in candidates:
            print(f"  - {c.get('name')} (username: {c.get('login', {}).get('username')})",
                  file=sys.stderr)
        raise CliError(
            "Ambiguous or no match — re-run with --bw-item '<exact title>'."
        )
    item_id = candidates[0]["id"]
    full = json.loads(run_cli(["bw", "get", "item", item_id], env, timeout=15))
    token = extract_token_field(full, args.bw_field)
    oenv = op_env(token)
    whoami = json.loads(run_cli(["op", "whoami", "--format=json"], oenv, timeout=15))
    vaults = json.loads(run_cli(["op", "vault", "list", "--format=json"], oenv, timeout=15))
    print(f"[ok] token works — account: {whoami.get('url')}", file=sys.stderr)
    print(f"[ok] visible vault(s): {[v['name'] for v in vaults]}", file=sys.stderr)
    return token, [v["name"] for v in vaults]


def op_item_list(oenv, vault_names=None):
    """List item overviews across all vaults the token can see. Falls back to
    per-vault listing if a vaultless call is rejected (service accounts
    sometimes require an explicit vault even for `item list`)."""
    try:
        raw = run_cli(["op", "item", "list", "--format=json"], oenv, timeout=30)
        return json.loads(raw)
    except CliError as e:
        if "vault query must be provided" not in str(e) or not vault_names:
            raise
        items = []
        for v in vault_names:
            raw = run_cli(["op", "item", "list", "--vault", v, "--format=json"], oenv, timeout=30)
            items.extend(json.loads(raw))
        return items


def fetch_item_redacted(item_id, vault_name, oenv):
    """Fetch one item and keep only non-secret fields (title, category, urls,
    username). Never returns password/OTP/concealed values — those are
    dropped by construction, not by filtering them out after the fact."""
    try:
        raw = run_cli(
            ["op", "item", "get", item_id, "--vault", vault_name, "--format=json"],
            oenv, timeout=15, retries=1,
        )
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001 - report and move on, don't abort the batch
        return {"id": item_id, "vault": vault_name, "title": None, "error": str(e)}
    username = next(
        (f.get("value") for f in data.get("fields", []) if f.get("purpose") == "USERNAME"),
        None,
    )
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "category": data.get("category"),
        "vault": vault_name,
        "urls": [u.get("href") for u in data.get("urls", []) if u.get("href")],
        "username": username,
    }


def cmd_enumerate(args, token=None, vault_names=None):
    if token is None:
        token, vault_names = cmd_token(args)
    oenv = op_env(token)
    overview = op_item_list(oenv, vault_names)
    targets = [it for it in overview if it.get("category") in PASSKEY_CAPABLE_CATEGORIES]
    print(
        f"[info] {len(overview)} total items, {len(targets)} in "
        f"Login/Password categories (only these can hold a passkey)",
        file=sys.stderr,
    )
    records = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {
            pool.submit(fetch_item_redacted, it["id"], it["vault"]["name"], oenv): it
            for it in targets
        }
        done = 0
        for fut in as_completed(futures):
            records.append(fut.result())
            done += 1
            if done % 100 == 0:
                print(f"[info] fetched {done}/{len(targets)}", file=sys.stderr)
    errors = [r for r in records if r.get("error")]
    if errors:
        print(f"[warn] {len(errors)} item(s) failed to fetch — see 'error' field", file=sys.stderr)
    if args.output:
        with open(args.output, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        print(f"[ok] wrote {len(records)} records to {args.output}", file=sys.stderr)
    return records


def cmd_match(args, records=None):
    if records is None:
        with open(args.enumerated) as f:
            records = [json.loads(line) for line in f if line.strip()]
    by_title = {}
    for r in records:
        by_title.setdefault(r.get("title"), []).append(r)

    with open(args.titles) as f:
        targets = [line.strip() for line in f if line.strip()]

    results = []
    for t in targets:
        matches = by_title.get(t)
        if not matches:
            # forgiving case-insensitive fallback, flagged as such
            ci_matches = [
                r for title, rs in by_title.items()
                if title and title.lower() == t.lower()
                for r in rs
            ]
            if ci_matches:
                matches = ci_matches
                note = "trouvé par correspondance insensible à la casse — vérifier le titre exact"
            else:
                results.append({"target": t, "matches": [], "note": "introuvable dans les vaults accessibles au token — peut-être dans le coffre Personal/Private (non accessible aux service accounts)"})
                continue
        else:
            note = None
        if len(matches) > 1:
            accounts = ", ".join(m.get("username") or "?" for m in matches)
            note = f"⚠️ {len(matches)} éléments trouvés pour ce titre (comptes: {accounts}) — vérifier lequel est le bon avant d'agir"
        results.append({"target": t, "matches": matches, "note": note})

    not_found = [r["target"] for r in results if not r["matches"]]
    if not_found:
        print(f"[warn] {len(not_found)} title(s) not found: {not_found}", file=sys.stderr)
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[ok] wrote match results to {args.output}", file=sys.stderr)
    return results


INTRO_TEMPLATE = """# Rotation des passkeys 1Password — dossier du {date}

> **Contexte.** Le token API/CLI 1Password (service account) ne permet **pas**
> de lister les passkeys : elles sont totalement absentes du JSON renvoyé par
> `op item get`, même avec `--reveal`/`--long`. Seule la recherche native
> `passkey` dans l'app 1Password (desktop/web) les affiche. La liste des
> identifiants ci-dessous vient de cette recherche, pas de l'API.
>
> **Mot de passe volontairement exclu** de ce tracker.
>
> **Méthode générale** (valable pour la plupart des services) : se connecter
> au service → Paramètres du compte → Sécurité / Connexion → repérer la
> passkey existante → la **supprimer** → en **créer une nouvelle**. Si
> l'extension navigateur 1Password est active, elle propose automatiquement
> d'enregistrer la nouvelle passkey à la place de l'ancienne.

Légende : ☐ à faire · ✅ fait · ⚠️ à vérifier avant de commencer · 🚫 compte supprimé, plus concerné

## Liste

| Statut | Service | Compte | Lien (coffre 1Password) | Notes |
|---|---|---|---|---|
"""

FOOTER_TEMPLATE = """
{count_line}

## Suivi

Cocher ☐ → ✅ au fur et à mesure. Ajouter la date entre parenthèses si utile
(ex. `✅ ({date})`).
"""


def parse_previous_table(path):
    """Extract {title: [(account, status_cell, notes_cell), ...]} from an
    existing tracker so re-scans don't reset progress Loup already tracked by
    hand. Grouped by title (not by (title, account)) because account cells
    are sometimes a partially-masked value transcribed from an app
    screenshot (e.g. "******2901") that won't byte-for-byte match what a
    fresh API fetch returns for the same field (e.g. "*******2901") — for the
    common case of one previous row per title, carry its status forward
    regardless of the account text; only fall back to matching on account
    when a title genuinely had more than one row (a real duplicate, like two
    different "Amazon" items)."""
    prev = {}
    if not path or not os.path.exists(path):
        return prev
    with open(path) as f:
        lines = f.readlines()
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("Statut", "---"):
            continue
        status, service, account, _link, notes = cells
        prev.setdefault(service, []).append((account, status, notes))
    return prev


def lookup_previous(previous, title, account):
    entries = previous.get(title)
    if not entries:
        return "☐", None
    if len(entries) == 1:
        return entries[0][1], entries[0][2]
    for acc, status, notes in entries:
        if acc == account:
            return status, notes
    return "☐", None  # genuinely ambiguous carry-over — safe default, don't guess


def simplify_url(url):
    """Keep scheme + host + path, drop query string and fragment. The path
    is usually the meaningful part (a security-settings page, a specific
    login route); query strings are where the junk lives — expired OAuth
    codes, tracking params, one-time state tokens."""
    if not url:
        return ""
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def cmd_report(args, results=None):
    if results is None:
        with open(args.matched) as f:
            results = json.load(f)
    previous = parse_previous_table(args.previous)

    rows = []

    def build_row(target, m, note):
        title = m.get("title") or target
        account = m.get("username") or "?"
        url = simplify_url((m.get("urls") or [None])[0])
        prev_status, prev_note = lookup_previous(previous, title, account)
        final_note = note or prev_note or ""
        return f"| {prev_status} | {title} | {account} | {url} | {final_note} |"

    for r in results:
        if not r["matches"]:
            rows.append(f"| ☐ | {r['target']} | ? | | {r['note']} |")
            continue
        for m in r["matches"]:
            rows.append(build_row(r["target"], m, r["note"]))

    count_line = f"**Total : {len(results)} identifiants"
    if len(rows) != len(results):
        count_line += f" ({len(rows)} lignes — au moins un titre a plusieurs comptes candidats, voir Notes)"
    count_line += ".**"

    body = INTRO_TEMPLATE.format(date=args.date) + "\n".join(rows)
    body += FOOTER_TEMPLATE.format(count_line=count_line, date=args.date)

    with open(args.output, "w") as f:
        f.write(body)
    print(f"[ok] wrote tracker to {args.output} ({len(rows)} rows)", file=sys.stderr)
    return body


def cmd_scan(args):
    token, vault_names = cmd_token(args)
    records = cmd_enumerate(args, token=token, vault_names=vault_names)
    results = cmd_match(args, records=records)
    cmd_report(args, results=results)


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bw-session", help="Bitwarden session token (else reads BW_SESSION env var)")
    p.add_argument("--bw-search", default="1Password", help="Search term to find the Bitwarden item holding the 1Password token")
    p.add_argument("--bw-item", help="Exact Bitwarden item title, if --bw-search is ambiguous")
    p.add_argument("--bw-field", help="Exact custom-field name holding the token, if auto-detection fails")
    p.add_argument("--max-workers", type=int, default=8, help="Parallel `op item get` workers (default 8)")
    p.add_argument("--date", default=date.today().strftime("%d/%m/%Y"), help="Date stamp for the report (default: today, dd/mm/yyyy)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("token", help="Resolve + sanity-check the 1Password token")
    sp.set_defaults(func=cmd_token)

    sp = sub.add_parser("enumerate", help="Dump redacted Login/Password item metadata")
    sp.add_argument("--output", required=True, help="Output JSONL path")
    sp.set_defaults(func=cmd_enumerate)

    sp = sub.add_parser("match", help="Match target titles against an enumerate dump")
    sp.add_argument("--enumerated", required=True, help="JSONL from `enumerate`")
    sp.add_argument("--titles", required=True, help="Text file, one passkey item title per line")
    sp.add_argument("--output", required=True, help="Output JSON path")
    sp.set_defaults(func=cmd_match)

    sp = sub.add_parser("report", help="Render the Markdown tracker from a match result")
    sp.add_argument("--matched", required=True, help="JSON from `match`")
    sp.add_argument("--previous", help="Existing tracker to preserve ✅/🚫 status + notes from")
    sp.add_argument("--output", required=True, help="Markdown output path")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("scan", help="token -> enumerate -> match -> report")
    sp.add_argument("--titles", required=True, help="Text file, one passkey item title per line")
    sp.add_argument("--previous", help="Existing tracker to preserve ✅/🚫 status + notes from")
    sp.add_argument("--output", required=True, help="Markdown output path")
    sp.set_defaults(func=cmd_scan)

    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except CliError as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
