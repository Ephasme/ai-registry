#!/usr/bin/env python3
"""Extract an already-sent handoff archive into a project directory on the
remote machine, then remove the archive.

Used by the handoff skill's --move option, after send.py has copied the
archive to a directory on <target>.

Usage:
    unpack_remote.py <target> <remote-archive-path> <remote-project-path>

remote-archive-path is the exact path send.py printed, e.g.
/tmp/tmp.Ab12Cd/handoff-topic-2026-07-08.tar.gz.
remote-project-path is the remote project directory to unpack into -- must
already exist (resolve_project.py finds it). Prints
"<target>:<remote-project-path>/<pack-name>" to stdout on success, where
<pack-name> is read from the archive's actual top-level tar entry (not
guessed from the archive's filename, which can diverge from it).
"""
import argparse
import shlex
import subprocess
import sys

SSH_OPTS = ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


def validate_target(target):
    if target.startswith("-"):
        print(f"unpack_remote.py: refusing target that looks like an option (starts with '-'): {target!r}", file=sys.stderr)
        return False
    return True


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("remote_archive")
    parser.add_argument("remote_project")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 64

    if not validate_target(args.target):
        return 1

    check = subprocess.run(
        ["ssh", *SSH_OPTS, "--", args.target, f"test -d {shlex.quote(args.remote_project)}"],
        capture_output=True, text=True,
    )
    if check.returncode != 0:
        detail = check.stderr.strip()
        print(
            f"unpack_remote.py: project directory not found on "
            f"{args.target}: {args.remote_project}"
            + (f" ({detail})" if detail else ""),
            file=sys.stderr,
        )
        return 1

    # List the archive's actual top-level entry (its name is what pack.py
    # named the staging dir, which need not match the archive's own
    # filename) in the same round-trip as extracting and cleaning up.
    cmd = (
        f"tar -tzf {shlex.quote(args.remote_archive)} | head -1 && "
        f"tar -xzf {shlex.quote(args.remote_archive)} -C {shlex.quote(args.remote_project)} "
        f"&& rm -f {shlex.quote(args.remote_archive)}"
    )
    result = subprocess.run(["ssh", *SSH_OPTS, "--", args.target, cmd], capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip()
        print(
            f"unpack_remote.py: extraction failed (exit {result.returncode})"
            + (f": {detail}" if detail else ""),
            file=sys.stderr,
        )
        return result.returncode

    first_line = result.stdout.split("\n", 1)[0]
    pack_name = first_line.rstrip("/")

    print(f"{args.target}:{args.remote_project}/{pack_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
