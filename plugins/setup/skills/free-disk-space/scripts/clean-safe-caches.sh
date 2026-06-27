#!/usr/bin/env bash
# clean-safe-caches.sh — wipe ONLY regenerable caches (the 🟢 tier).
# Everything here is rebuilt automatically by the tool that owns it; the only
# cost is a one-time slower "first run". Default is a DRY-RUN.
#
# Usage:
#   clean-safe-caches.sh           dry-run: list targets + sizes, delete nothing
#   clean-safe-caches.sh --apply   actually delete, then report freed space
#
# To add a target, append it to TARGETS with a one-line reason it's regenerable.

set -uo pipefail

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

free_bytes() { diskutil info / 2>/dev/null | awk -F'[()]' '/Free Space/ {print $2}' | awk '{print $1}'; }
human() { # bytes -> human
  awk -v b="$1" 'BEGIN{split("B KB MB GB TB",u);for(i=1;b>=1024&&i<5;i++)b/=1024;printf "%.1f %s",b,u[i]}'
}

# Each entry: a glob/path that is safe to remove. Directories are emptied,
# files removed. Paths with spaces are quoted at use-site.
TARGETS=(
  "$HOME/.cache/uv"                    # uv Python package cache (often the biggest)
  "$HOME/.cache/puppeteer"             # downloaded browser binaries
  "$HOME/.cache/pyright-python"        # pyright bundles
  "$HOME/.cache/pre-commit"            # pre-commit hook envs
  "$HOME/.cache/firebase"              # firebase tool cache
  "$HOME/.cache/node"                  # node-gyp etc.
  "$HOME/.cache/gh"                    # gh cli cache
  "$HOME/.cache/pip"                   # pip cache
  "$HOME/.npm/_cacache"                # npm content-addressable cache
  "$HOME/.gradle/caches"               # gradle build cache
  "$HOME/Library/Caches"               # general app caches (contents)
  "$HOME/Library/Developer/Xcode/DerivedData"   # Xcode build products
  "$HOME/Library/Developer/Xcode/iOS DeviceSupport" # re-created on device connect
)

# Editor Electron caches: ONLY these subdirs are caches. Never backups/sessions/User.
EDITOR_APPS=(
  "$HOME/Library/Application Support/Cursor"
  "$HOME/Library/Application Support/Code"
  "$HOME/Library/Application Support/Claude"
  "$HOME/.claude-desktop-work"
  "$HOME/.claude-desktop-perso"
)
EDITOR_SUBDIRS=("Cache" "Code Cache" "GPUCache" "CachedData" "CachedExtensionVSIXs" "logs")

size_of() { du -sh "$1" 2>/dev/null | cut -f1; }

echo "=== Safe cache cleanup ($([ $APPLY -eq 1 ] && echo APPLY || echo DRY-RUN)) ==="
BEFORE=$(free_bytes)
echo "Free space before: $(human "${BEFORE:-0}")"
echo

wipe() { # $1 = path (dir contents removed, or file removed)
  local p="$1"
  [ -e "$p" ] || return 0
  local s; s=$(size_of "$p")
  if [ $APPLY -eq 1 ]; then
    if [ -d "$p" ]; then rm -rf "$p"/* "$p"/.[!.]* 2>/dev/null; else rm -f "$p" 2>/dev/null; fi
    echo "  cleared  $s  $p"
  else
    echo "  would clear  $s  $p"
  fi
}

for t in "${TARGETS[@]}"; do wipe "$t"; done

echo "-- editor Electron caches --"
for app in "${EDITOR_APPS[@]}"; do
  [ -d "$app" ] || continue
  for sub in "${EDITOR_SUBDIRS[@]}"; do wipe "$app/$sub"; done
done

if [ $APPLY -eq 1 ]; then
  echo "-- extras --"
  command -v xcrun >/dev/null 2>&1 && { xcrun simctl delete unavailable >/dev/null 2>&1 && echo "  simctl: removed unavailable simulators"; }
  command -v brew  >/dev/null 2>&1 && { brew cleanup -q >/dev/null 2>&1 && echo "  brew cleanup done"; }
  command -v docker >/dev/null 2>&1 && { docker builder prune -af >/dev/null 2>&1 && echo "  docker build cache pruned"; }
fi

echo
AFTER=$(free_bytes)
echo "Free space after: $(human "${AFTER:-0}")"
if [ $APPLY -eq 1 ] && [ -n "${BEFORE:-}" ] && [ -n "${AFTER:-}" ]; then
  echo "Reclaimed: $(human "$((AFTER-BEFORE))")"
else
  echo "(dry-run — re-run with --apply to delete)"
fi
