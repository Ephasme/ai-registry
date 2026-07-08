#!/usr/bin/env python3
"""Upsert a (target, project) -> remote-path mapping into the handoff
project cache (~/.handoff/projects.tsv), so --move doesn't need to
re-search the remote filesystem next time.

Called automatically by resolve_project.py on an unambiguous match, and
manually after a human disambiguates a multi-match result.

Usage:
    record_project.py <target> <project> <remote-path>

Writes are flock-guarded and go through a temp-file-then-rename so a
concurrent writer or an interrupted write can't corrupt or lose the
existing cache.
"""
import argparse
import fcntl
import os
import sys
from pathlib import Path

CACHE_PATH = Path.home() / ".handoff" / "projects.tsv"


def upsert(target, project, remote_path, cache_path=CACHE_PATH):
    for name, value in (("target", target), ("project", project), ("remote_path", remote_path)):
        if "\t" in value or "\n" in value:
            raise ValueError(
                f"{name} contains a tab or newline, which would corrupt the "
                f"tab-separated cache: {value!r}"
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = cache_path.with_name(cache_path.name + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            lines = []
            if cache_path.exists():
                for line in cache_path.read_text().splitlines():
                    if not line.strip():
                        continue
                    fields = line.split("\t")
                    if len(fields) >= 2 and fields[0] == target and fields[1] == project:
                        continue
                    lines.append(line)
            lines.append(f"{target}\t{project}\t{remote_path}")

            tmp_path = cache_path.with_name(f"{cache_path.name}.tmp{os.getpid()}")
            tmp_path.write_text("\n".join(lines) + "\n")
            tmp_path.replace(cache_path)  # atomic rename on POSIX
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("project")
    parser.add_argument("remote_path")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 64

    try:
        upsert(args.target, args.project, args.remote_path)
    except ValueError as e:
        print(f"record_project.py: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
