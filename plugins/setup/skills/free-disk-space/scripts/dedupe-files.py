#!/usr/bin/env python3
"""dedupe-files.py — remove byte-identical duplicate files, keeping one copy.

Only files with the SAME content hash are treated as duplicates. Two files that
merely share a name pattern (e.g. "contract.pdf" and "contract (1).pdf") but
differ in bytes are NOT duplicates and are both kept — important for things like
signed vs unsigned versions of a document.

Within a duplicate group the kept copy is the one with the shortest filename
(originals are usually shorter than "... (1).pdf"). Dry-run by default.

Usage:
  dedupe-files.py <dir>                     dry-run, all files (recursive)
  dedupe-files.py <dir> --apply             delete the redundant copies
  dedupe-files.py <dir> --ext pdf,jpg       only these extensions
  dedupe-files.py <dir> --no-recurse        top level only
"""
import argparse, hashlib, os, sys

def file_hash(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ext", default="", help="comma-separated extensions, e.g. pdf,jpg")
    ap.add_argument("--no-recurse", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.dir):
        sys.exit(f"Not a directory: {a.dir}")
    exts = {e.strip().lower().lstrip(".") for e in a.ext.split(",") if e.strip()}

    files = []
    if a.no_recurse:
        files = [os.path.join(a.dir, f) for f in os.listdir(a.dir)
                 if os.path.isfile(os.path.join(a.dir, f))]
    else:
        for root, _, names in os.walk(a.dir):
            files += [os.path.join(root, n) for n in names]
    if exts:
        files = [f for f in files if f.rsplit(".", 1)[-1].lower() in exts]

    groups = {}
    for f in files:
        try:
            groups.setdefault(file_hash(f), []).append(f)
        except OSError:
            pass

    freed, removed = 0, 0
    for h, fs in groups.items():
        if len(fs) < 2:
            continue
        fs.sort(key=lambda x: (len(os.path.basename(x)), x))  # keep cleanest/shortest name
        keep, dups = fs[0], fs[1:]
        print(f"\nDuplicate group ({len(fs)} copies, hash {h[:10]}…):")
        print(f"  keep:   {keep}")
        for d in dups:
            sz = os.path.getsize(d)
            freed += sz
            print(f"  {'remove' if a.apply else 'would remove'}: {d}  ({sz/1e6:.1f} MB)")
            if a.apply:
                os.remove(d); removed += 1

    print(f"\n{'Removed' if a.apply else 'Would remove'} {removed if a.apply else sum(len(v)-1 for v in groups.values() if len(v)>1)} "
          f"file(s), freeing {freed/1e6:.1f} MB")
    if not a.apply:
        print("(dry-run — re-run with --apply to delete)")

if __name__ == "__main__":
    main()
