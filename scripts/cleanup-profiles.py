#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
cleanup-profiles — discover Claude config dirs (CLI and Desktop app) and wipe
their customizations from the ones you pick.

Two steps, like bulk-install.py:

  1. Discovery. Find every Claude profile dir and list them, each with a CLEAN
     checkbox. Scans CLI dirs (~/.claude, ~/.claude-*) and Desktop app dirs
     (~/Library/Application Support/Claude[-*]).
  2. Clean. For every selected profile, remove its customizations and PRESERVE
     auth, sessions, history and editor prefs / app state.

Nothing is hard-deleted: removed items are MOVED into <dir>/backups/cleanup-<TS>/
and edited JSON files are copied there first, so it is reversible.

  CLI dirs:
    REMOVE (moved):   skills/ agents/ commands/ output-styles/ plugins/
    EDIT (stripped):  settings.json -> enabledPlugins, extraKnownMarketplaces,
                                       hooks, outputStyle, statusLine
                      .claude.json  -> mcpServers (top-level + per-project)
  Desktop dirs:
    REMOVE (moved):   Claude Extensions/, Claude Extensions Settings/,
                      extensions-installations.json, extensions-blocklist.json
    EDIT (stripped):  claude_desktop_config.json -> mcpServers
  PRESERVE (untouched): .credentials.json, oauthAccount + rest of .claude.json,
                      projects/ sessions/ tasks/ history.jsonl caches, settings
                      prefs (model/theme/permissions/...), and Desktop app state
                      (Cookies, Local Storage, bundled claude-code runtime, ...).

Usage:
  ./scripts/cleanup-profiles.py [--keep a,b,c] [--dry-run] [--yes]

Keys in the picker:
  up/down (or j/k) move    space (or c) toggle    C toggle all
  g/G top/bottom           enter confirm          q/esc cancel
