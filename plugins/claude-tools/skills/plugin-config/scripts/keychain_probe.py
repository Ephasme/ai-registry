#!/usr/bin/env python3
"""Discover where Claude Code stores plugin secrets in the macOS keychain.

The keychain service/account naming Claude Code uses for sensitive plugin
userConfig values is undocumented, so you can't reliably look an entry up by
name. This script sidesteps that: snapshot the keychain's generic-password
*attributes* (service + account only -- never the secret), set a value, snapshot
again, and diff. Whatever appears is where Claude Code put it.

Only item NAMES are read (`security dump-keychain` without -d/-g), so no secret
ever leaves the keychain.

Usage:
    # capture the current set of generic-password entries
    keychain_probe.py snapshot -o before.txt

    # ...set a plugin secret some other way (e.g. set_config.py)...

    keychain_probe.py snapshot -o after.txt
    keychain_probe.py diff before.txt after.txt      # shows added/removed items

macOS only.
"""

from __future__ import annotations

import argparse
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import List, NoReturn, Set


def _fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def snapshot_items(keychain: str = "") -> Set[str]:
    """Return a set of "svce=<service>\\tacct=<account>" lines for genp items.

    `keychain` may be a path; empty means the default search list (covers the
    login keychain). Secret data is never requested.
    """
    if platform.system() != "Darwin":
        _fail("keychain_probe only works on macOS (uses the `security` tool).")

    cmd = ["security", "dump-keychain"]
    if keychain:
        cmd.append(keychain)
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout
    except FileNotFoundError:
        _fail("`security` not found -- are you on macOS?")

    items: Set[str] = set()
    svce_re = re.compile(r'"svce"<blob>="((?:[^"\\]|\\.)*)"')
    acct_re = re.compile(r'"acct"<blob>="((?:[^"\\]|\\.)*)"')
    # Each keychain item begins with a line `keychain: "..."`.
    for block in re.split(r"(?m)^keychain: ", out)[1:]:
        if 'class: "genp"' not in block:
            continue
        svce = svce_re.search(block)
        acct = acct_re.search(block)
        items.add(f"svce={svce.group(1) if svce else ''}\tacct={acct.group(1) if acct else ''}")
    return items


def _read_lines(path: Path) -> Set[str]:
    try:
        return {ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")


def _print_items(items: List[str], indent: str = "  ") -> None:
    for line in sorted(items):
        svce, _, acct = line.partition("\t")
        print(f"{indent}{svce:<48} {acct}")


def cmd_snapshot(args: argparse.Namespace) -> int:
    items = snapshot_items(args.keychain or "")
    text = "\n".join(sorted(items))
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {len(items)} generic-password entries to {args.output}")
    else:
        print(text)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    before = _read_lines(Path(args.before))
    after = _read_lines(Path(args.after))
    added = after - before
    removed = before - after
    if added:
        print(f"+ added ({len(added)}) -- likely where the secret landed:")
        _print_items(list(added))
    if removed:
        print(f"- removed ({len(removed)}):")
        _print_items(list(removed))
    if not added and not removed:
        print("no change in generic-password entries.")
        print("the value may have updated an existing item in place (same service")
        print("+ account), or gone to ~/.claude*/.credentials.json instead.")
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="dump current genp entry names")
    p_snap.add_argument("-o", "--output", help="write to this file instead of stdout")
    p_snap.add_argument("--keychain", help="keychain path (default: search list)")
    p_snap.set_defaults(func=cmd_snapshot)

    p_diff = sub.add_parser("diff", help="show entries added/removed between two snapshots")
    p_diff.add_argument("before")
    p_diff.add_argument("after")
    p_diff.set_defaults(func=cmd_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
