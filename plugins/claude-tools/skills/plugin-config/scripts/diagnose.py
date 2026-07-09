#!/usr/bin/env python3
"""Report where a Claude Code plugin's userConfig values live -- and flag trouble.

For a given plugin (and one or more config dirs), this prints each declared
userConfig field, whether the installed manifest marks it sensitive, where its
value currently sits, and any mismatch that would make ${user_config.KEY}
resolve empty at runtime.

The classic failure this catches: a field marked ``sensitive: true`` whose value
is sitting in plaintext settings.json. Claude Code reads sensitive values from
the keychain, so the settings.json copy is ignored (and gets wiped if your
settings.json is regenerated from a template) -- the plugin then sees an empty
value and its MCP server fails to authenticate.

Usage:
    diagnose.py mcp-servers@ai-registry
    diagnose.py exa-search                       # marketplace auto-detected
    diagnose.py my-plugin@mkt --config-dir ~/.claude-work --config-dir ~/.claude-perso
    diagnose.py my-plugin@mkt --json

Read-only. Never prints secret values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

import _common as c

try:
    import keychain_probe  # type: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - same dir, should always import
    keychain_probe = None  # type: ignore[assignment]


def _keychain_candidates(plugin_name: str, marketplace, keys: List[str]) -> List[str]:
    """Best-effort: keychain entry NAMES that mention this plugin/marketplace/keys.

    Names only -- no secret values. Purely a hint; absence proves nothing because
    Claude Code's naming for plugin secrets is undocumented and may be opaque.
    """
    if keychain_probe is None or not c.is_macos():
        return []
    needles = [n.lower() for n in [plugin_name, marketplace, *keys] if n]
    hits = []
    for line in keychain_probe.snapshot_items():
        low = line.lower()
        if any(n in low for n in needles):
            hits.append(line.replace("\t", "  "))
    return hits


def diagnose_one(config_dir: Path, plugin_id: str) -> dict:
    plugin_name, marketplace = c.parse_plugin_id(plugin_id)
    resolved_market, manifest = c.resolve_manifest(config_dir, plugin_name, marketplace)
    market = marketplace or resolved_market
    full_id = c.full_plugin_id(plugin_name, market)
    user_config = c.manifest_user_config(manifest)

    # Merge options across settings files, remembering which file held each key.
    option_source = {}  # key -> filename
    for fname, opts in c.read_settings_options(config_dir, full_id):
        for k in opts:
            option_source.setdefault(k, fname)

    keys = list(user_config.keys())
    creds = c.credentials_state(config_dir, plugin_name, keys)
    # On Linux/headless the sensitive store (.credentials.json) is parseable, so
    # we can *confirm* a sensitive field is set rather than guess. None means the
    # store is opaque here (macOS keychain, or file absent/unreadable).
    cred_keys = c.credentials_secret_keys(config_dir, full_id)
    store = c.sensitive_store_label()

    fields = []
    for key, spec in user_config.items():
        sensitive = bool(spec.get("sensitive"))
        in_settings = key in option_source
        in_creds = cred_keys is not None and key in cred_keys
        warnings = []
        # status: set | unset | mismatch | unknown
        if sensitive:
            if in_settings:
                status = "mismatch"
                warnings.append(
                    f"value is in plaintext {option_source[key]} but the field is "
                    f"sensitive -> Claude Code reads it from {store}, so this copy "
                    "is IGNORED (and will be wiped if settings.json is "
                    "regenerated). Re-set it with set_config.py."
                )
            elif in_creds:
                status = "set"  # confirmed present in .credentials.json
            elif cred_keys is not None:
                status = "unset"
                warnings.append(f"not present in {store} -> currently unset.")
            else:
                status = "unknown"
                warnings.append(
                    f"sensitive -> expected in the {store}; can't confirm by name "
                    "here. Use keychain_probe.py, or just (re)set it to be sure."
                )
        else:
            if in_settings:
                status = "set"
            else:
                status = "unset"
                warnings.append("not set in settings.json -> currently unset.")
        fields.append({
            "key": key,
            "sensitive": sensitive,
            "status": status,
            "expected_store": f"{store} (sensitive)" if sensitive
            else "settings.json pluginConfigs",
            "in_settings": in_settings,
            "in_credentials": in_creds,
            "settings_file": option_source.get(key),
            "warnings": warnings,
        })

    stray = sorted(set(option_source) - set(user_config))
    return {
        "config_dir": str(config_dir),
        "plugin_id": full_id,
        "marketplace": market,
        "manifest": str(manifest) if manifest else None,
        "fields": fields,
        "stray_options": stray,
        "credentials": creds,
        "keychain_candidates": _keychain_candidates(plugin_name, market, keys),
    }


def print_report(rep: dict) -> None:
    print(f"\n=== {rep['plugin_id']}  @  {rep['config_dir']} ===")
    if not rep["manifest"]:
        print("  ! installed manifest not found in this config dir.")
        print("    Is the plugin installed here, and the marketplace cached?")
        print("    Try: claude plugin marketplace update <marketplace>")
        return
    print(f"  manifest: {rep['manifest']}")
    if not rep["fields"]:
        print("  (plugin declares no userConfig fields)")
    icon = {"set": "✓", "unset": "·", "mismatch": "⚠", "unknown": "?"}
    for f in rep["fields"]:
        flag = "sensitive" if f["sensitive"] else "plain"
        st = f.get("status", "unknown")
        if f["sensitive"]:
            where = (f["settings_file"] if f["in_settings"]
                     else (".credentials.json" if f.get("in_credentials") else "—"))
        else:
            where = f["settings_file"] if f["in_settings"] else "—"
        print(f"\n  {icon.get(st, '?')} {f['key']}  [{flag}]  {st}")
        print(f"      expected store : {f['expected_store']}")
        print(f"      found in       : {where}")
        for w in f["warnings"]:
            print(f"      ⚠ {w}")
    if rep["stray_options"]:
        print(f"\n  stray options in settings (not declared in manifest): "
              f"{', '.join(rep['stray_options'])}")
    cr = rep["credentials"]
    print(f"\n  .credentials.json: {'present' if cr['exists'] else 'absent'} "
          f"({cr['path']})")
    if cr["mentions"]:
        print(f"      mentions: {', '.join(cr['mentions'])}")
    if rep["keychain_candidates"]:
        print("  keychain entries mentioning this plugin (names only):")
        for line in rep["keychain_candidates"]:
            print(f"      {line}")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugin_id", help='plugin, e.g. "name@marketplace" or "name"')
    parser.add_argument("--config-dir", action="append",
                        help="config dir to inspect (repeatable; default: "
                             "$CLAUDE_CONFIG_DIR or ~/.claude)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    reports = [diagnose_one(d, args.plugin_id)
               for d in c.resolve_config_dirs(args.config_dir)]

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for rep in reports:
            print_report(rep)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
