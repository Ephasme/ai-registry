#!/usr/bin/env python3
"""Set Claude Code plugin userConfig values from the shell -- no interactive TUI.

Wraps `claude plugin install <id> --config KEY=VALUE`, which stores each value
through the exact same path as the interactive /plugin configure flow (sensitive
-> keychain, plain -> settings.json), validated against the plugin's schema. On
top of that this script:

  - refreshes the marketplace cache first (default on), so the *installed*
    manifest's sensitive flags are current -- the installed manifest, not the
    repo, decides where a value is stored, so a stale one silently sends a
    secret to the wrong place;
  - runs across one or more CLAUDE_CONFIG_DIR profiles in a single call;
  - warns about keys you set that the manifest doesn't declare;
  - optionally diffs the macOS keychain around the change to reveal where a
    sensitive value actually landed (--keychain-probe);
  - re-runs the diagnosis afterward so you can see the result.

Secret hygiene: prefer --config-from-env KEY (reads the value from environment
variable KEY) so the secret stays out of your shell history. Note the value is
still passed as an argument to the underlying `claude` process, so it may be
briefly visible to `ps` -- that's a property of the CLI, not this wrapper.

Usage:
    # value inline (ends up in shell history -- fine for non-secrets / throwaways)
    set_config.py mcp-servers@ai-registry --config CF_ACCESS_CLIENT_ID=abc.access

    # value from the environment (preferred for secrets)
    export CF_ACCESS_CLIENT_SECRET=...   # e.g. from `sops -d`, a vault, etc.
    set_config.py mcp-servers@ai-registry \\
        --config-from-env CF_ACCESS_CLIENT_SECRET \\
        --config-dir ~/.claude-perso --config-dir ~/.claude-work \\
        --keychain-probe

    # see exactly what would run, with secrets masked
    set_config.py my-plugin@mkt --config-from-env API_KEY --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import _common as c
import diagnose  # type: ignore[reportMissingImports]

try:
    import keychain_probe  # type: ignore[reportMissingImports]
except ImportError:  # pragma: no cover
    keychain_probe = None  # type: ignore[assignment]


def _parse_kv(pairs: Optional[List[str]]) -> List[Tuple[str, str]]:
    out = []
    for raw in pairs or []:
        if "=" not in raw:
            sys.exit(f"error: --config expects KEY=VALUE, got: {raw!r}")
        k, v = raw.split("=", 1)
        if not k:
            sys.exit(f"error: empty key in --config {raw!r}")
        out.append((k, v))
    return out


def _from_env(keys: Optional[List[str]]) -> List[Tuple[str, str]]:
    out = []
    for k in keys or []:
        if k not in os.environ:
            sys.exit(f"error: --config-from-env {k}: environment variable not set")
        out.append((k, os.environ[k]))
    return out


def _run(cmd: List[str], env: Dict[str, str]) -> int:
    return subprocess.run(cmd, env=env).returncode


def set_in_dir(
    config_dir: Path,
    plugin_id: str,
    values: List[Tuple[str, str]],
    *,
    update_marketplace: bool,
    keychain_probe_on: bool,
    scope: str,
    dry_run: bool,
) -> bool:
    plugin_name, marketplace = c.parse_plugin_id(plugin_id)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    claude = shutil.which("claude")
    if not claude and not dry_run:
        sys.exit("error: `claude` not found on PATH.")
    claude = claude or "claude"

    print(f"\n=== {plugin_id}  @  {config_dir} ===")

    # 1. Refresh the marketplace so the installed manifest's sensitive flags match
    #    the source. Skipped on --no-update-marketplace or when we can't tell the
    #    marketplace name (no @ in the id).
    if update_marketplace and marketplace:
        mk = [claude, "plugin", "marketplace", "update", marketplace]
        print("  $ " + " ".join(mk))
        if not dry_run:
            _run(mk, env)
    elif update_marketplace and not marketplace:
        print("  (skipping marketplace update: no @marketplace in the plugin id)")

    # 2. Show where each value will land, per the (now-current) installed manifest.
    _, manifest = c.resolve_manifest(config_dir, plugin_name, marketplace)
    user_config = c.manifest_user_config(manifest)
    for key, _ in values:
        spec = user_config.get(key)
        if spec is None:
            print(f"  ⚠ {key}: not declared in this plugin's userConfig "
                  "(claude will reject it unless the manifest declares it).")
        else:
            dest = (c.sensitive_store_label() if spec.get("sensitive")
                    else "settings.json")
            print(f"  • {key} -> {dest}")

    # 3. Snapshot keychain (before) if asked.
    before = None
    if keychain_probe_on and keychain_probe and c.is_macos():
        before = keychain_probe.snapshot_items()

    # 4. The actual non-interactive set.
    cmd = [claude, "plugin", "install", plugin_id, "--scope", scope]
    shown = list(cmd)
    for key, val in values:
        cmd += ["--config", f"{key}={val}"]
        shown += ["--config", f"{key}={c.mask(val)}"]
    print("  $ " + " ".join(shown))
    if dry_run:
        print("  (dry run -- not executed)")
        return True
    rc = _run(cmd, env)
    if rc != 0:
        print(f"  ! claude exited {rc}")
        return False

    # 5. Keychain diff (after).
    if before is not None and keychain_probe is not None:
        after = keychain_probe.snapshot_items()
        added = sorted(after - before)
        if added:
            print("  keychain entries added (likely where the secret landed):")
            for line in added:
                print("      " + line.replace("\t", "  "))
        else:
            print("  keychain: no new entry (updated in place, or stored in "
                  ".credentials.json).")
    return True


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugin_id", help='plugin, e.g. "name@marketplace"')
    parser.add_argument("--config", action="append", metavar="KEY=VALUE",
                        help="set a value inline (repeatable)")
    parser.add_argument("--config-from-env", action="append", metavar="KEY",
                        help="set KEY from environment variable KEY (repeatable; "
                             "preferred for secrets)")
    parser.add_argument("--config-dir", action="append",
                        help="target config dir (repeatable; default: "
                             "$CLAUDE_CONFIG_DIR or ~/.claude)")
    parser.add_argument("--scope", default="user",
                        choices=["user", "project", "local"],
                        help="installation scope (default: user)")
    parser.add_argument("--no-update-marketplace", action="store_true",
                        help="don't refresh the marketplace cache first")
    parser.add_argument("--keychain-probe", action="store_true",
                        help="diff the macOS keychain around the change")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip the post-set diagnosis")
    parser.add_argument("--dry-run", action="store_true",
                        help="print commands (secrets masked) without running")
    args = parser.parse_args(argv)

    values = _parse_kv(args.config) + _from_env(args.config_from_env)
    if not values:
        sys.exit("error: nothing to set -- pass --config or --config-from-env.")

    dirs = c.resolve_config_dirs(args.config_dir)
    ok = True
    for d in dirs:
        ok = set_in_dir(
            d, args.plugin_id, values,
            update_marketplace=not args.no_update_marketplace,
            keychain_probe_on=args.keychain_probe,
            scope=args.scope,
            dry_run=args.dry_run,
        ) and ok

    if not args.dry_run and not args.no_verify:
        print("\n--- verification ---")
        for d in dirs:
            diagnose.print_report(diagnose.diagnose_one(d, args.plugin_id))
        if c.is_macos():
            print("\nNote: on macOS sensitive values can't be read back by name, "
                  "so a [sensitive] field with no warning just means no plaintext "
                  "copy is lingering -- not proof the keychain write succeeded. "
                  "Confirm by checking the plugin works (its MCP server connects).")
        else:
            print("\nNote: a 'set' status for a [sensitive] field means the key is "
                  "present in .credentials.json (not the value) -- strong, but the "
                  "decisive check is still that the plugin's MCP server connects.")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
