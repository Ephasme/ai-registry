#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
bulk-install — discover git repos and install the `air` / `sair` plugin
marketplaces into the ones you pick.

Two steps, matching the request:

  1. Discovery. Walk a root (default ~/code) and list every git repo found,
     each with a per-repo checkbox for AIR, SAIR, and DEL. Defaults follow a
     simple path rule: repos under perso/ start with AIR; repos under sherpas*/
     start with AIR + SAIR.
  2. Act. For every selected repo, run the chosen action(s):

         air  ->  $AI_REGISTRY_DIR/scripts/ai-registry.sh install      (public)
         sair ->  $SHERPAS_REGISTRY_DIR/scripts/sherpas.sh install     (private)
         del  ->  DELETE the entire repo directory from disk, no install

(air/sair first remove the repo-local .claude/, then install into a fresh one.
 DEL is different: it removes the whole repo, .git and all.)

Both installers add their marketplace and install all its plugins into the
repo's local .claude/ at project scope (overridable with --scope).

Usage:
  ./scripts/bulk-install.py [--root DIR ...] [--scope project|user|local]
                            [--depth N] [--dry-run] [--yes]

Keys in the picker:
  up/down (or j/k) move      left/right (or h/l) switch column
  space  toggle the focused cell      a / s / d  toggle AIR / SAIR / DEL on the row
  A / S / D  toggle the whole AIR / SAIR / DEL column
  g / G  jump to top / bottom         enter  confirm        q / esc  cancel