"""
from __future__ import annotations

import argparse
import curses
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HOME = Path.home()

# Customization subdirs (category name -> human label).
CONTENT_DIRS = {
    "skills": "custom skills",
    "agents": "custom subagents",
    "commands": "custom slash commands",
    "output-styles": "custom output styles",
    "plugins": "installed plugins + marketplaces",
}
# Desktop app (Electron) customizations, removed under the `extensions` category.
DESKTOP_EXT_ITEMS = ["Claude Extensions", "Claude Extensions Settings",
                     "extensions-installations.json", "extensions-blocklist.json"]
# Human labels for everything we may move to backup.
LABELS = {
    **CONTENT_DIRS,
    "Claude Extensions": "desktop extensions",
    "Claude Extensions Settings": "desktop extension settings",
    "extensions-installations.json": "desktop extension registry",
    "extensions-blocklist.json": "desktop extension blocklist",
}
DEFAULT_CATEGORIES = ["skills", "agents", "commands", "output-styles", "plugins",
                      "hooks", "mcp", "extensions"]


def tilde(p: Path | str) -> str:
    s = str(p)
    h = str(HOME)
    return "~" + s[len(h):] if s == h or s.startswith(h + os.sep) else s


def looks_like_profile(t: Path) -> bool:
    return t.is_dir() and (
        t.name.startswith(".claude")
        or (t / ".claude.json").exists()
        or (t / "settings.json").exists()
        or (t / "claude_desktop_config.json").exists()  # Desktop app dir
    )


def is_desktop(t: Path) -> bool:
    return (t / "claude_desktop_config.json").exists() or (t / "Claude Extensions").is_dir()


def describe(item: Path) -> str:
    return LABELS.get(item.name, item.name)


# --------------------------------------------------------------------------- #
# 1. Discovery
# --------------------------------------------------------------------------- #
def discover() -> list[Path]:
    """Find Claude profile dirs: CLI (~/.claude, ~/.claude-*) and Desktop app
    (~/Library/Application Support/Claude[-*]) that look like profiles."""
    appsup = HOME / "Library" / "Application Support"
    candidates = [
        HOME / ".claude", *sorted(HOME.glob(".claude-*")),
        appsup / "Claude", *sorted(appsup.glob("Claude-*")),
    ]
    found: list[Path] = []
    for p in candidates:
        if looks_like_profile(p) and p not in found:
            found.append(p)
    return found


@dataclass
class Row:
    path: Path
    clean: bool = False


# --------------------------------------------------------------------------- #
# 2. Selection — curses picker (with a plain-text fallback)
# --------------------------------------------------------------------------- #
def pick_curses(rows: list[Row], active: Path | None) -> bool:
    def _ui(stdscr) -> bool:
        curses.curs_set(0)
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        cur, top = 0, 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            n = sum(r.clean for r in rows)
            stdscr.addnstr(0, 0, f"Discovered {len(rows)} Claude profile dirs", w - 1, curses.A_BOLD)
            stdscr.addnstr(1, 0, "up/down move  space/c toggle  C toggle all", w - 1, curses.A_DIM)
            stdscr.addnstr(2, 0, "g/G top/bottom  enter confirm  q cancel", w - 1, curses.A_DIM)
            stdscr.addnstr(3, 0, "    CLEAN  PROFILE", w - 1, curses.A_UNDERLINE)

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
                label = tilde(r.path) + ("  (active)" if active and r.path == active else "")
                stdscr.addstr(y, 0, " > " if focused else "   ", rowattr)
                stdscr.addstr(y, 4, "[x]" if r.clean else "[ ]",
                              curses.A_REVERSE if focused else rowattr)
                stdscr.addnstr(y, 11, label, max(1, w - 12), rowattr)

            stdscr.addnstr(h - 1, 0, f"selected: {n}   ({cur + 1}/{len(rows)})", w - 1, curses.A_DIM)
            stdscr.refresh()

            k = stdscr.getch()
            if k in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                cur = min(len(rows) - 1, cur + 1)
            elif k in (curses.KEY_NPAGE,):
                cur = min(len(rows) - 1, cur + list_h)
            elif k in (curses.KEY_PPAGE,):
                cur = max(0, cur - list_h)
            elif k == ord("g"):
                cur = 0
            elif k == ord("G"):
                cur = len(rows) - 1
            elif k in (ord(" "), ord("c")):
                rows[cur].clean = not rows[cur].clean
            elif k == ord("C"):
                v = not all(r.clean for r in rows)
                for r in rows:
                    r.clean = v
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


def pick_text(rows: list[Row], active: Path | None) -> bool:
    """Fallback selector for when there is no usable TTY for curses."""
    for i, r in enumerate(rows):
        tag = "  (active)" if active and r.path == active else ""
        print(f"{i + 1:3}  {tilde(r.path)}{tag}")
    sel = parse_nums(input("\nClean which #s? (e.g. '1 2', 'all', blank=none): "), len(rows))
    for i in sel:
        rows[i].clean = True
    return True


# --------------------------------------------------------------------------- #
# 3. Clean
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"  warning: could not read {tilde(path)} ({e}); leaving it untouched", file=sys.stderr)
        return None


def write_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def build_plan(profile: Path, cats: list[str]) -> dict:
    """What would be removed/edited for one profile (no side effects).

    Handles both CLI dirs (skills/agents/.../.claude.json/settings.json) and
    Desktop app dirs (Claude Extensions/, claude_desktop_config.json).
    """
    moves: list[Path] = []
    # CLI content dirs.
    for name in CONTENT_DIRS:
        if name in cats:
            d = profile / name
            if d.is_dir() or d.is_symlink():
                moves.append(d)
    # Desktop extensions.
    if "extensions" in cats:
        for name in DESKTOP_EXT_ITEMS:
            item = profile / name
            if item.exists() or item.is_symlink():
                moves.append(item)

    # CLI settings.json customization keys.
    settings = load_json(profile / "settings.json")
    skeys: list[str] = []
    if settings is not None:
        wanted = []
        if "plugins" in cats:
            wanted += ["enabledPlugins", "extraKnownMarketplaces"]
        if "hooks" in cats:
            wanted += ["hooks"]
        if "output-styles" in cats:
            wanted += ["outputStyle", "statusLine"]
        skeys = [k for k in wanted if k in settings]

    # CLI MCP servers (.claude.json, top-level + per-project).
    cli_mcp = None
    if "mcp" in cats:
        cj = load_json(profile / ".claude.json")
        if cj is not None:
            top = list((cj.get("mcpServers") or {}).keys())
            nproj = sum(1 for v in (cj.get("projects") or {}).values()
                        if isinstance(v, dict) and v.get("mcpServers"))
            if top or nproj:
                cli_mcp = {"top": top, "projects": nproj}

    # Desktop MCP servers (claude_desktop_config.json).
    desktop_mcp = None
    if "mcp" in cats:
        dc = load_json(profile / "claude_desktop_config.json")
        if dc is not None:
            servers = list((dc.get("mcpServers") or {}).keys())
            if servers:
                desktop_mcp = servers

    return {"moves": moves, "settings_keys": skeys, "cli_mcp": cli_mcp, "desktop_mcp": desktop_mcp}


def plan_empty(plan: dict) -> bool:
    return not (plan["moves"] or plan["settings_keys"] or plan["cli_mcp"] or plan["desktop_mcp"])


def _strip_json(profile: Path, backup: Path, name: str, mutate, manifest_key: str,
                manifest: dict, label: str) -> None:
    """Back up a JSON file, apply mutate(data), write it back."""
    path = profile / name
    data = load_json(path)
    if data is None:
        return
    shutil.copy2(path, backup / name)
    info = mutate(data)
    write_json(path, data)
    manifest[manifest_key] = info
    print(f"    edited {name} ({label})")


def execute(profile: Path, plan: dict, dry: bool) -> Path | None:
    """Apply the plan for one profile. Returns the backup dir (or None on dry-run)."""
    if dry:
        for item in plan["moves"]:
            suffix = "/" if item.is_dir() and not item.is_symlink() else ""
            print(f"    move   {item.name}{suffix}  -> backups/cleanup-<TS>/")
        if plan["settings_keys"]:
            print(f"    edit   settings.json (strip {', '.join(plan['settings_keys'])})")
        if plan["cli_mcp"]:
            print("    edit   .claude.json (remove MCP servers)")
        if plan["desktop_mcp"]:
            print("    edit   claude_desktop_config.json (remove MCP servers)")
        return None

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = profile / "backups" / f"cleanup-{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"timestamp": ts, "target": str(profile), "moved": []}

    for item in plan["moves"]:
        shutil.move(str(item), str(backup / item.name))
        manifest["moved"].append(item.name)
        print(f"    moved  {item.name}  ->  {tilde(backup / item.name)}")

    if plan["settings_keys"]:
        def drop_keys(s, keys=plan["settings_keys"]):
            for k in keys:
                s.pop(k, None)
            return keys
        _strip_json(profile, backup, "settings.json", drop_keys, "settings_keys", manifest,
                    f"stripped {', '.join(plan['settings_keys'])}")

    if plan["cli_mcp"]:
        def drop_cli_mcp(cj, info=plan["cli_mcp"]):
            cj.pop("mcpServers", None)
            for v in (cj.get("projects") or {}).values():
                if isinstance(v, dict):
                    v.pop("mcpServers", None)
            return info
        _strip_json(profile, backup, ".claude.json", drop_cli_mcp, "cli_mcp", manifest,
                    "removed MCP servers")

    if plan["desktop_mcp"]:
        def drop_desktop_mcp(dc, info=plan["desktop_mcp"]):
            dc.pop("mcpServers", None)
            return info
        _strip_json(profile, backup, "claude_desktop_config.json", drop_desktop_mcp, "desktop_mcp",
                    manifest, "removed MCP servers")

    write_json(backup / "manifest.json", manifest)
    return backup


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Discover Claude profile dirs and wipe customizations from the ones you pick.",
    )
    ap.add_argument("--keep", default="", metavar="LIST",
                    help="categories to KEEP: " + " ".join(DEFAULT_CATEGORIES))
    ap.add_argument("--dry-run", action="store_true", help="show what would happen; change nothing")
    ap.add_argument("--yes", "-y", action="store_true", help="skip the final confirmation prompt")
    args = ap.parse_args()

    keep = set(args.keep.replace(",", " ").split())
    bad = keep - set(DEFAULT_CATEGORIES)
    if bad:
        print(f"error: unknown --keep categories: {', '.join(sorted(bad))}", file=sys.stderr)
        return 1
    cats = [c for c in DEFAULT_CATEGORIES if c not in keep]

    active_env = os.environ.get("CLAUDE_CONFIG_DIR")
    active = Path(active_env).expanduser().resolve() if active_env else None

    print("==> scanning ~ for Claude profile dirs ...")
    paths = discover()
    if not paths:
        print("No Claude profile dirs found.")
        return 1
    rows = [Row(p) for p in paths]
    active_match = next((p for p in paths if active and p.resolve() == active), None)

    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            confirmed = pick_curses(rows, active_match)
        except curses.error as e:
            print(f"(curses unavailable: {e}; falling back to text)", file=sys.stderr)
            confirmed = pick_text(rows, active_match)
    else:
        confirmed = pick_text(rows, active_match)

    if not confirmed:
        print("Cancelled.")
        return 130

    selected = [r for r in rows if r.clean]
    if not selected:
        print("Nothing selected.")
        return 0

    # Plan.
    print(f"\n==> plan ({'DRY RUN' if args.dry_run else 'apply'}):")
    if keep:
        print(f"    keeping: {', '.join(sorted(keep))}")
    plans: dict[Path, dict] = {}
    for r in selected:
        plan = build_plan(r.path, cats)
        plans[r.path] = plan
        kind = "desktop" if is_desktop(r.path) else "cli"
        print(f"  {tilde(r.path)}  [{kind}]")
        if plan_empty(plan):
            print("      (already clean — nothing to remove)")
            continue
        for item in plan["moves"]:
            suffix = "/" if item.is_dir() and not item.is_symlink() else ""
            print(f"      remove {item.name}{suffix}  ({describe(item)})")
        if plan["settings_keys"]:
            print(f"      strip  settings.json: {', '.join(plan['settings_keys'])}")
        if plan["cli_mcp"]:
            m = plan["cli_mcp"]
            extra = f" + {m['projects']} project(s)" if m["projects"] else ""
            print(f"      strip  .claude.json MCP: {', '.join(m['top']) or '(none top-level)'}{extra}")
        if plan["desktop_mcp"]:
            print(f"      strip  claude_desktop_config.json MCP: {', '.join(plan['desktop_mcp'])}")
    print("\n    PRESERVED: auth, oauthAccount, projects/, sessions/, history, caches,"
          " settings prefs, and the Desktop app's own state.")
    if any(is_desktop(r.path) for r in selected):
        print("    NOTE: quit Claude Desktop before cleaning its folders.")

    # Confirm. Reversible (everything is backed up), so a plain yes is enough.
    if not args.dry_run and not args.yes:
        print("\nRemoved items are moved to <profile>/backups/cleanup-<TS>/ (reversible).")
        if input("Proceed? type 'yes': ").strip().lower() not in ("yes", "y"):
            print("Aborted.")
            return 130

    # Execute.
    for r in selected:
        print(f"\n--> {tilde(r.path)}")
        if plan_empty(plans[r.path]):
            print("    (nothing to do)")
            continue
        backup = execute(r.path, plans[r.path], args.dry_run)
        if backup:
            print(f"    backup: {tilde(backup)}")

    print("\n==> done." + (" (dry run; nothing changed)" if args.dry_run else
                           "  Restart Claude Code to reload the cleaned profile(s)."))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
