#!/usr/bin/env python3
"""Configure MANY plugins at once by auto-routing a pool of values to whichever
plugins declare them -- across one or more config-dir profiles.

Where set_config.py sets one plugin, this is the fleet-scale path: give it a
pool of KEY=VALUE pairs from any mix of sources, and it discovers every
installed plugin, reads each plugin's userConfig schema, and sends each value to
the plugin(s) that actually declare that key. Values with no home and declared
fields with no value are both reported, so nothing silently goes missing.

Every set goes through the same code path as set_config.py / the interactive
dialog (`claude plugin install --config`), so sensitive -> keychain/.credentials
and plain -> settings.json exactly as usual.

VALUE SOURCES (repeatable, combined into one pool; later sources override
earlier on key collision, with a note):

    --config KEY=VALUE          inline (fine for non-secrets; hits shell history)
    --config-from-env KEY       read one value from environment variable KEY
    --from-json FILE            flat {"KEY": "value", ...} JSON. Nested objects
                                and non-string values are ignored (they're not
                                plugin userConfig -- e.g. server-side config).
    --from-sops PATH            a *.sops.json file, or a directory of them,
                                decrypted with the `sops` binary. Same flat-JSON
                                rule as --from-json. Requires `sops` on PATH and
                                a decryption key configured (e.g. an age key at
                                ~/.config/sops/age/keys.txt or $SOPS_AGE_KEY_FILE).
    --env-all                   opportunistically pull any *declared* userConfig
                                key that exists as an env var and isn't already
                                in the pool.

Examples:
    # decrypt a repo's secrets dir and fan the values out to every plugin that
    # wants one, in both profiles:
    export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
    bulk_config.py --from-sops ~/code/ai-registry/secrets \\
        --config-dir ~/.claude-work --config-dir ~/.claude-perso

    # dry-run first to see the routing (secrets masked, nothing written):
    bulk_config.py --from-json /tmp/values.json --dry-run

    # only touch a couple of plugins:
    bulk_config.py --from-sops ./secrets --include research --include engineering

Read-only until it writes: --dry-run shows the full routing plan with secrets
masked. Never prints secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import _common as c
import set_config  # reuse set_in_dir for the actual per-plugin write


# --------------------------------------------------------------------------- #
# Value-pool sources
# --------------------------------------------------------------------------- #

def _flat_string_items(obj: object, origin: str) -> Dict[str, str]:
    """Top-level string entries of a JSON object. Skips nested/non-string values
    (those are not plugin userConfig -- e.g. structured server-side config)."""
    out: Dict[str, str] = {}
    if not isinstance(obj, dict):
        sys.exit(f"error: {origin}: expected a JSON object at top level")
    for k, v in obj.items():
        if isinstance(v, str):
            out[k] = v
    return out


def _load_json_file(path: Path) -> Dict[str, str]:
    data = c.load_json(path)
    if data is None:
        sys.exit(f"error: --from-json {path}: not found or not valid JSON")
    return _flat_string_items(data, f"--from-json {path}")


def _sops_decrypt(path: Path, sops_bin: str) -> Dict[str, str]:
    proc = subprocess.run(
        [sops_bin, "-d", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip().splitlines()
        hint = err[-1] if err else f"sops exited {proc.returncode}"
        sys.exit(f"error: sops could not decrypt {path}: {hint}\n"
                 "       (is the decryption key configured? e.g. "
                 "SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt)")
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        sys.exit(f"error: sops output for {path} was not JSON")
    return _flat_string_items(data, f"--from-sops {path}")


def _load_sops_path(path: Path) -> Dict[str, str]:
    sops_bin = shutil.which("sops")
    if not sops_bin:
        sys.exit("error: --from-sops needs the `sops` binary on PATH "
                 "(https://github.com/getsops/sops/releases).")
    files: List[Path]
    if path.is_dir():
        files = sorted(path.glob("*.sops.json"))
        if not files:
            sys.exit(f"error: --from-sops {path}: no *.sops.json files found")
    elif path.is_file():
        files = [path]
    else:
        sys.exit(f"error: --from-sops {path}: not a file or directory")
    pool: Dict[str, str] = {}
    for f in files:
        for k, v in _sops_decrypt(f, sops_bin).items():
            pool[k] = v
    return pool


def build_pool(args) -> Tuple[Dict[str, str], List[str]]:
    """Merge every source into one KEY->value pool. Returns (pool, notes)."""
    pool: Dict[str, str] = {}
    notes: List[str] = []

    def merge(src_name: str, items: Dict[str, str]) -> None:
        for k, v in items.items():
            if k in pool and pool[k] != v:
                notes.append(f"{k}: value from {src_name} overrides an earlier source")
            pool[k] = v

    for raw in args.config or []:
        if "=" not in raw:
            sys.exit(f"error: --config expects KEY=VALUE, got {raw!r}")
        k, v = raw.split("=", 1)
        merge("--config", {k: v})
    for k in args.config_from_env or []:
        if k not in os.environ:
            sys.exit(f"error: --config-from-env {k}: environment variable not set")
        merge("--config-from-env", {k: os.environ[k]})
    for f in args.from_json or []:
        merge(f"--from-json {f}", _load_json_file(Path(f).expanduser()))
    for p in args.from_sops or []:
        merge(f"--from-sops {p}", _load_sops_path(Path(p).expanduser()))
    return pool, notes


# --------------------------------------------------------------------------- #
# Discovery + routing
# --------------------------------------------------------------------------- #

def _plugin_matches(full_id: str, include: List[str], exclude: List[str]) -> bool:
    name, market = c.parse_plugin_id(full_id)
    hay = {full_id, name}
    if exclude and (hay & set(exclude)):
        return False
    if include and not (hay & set(include)):
        return False
    return True


def _declared_keys(config_dir: Path, full_id: str) -> List[str]:
    name, market = c.parse_plugin_id(full_id)
    _, manifest = c.resolve_manifest(config_dir, name, market)
    return list(c.manifest_user_config(manifest).keys())


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def _refresh_marketplaces(config_dir: Path, markets: List[str], dry_run: bool) -> None:
    claude = shutil.which("claude") or "claude"
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    for m in markets:
        cmd = [claude, "plugin", "marketplace", "update", m]
        print(f"  $ {' '.join(cmd)}")
        if not dry_run:
            subprocess.run(cmd, env=env)


def run_dir(config_dir: Path, pool: Dict[str, str], args) -> dict:
    installed = [p for p in c.list_installed_plugins(config_dir)
                 if _plugin_matches(p, args.include or [], args.exclude or [])]
    print(f"\n########## {config_dir} ##########")
    if not installed:
        print("  (no matching installed plugins found here)")
        return {"config_dir": str(config_dir), "installed": [], "routes": {},
                "used_keys": set(), "unfilled": {}}

    # Refresh each unique marketplace once (not once per plugin).
    if not args.no_update_marketplace:
        markets = sorted({c.parse_plugin_id(p)[1] for p in installed
                          if c.parse_plugin_id(p)[1]})
        _refresh_marketplaces(config_dir, markets, args.dry_run)

    # Opportunistic env pickup: only declared keys, only if not already pooled.
    if args.env_all:
        declared_all = {k for p in installed for k in _declared_keys(config_dir, p)}
        for k in sorted(declared_all):
            if k not in pool and k in os.environ:
                pool[k] = os.environ[k]

    routes: Dict[str, List[str]] = {}
    used: set = set()
    unfilled: Dict[str, List[str]] = {}
    for full_id in installed:
        declared = _declared_keys(config_dir, full_id)
        matched = [k for k in declared if k in pool]
        missing = [k for k in declared if k not in pool]
        if missing:
            unfilled[full_id] = missing
        if not matched:
            continue
        routes[full_id] = matched
        used.update(matched)
        # Reuse set_config's single-plugin writer (marketplace already refreshed).
        set_config.set_in_dir(
            config_dir, full_id,
            [(k, pool[k]) for k in matched],
            update_marketplace=False,
            keychain_probe_on=False,
            scope=args.scope,
            dry_run=args.dry_run,
        )

    return {"config_dir": str(config_dir), "installed": installed,
            "routes": routes, "used_keys": used, "unfilled": unfilled}


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", action="append", metavar="KEY=VALUE",
                        help="inline value (repeatable)")
    parser.add_argument("--config-from-env", action="append", metavar="KEY",
                        help="value from environment variable KEY (repeatable)")
    parser.add_argument("--from-json", action="append", metavar="FILE",
                        help="flat JSON {KEY: value} file (repeatable)")
    parser.add_argument("--from-sops", action="append", metavar="PATH",
                        help="*.sops.json file or dir of them, decrypted via sops "
                             "(repeatable)")
    parser.add_argument("--env-all", action="store_true",
                        help="also pull any declared key present as an env var")
    parser.add_argument("--config-dir", action="append",
                        help="target profile dir (repeatable; default: "
                             "$CLAUDE_CONFIG_DIR or ~/.claude)")
    parser.add_argument("--include", action="append", metavar="PLUGIN",
                        help="only configure these plugins (name or name@market)")
    parser.add_argument("--exclude", action="append", metavar="PLUGIN",
                        help="skip these plugins (name or name@market)")
    parser.add_argument("--scope", default="user",
                        choices=["user", "project", "local"])
    parser.add_argument("--no-update-marketplace", action="store_true",
                        help="don't refresh marketplace caches first")
    parser.add_argument("--dry-run", action="store_true",
                        help="show the routing plan (secrets masked); write nothing")
    args = parser.parse_args(argv)

    pool, notes = build_pool(args)
    if not pool and not args.env_all:
        sys.exit("error: empty value pool -- pass --config / --config-from-env / "
                 "--from-json / --from-sops (or --env-all).")
    print(f"value pool: {len(pool)} key(s): {', '.join(sorted(pool))}")
    for n in notes:
        print(f"  note: {n}")

    dirs = c.resolve_config_dirs(args.config_dir)
    results = [run_dir(d, dict(pool), args) for d in dirs]

    # Summary: homeless keys (matched by no plugin in any dir) + unfilled fields.
    all_used: set = set()
    for r in results:
        all_used |= r["used_keys"]
    homeless = sorted(set(pool) - all_used)

    print("\n========== summary ==========")
    for r in results:
        n_routes = sum(len(v) for v in r["routes"].values())
        print(f"{r['config_dir']}: {len(r['routes'])} plugin(s), "
              f"{n_routes} value(s) routed")
        for pid, keys in sorted(r["routes"].items()):
            print(f"  → {pid}: {', '.join(keys)}")
    if homeless:
        print(f"\nunused pool keys (declared by no installed plugin): "
              f"{', '.join(homeless)}")
        print("  (expected for server-side secrets that aren't plugin userConfig)")
    # Report unfilled declared fields, de-duped across dirs.
    unfilled: Dict[str, set] = {}
    for r in results:
        for pid, keys in r["unfilled"].items():
            unfilled.setdefault(pid, set()).update(keys)
    if unfilled:
        print("\ndeclared fields with no value in the pool (left unset):")
        for pid in sorted(unfilled):
            print(f"  {pid}: {', '.join(sorted(unfilled[pid]))}")

    if args.dry_run:
        print("\n(dry run -- nothing was written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
