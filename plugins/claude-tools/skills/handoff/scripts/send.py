#!/usr/bin/env python3
"""Send a file to a private temp directory on a remote machine.

Typically the .tar.gz produced by pack.py. Prefers rsync and falls back to
scp whenever rsync fails -- whether because it's missing locally or on the
remote -- since the docstring's promise only holds if both sides are
actually probed. Used by the handoff skill's --send=<target> option, which
only applies to --output=pack.

Usage:
    send.py <file> <target>

target is [user@]host. The file lands in a fresh, private directory
created with `mktemp -d` on the remote -- not the shared, world-writable
/tmp directly, which would let another local user on that host pre-plant
a symlink at a predictable path. Prints "<target>:<remote-dir>/<basename>"
to stdout on success. Exits non-zero on transfer failure (bad host, auth
failure, no space on the remote).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SSH_OPTS = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


def validate_target(target):
    if target.startswith("-"):
        print(f"send.py: refusing target that looks like an option (starts with '-'): {target!r}", file=sys.stderr)
        return False
    return True


def remote_staging_dir(target):
    result = subprocess.run(
        ["ssh", *SSH_OPTS, "--", target, "mktemp -d"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip()
        print(f"send.py: couldn't create a staging directory on {target}"
              + (f": {detail}" if detail else ""), file=sys.stderr)
        return None
    return result.stdout.strip()


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("target")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 64

    if not args.file.is_file():
        print(f"send.py: not a file: {args.file}", file=sys.stderr)
        return 1

    if not validate_target(args.target):
        return 1

    staging = remote_staging_dir(args.target)
    if not staging:
        return 1

    dest = f"{args.target}:{staging}/"
    attempts = []
    if shutil.which("rsync"):
        attempts.append(["rsync", "-avz", "-e", f"ssh {' '.join(SSH_OPTS)}", "--", str(args.file), dest])
    attempts.append(["scp", *SSH_OPTS, "--", str(args.file), dest])

    result = subprocess.run(attempts[0])
    for cmd in attempts[1:]:
        if result.returncode == 0:
            break
        result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"send.py: transfer failed (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    print(f"{args.target}:{staging}/{args.file.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