"""
from __future__ import annotations

import argparse
import curses
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()

# Installer locations mirror the `air` / `sair` shell aliases (~/.zshrc), and
# honor the same env overrides so this stays in sync with them.
AIR_SCRIPT = Path(
    os.environ.get("AI_REGISTRY_DIR", str(HOME / "code/perso/ai-registry"))
) / "scripts/ai-registry.sh"
SAIR_SCRIPT = Path(
    os.environ.get("SHERPAS_REGISTRY_DIR", str(HOME / "code/perso/sherpas-ai-registry-loup"))
) / "scripts/sherpas.sh"

# Dirs that whole-repo DELETE must never touch (would self-destruct the tooling):
# the two registry repos and the repo this script lives in.
def _repo_of(p: Path) -> Path:
    return p.resolve().parent.parent  # scripts/<x>.sh -> registry repo root

GUARD_DIRS = {_repo_of(AIR_SCRIPT), _repo_of(SAIR_SCRIPT), Path(__file__).resolve().parent.parent}

DEFAULT_ROOTS = [HOME / "code"]

# Directories we never descend into while scanning (speed + noise control).
PRUNE = {
    "node_modules", ".venv", "venv", "env", ".direnv", "Library", ".cache",
    "dist", "build", ".next", "out", "target", ".gradle", "Pods",
    ".terraform", "__pycache__", "vendor", "DerivedData",
}


def tilde(p: Path | str) -> str:
    """Render a path with $HOME collapsed to ~ for compact display."""
    s = str(p)
    h = str(HOME)
    return "~" + s[len(h):] if s == h or s.startswith(h + os.sep) else s


# --------------------------------------------------------------------------- #
# 1. Discovery
# --------------------------------------------------------------------------- #
def discover(roots: list[Path], max_depth: int | None) -> list[Path]:
    """Find git repos (dirs containing a .git entry) under the given roots.

    A repo is not descended into, so nested submodules are not listed
    separately. Hidden dirs and the PRUNE set are skipped for speed.
    """
    repos: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            print(f"warning: root '{tilde(root)}' is not a directory; skipping", file=sys.stderr)
            continue
        base = len(root.resolve().parts)
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            p = Path(dirpath)
            # A .git dir (normal repo) or .git file (worktree/submodule) marks a repo.
            if ".git" in dirnames or ".git" in filenames:
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    repos.append(p)
                dirnames[:] = []  # stop descending into the repo
                continue
            if max_depth is not None and len(p.resolve().parts) - base >= max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in PRUNE and not d.startswith(".")]
    repos.sort(key=lambda x: str(x).lower())
    return repos


@dataclass
class Row:
    path: Path
    air: bool = False
    sair: bool = False
    delete: bool = False  # delete the ENTIRE repo directory from disk (no install)

    @property
    def selected(self) -> bool:
        return self.air or self.sair or self.delete


def default_selection(path: Path) -> tuple[bool, bool]:
    """Simple path rule for the initial (air, sair) checkbox state.

    A repo under a 'perso' dir gets AIR only; one under a 'sherpas*' dir gets
    AIR + SAIR. The perso check wins, so e.g. perso/sherpas-ai-registry-loup is
    treated as perso (air only). Anything else starts unchecked.
    """
    parts = [p.lower() for p in path.parts]
    if "perso" in parts:
        return (True, False)
    if any(p.startswith("sherpas") for p in parts):
        return (True, True)
    return (False, False)


# --------------------------------------------------------------------------- #
# 2. Selection — curses picker (with a plain-text fallback)
# --------------------------------------------------------------------------- #
def pick_curses(rows: list[Row]) -> bool:
    """Interactive two-column checkbox grid. Returns True on confirm."""
    def _ui(stdscr) -> bool:
        curses.curs_set(0)
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        cur, col, top = 0, 0, 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            n_air = sum(r.air for r in rows)
            n_sair = sum(r.sair for r in rows)
            n_del = sum(r.delete for r in rows)
            stdscr.addnstr(0, 0, f"Discovered {len(rows)} repos", w - 1, curses.A_BOLD)
            help1 = "up/down move  left/right col  space toggle  a/s/d row  A/S/D column"
            help2 = "g/G top/bottom  enter confirm  q cancel   -  DEL = delete ENTIRE repo!"
            stdscr.addnstr(1, 0, help1, w - 1, curses.A_DIM)
            stdscr.addnstr(2, 0, help2, w - 1, curses.A_DIM)
            stdscr.addnstr(3, 0, "    AIR  SAIR DEL  REPO", w - 1, curses.A_UNDERLINE)

            list_top, list_h = 4, max(1, h - 5)
            if cur < top:
                top = cur
            elif cur >= top + list_h:
                top = cur - list_h + 1

            for i in range(top, min(top + list_h, len(rows))):
                r = rows[i]
                y = list_top + (i - top)
                focused = i == cur
                rowattr = curses.A_BOLD if focused else curses.A_NORMAL

                def cell(c: int) -> int:
                    if focused and col == c:
                        return curses.A_REVERSE
                    return rowattr

                stdscr.addstr(y, 0, " > " if focused else "   ", rowattr)
                stdscr.addstr(y, 4, "[x]" if r.air else "[ ]", cell(0))
                stdscr.addstr(y, 9, "[x]" if r.sair else "[ ]", cell(1))
                stdscr.addstr(y, 14, "[x]" if r.delete else "[ ]", cell(2))
                stdscr.addnstr(y, 19, tilde(r.path), max(1, w - 20), rowattr)

            footer = f"selected: AIR={n_air}  SAIR={n_sair}  DEL={n_del}   ({cur + 1}/{len(rows)})"
            stdscr.addnstr(h - 1, 0, footer, w - 1, curses.A_DIM)
            stdscr.refresh()

            k = stdscr.getch()
            if k in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                cur = min(len(rows) - 1, cur + 1)
            elif k in (curses.KEY_LEFT, ord("h")):
                col = max(0, col - 1)
            elif k in (curses.KEY_RIGHT, ord("l")):
                col = min(2, col + 1)
            elif k in (curses.KEY_NPAGE,):
                cur = min(len(rows) - 1, cur + list_h)
            elif k in (curses.KEY_PPAGE,):
                cur = max(0, cur - list_h)
            elif k == ord("g"):
                cur = 0
            elif k == ord("G"):
                cur = len(rows) - 1
            elif k == ord(" "):
                attr = ("air", "sair", "delete")[col]
                setattr(rows[cur], attr, not getattr(rows[cur], attr))
            elif k == ord("a"):
                rows[cur].air = not rows[cur].air
            elif k == ord("s"):
                rows[cur].sair = not rows[cur].sair
            elif k == ord("d"):
                rows[cur].delete = not rows[cur].delete
            elif k == ord("A"):
                v = not all(r.air for r in rows)
                for r in rows:
                    r.air = v
            elif k == ord("S"):
                v = not all(r.sair for r in rows)
                for r in rows:
                    r.sair = v
            elif k == ord("D"):
                v = not all(r.delete for r in rows)
                for r in rows:
                    r.delete = v
            elif k in (curses.KEY_ENTER, 10, 13):
                return True
            elif k in (ord("q"), 27):
                return False

    return curses.wrapper(_ui)


def parse_nums(s: str, n: int) -> set[int]:
    if s.strip().lower() in ("all", "*"):
        return set(range(n))
    out: set[int] = set()
    for tok in s.replace(",", " ").split():
        if tok.isdigit():
            i = int(tok) - 1
            if 0 <= i < n:
                out.add(i)
    return out


def pick_text(rows: list[Row]) -> bool:
    """Fallback selector for when there is no usable TTY for curses."""
    for i, r in enumerate(rows):
        tags = ",".join(t for t, on in (("air", r.air), ("sair", r.sair), ("del", r.delete)) if on)
        print(f"{i + 1:3}  [{tags:<8}] {tilde(r.path)}")
    print("\n(blank keeps the [defaults] shown above; numbers REPLACE that column's selection)")
    air = input("AIR install #s?  (e.g. '1 3 5', 'all', 'none', blank=keep): ").strip()
    if air:
        sel = parse_nums(air, len(rows))
        for i, r in enumerate(rows):
            r.air = i in sel
    sair = input("SAIR install #s? (e.g. '1 3 5', 'all', 'none', blank=keep): ").strip()
    if sair:
        sel = parse_nums(sair, len(rows))
        for i, r in enumerate(rows):
            r.sair = i in sel
    dele = input("DELETE ENTIRE REPO #s? (whole dir, .git and all; 'all', 'none', blank=keep): ").strip()
    if dele:
        sel = parse_nums(dele, len(rows))
        for i, r in enumerate(rows):
            r.delete = i in sel
    return True


# --------------------------------------------------------------------------- #
# 3. Install
# --------------------------------------------------------------------------- #
def nuke_claude(repo: Path, dry: bool) -> None:
    """Remove the repo-local .claude/ before installing. --dry-run only previews.

    The line is always printed so the preview is accurate, with a note when
    there is no .claude to remove.
    """
    claude = repo / ".claude"
    present = claude.exists() or claude.is_symlink()
    suffix = "" if present else "  (not present, nothing to do)"
    print(f"    nuke   {tilde(claude)}{suffix}")
    if dry or not present:
        return
    if claude.is_symlink():
        claude.unlink()
    else:
        shutil.rmtree(claude)


def deletion_blocker(repo: Path, roots: list[Path]) -> str | None:
    """Return a reason DELETE must be refused for this repo, else None.

    Guards against deleting system/home roots, a scan root itself, anything not
    under a scan root, and the registry/script dirs (or any ancestor of them).
    """
    rp = repo.resolve()
    if rp == Path("/") or rp == HOME.resolve():
        return "system/home root"
    root_set = {Path(r).expanduser().resolve() for r in roots}
    if rp in root_set:
        return "scan root itself"
    if not any(root in rp.parents for root in root_set):
        return "not under any scan root"
    for guard in GUARD_DIRS:
        if rp == guard or guard in rp.parents or rp in guard.parents:
            return f"would remove the registry/tooling dir {tilde(guard)}"
    return None


def delete_repo(repo: Path, dry: bool) -> None:
    """Delete the ENTIRE repo directory. --dry-run only previews."""
    print(f"    DELETE repo  {tilde(repo)}")
    if dry:
        return
    if repo.is_symlink():
        repo.unlink()
    else:
        shutil.rmtree(repo)


def run_installer(script: Path, scope: str, cwd: Path, dry: bool) -> int:
    cmd = [str(script), "install", scope]
    print(f"    run    {tilde(script)} install {scope}   (cwd={tilde(cwd)})")
    if dry:
        return 0
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Discover git repos and bulk-install the air/sair marketplaces into the ones you pick.",
    )
    ap.add_argument("--root", action="append", type=Path, metavar="DIR",
                    help="root dir to scan (repeatable; default: ~/code)")
    ap.add_argument("--scope", choices=("project", "user", "local"), default="project",
                    help="install scope passed to the installers (default: project)")
    ap.add_argument("--depth", type=int, default=None, metavar="N",
                    help="max directory depth to descend while scanning")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would happen; do not nuke or install")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="skip the final confirmation prompt")
    args = ap.parse_args()

    roots = args.root or DEFAULT_ROOTS
    print(f"==> scanning {', '.join(tilde(r) for r in roots)} ...")
    paths = discover(roots, args.depth)
    if not paths:
        print("No git repos found.")
        return 1
    rows = [Row(p, *default_selection(p)) for p in paths]

    # Pick. Use curses when we have a real terminal on both ends, else text.
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            confirmed = pick_curses(rows)
        except curses.error as e:
            print(f"(curses unavailable: {e}; falling back to text)", file=sys.stderr)
            confirmed = pick_text(rows)
    else:
        confirmed = pick_text(rows)

    if not confirmed:
        print("Cancelled.")
        return 130

    selected = [r for r in rows if r.selected]
    if not selected:
        print("Nothing selected.")
        return 0

    # Validate the installers we are about to run actually exist. A repo marked
    # for whole-repo DELETE is not installed into, so it does not need them.
    need_air = any(r.air and not r.delete for r in selected)
    need_sair = any(r.sair and not r.delete for r in selected)
    if need_air and not AIR_SCRIPT.exists():
        print(f"error: AIR installer not found at {tilde(AIR_SCRIPT)} "
              f"(set $AI_REGISTRY_DIR)", file=sys.stderr)
        return 1
    if need_sair and not SAIR_SCRIPT.exists():
        print(f"error: SAIR installer not found at {tilde(SAIR_SCRIPT)} "
              f"(set $SHERPAS_REGISTRY_DIR)", file=sys.stderr)
        return 1
    if not args.dry_run and (need_air or need_sair):
        for tool in ("claude", "jq"):
            if shutil.which(tool) is None:
                print(f"error: '{tool}' not found on PATH (required by the installers)", file=sys.stderr)
                return 1

    # Plan. Whole-repo deletions are shown loudly and separately.
    del_repos = [r for r in selected if r.delete]
    print(f"\n==> plan ({'DRY RUN' if args.dry_run else 'scope: ' + args.scope}):")
    for r in selected:
        print(f"  {tilde(r.path)}")
        if r.delete:
            extra = "  (install skipped)" if (r.air or r.sair) else ""
            print(f"      will: DELETE THE ENTIRE REPO DIRECTORY{extra}")
        else:
            installs = [t for t, on in (("air", r.air), ("sair", r.sair)) if on]
            print(f"      will: nuke .claude, then install [{','.join(installs)}]")

    # Confirm. Whole-repo deletes are irreversible, so they get a stronger gate.
    if not args.dry_run and not args.yes:
        if del_repos:
            print("\n" + "!" * 70)
            print(f"WARNING: {len(del_repos)} ENTIRE repo director"
                  f"{'y' if len(del_repos) == 1 else 'ies'} will be permanently deleted")
            print("(every file, including .git and any uncommitted/unpushed work):")
            for r in del_repos:
                print(f"    - {tilde(r.path)}")
            print("!" * 70)
            if input("Type DELETE (in caps) to confirm: ").strip() != "DELETE":
                print("Aborted.")
                return 130
        else:
            print("\nThis removes the .claude/ dir in each repo above before installing.")
            if input("Proceed? type 'yes': ").strip().lower() not in ("yes", "y"):
                print("Aborted.")
                return 130

    # Execute.
    failures: list[str] = []
    for r in selected:
        print(f"\n--> {tilde(r.path)}")
        if r.delete:
            blocker = deletion_blocker(r.path, roots)
            if blocker:
                print(f"    SKIP delete: {blocker}")
                failures.append(f"{tilde(r.path)} (delete refused: {blocker})")
                continue
            delete_repo(r.path, args.dry_run)
            continue  # repo is gone; nothing to install
        nuke_claude(r.path, args.dry_run)
        if r.air and run_installer(AIR_SCRIPT, args.scope, r.path, args.dry_run) != 0:
            failures.append(f"{tilde(r.path)} (air)")
        if r.sair and run_installer(SAIR_SCRIPT, args.scope, r.path, args.dry_run) != 0:
            failures.append(f"{tilde(r.path)} (sair)")

    print("\n==> done." + (" (dry run; nothing changed)" if args.dry_run else ""))
    if failures:
        print("Failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
