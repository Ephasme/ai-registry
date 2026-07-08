#!/usr/bin/env python3
"""Archive a prepared handoff staging directory into the OS temp dir.

Used by the handoff skill's --output=pack mode once the staging directory
has been populated with handoff.md plus whatever local files/snapshots it
references. This only does the mechanical tar+cleanup part, not deciding
what belongs in the pack.

Usage:
    pack.py <staging-dir>

staging-dir is a directory named handoff-<topic>-YYYY-MM-DD, already
populated with the files the pack should contain. Prints the resulting
.tar.gz path to stdout on success.
"""
import argparse
import os
import shutil
import sys
import tarfile
from pathlib import Path


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_dir", type=Path)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 64

    staging_dir = args.staging_dir
    if not staging_dir.is_dir():
        print(f"pack.py: not a directory: {staging_dir}", file=sys.stderr)
        return 1

    name = staging_dir.resolve().name
    if not name.startswith("handoff-"):
        print(
            f"pack.py: refusing to archive/remove a directory not named "
            f"handoff-<topic>-<date>: {staging_dir}",
            file=sys.stderr,
        )
        return 1

    outdir = Path(os.environ.get("TMPDIR", "/tmp"))
    archive = outdir / f"{name}.tar.gz"

    try:
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(staging_dir.resolve(), arcname=name)
    except Exception as e:
        archive.unlink(missing_ok=True)
        print(f"pack.py: failed to create archive: {e}", file=sys.stderr)
        return 1

    shutil.rmtree(staging_dir)

    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
