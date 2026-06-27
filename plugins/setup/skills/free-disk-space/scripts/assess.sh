#!/usr/bin/env bash
# assess.sh — read-only disk-usage assessment (macOS / APFS).
# Usage:
#   assess.sh            full machine scan: free space + where it went
#   assess.sh downloads  inventory the Downloads folder by category & size
# Nothing is ever deleted by this script.

set -uo pipefail

free_space() {
  # True APFS container free space (df -h is misleading on APFS).
  diskutil info / 2>/dev/null | grep -i "Free Space" | sed 's/^ *//'
}

hr() { printf '%s\n' "----------------------------------------------------------------"; }

assess_downloads() {
  local DL="$HOME/Downloads"
  [ -d "$DL" ] || { echo "No ~/Downloads"; return; }
  echo "== Downloads: $(du -sh "$DL" 2>/dev/null | cut -f1), $(find "$DL" -type f 2>/dev/null | wc -l | tr -d ' ') files =="
  hr
  echo "-- Installers (.dmg/.pkg) — almost always disposable --"
  find "$DL" -maxdepth 2 -type f \( -iname '*.dmg' -o -iname '*.pkg' \) -exec du -h {} + 2>/dev/null | sort -rh | head -15
  echo "-- Archives (.zip) --"
  find "$DL" -maxdepth 2 -type f -iname '*.zip' -exec du -h {} + 2>/dev/null | sort -rh | head -15
  echo "-- Top 20 files by size --"
  find "$DL" -type f -exec du -h {} + 2>/dev/null | sort -rh | head -20
  echo "-- Size by extension --"
  find "$DL" -type f 2>/dev/null | sed 's/.*\.//' | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -15
  echo "-- ⚠ Sensitive files to flag (DO NOT auto-delete) --"
  find "$DL" -maxdepth 3 -type f \( -iname '*.1pux' -o -iname '*.pem' -o -iname 'id_rsa*' \
      -o -iname '*.p12' -o -iname '*.keychain*' -o -iname '*wallet*' -o -iname '*seed*' \) 2>/dev/null | head
}

assess_full() {
  echo "== DISK =="
  df -h / 2>/dev/null | tail -1
  echo "Real free space (APFS container): $(free_space)"
  hr
  echo "== HOME top-level (this can take 1-2 min) =="
  du -sh "$HOME"/* "$HOME"/.[!.]* 2>/dev/null | sort -rh | head -25
  hr
  echo "== ~/Library (top 12) =="
  du -sh "$HOME/Library"/* 2>/dev/null | sort -rh | head -12
  echo "-- Library/Application Support (top 12) --"
  du -sh "$HOME/Library/Application Support"/* 2>/dev/null | sort -rh | head -12
  echo "-- Library/Developer (Xcode etc.) --"
  du -sh "$HOME/Library/Developer"/* 2>/dev/null | sort -rh | head
  [ -d "$HOME/Library/Developer/Xcode" ] && du -sh "$HOME/Library/Developer/Xcode"/* 2>/dev/null | sort -rh | head
  hr
  echo "== ~/.cache (top 12) =="
  du -sh "$HOME/.cache"/* 2>/dev/null | sort -rh | head -12
  hr
  echo "== Regenerable cache hotspots =="
  for d in "$HOME/.npm" "$HOME/.gradle/caches" "$HOME/Library/Caches" \
           "$HOME/Library/Developer/Xcode/DerivedData" "$HOME/Library/Developer/CoreSimulator"; do
    [ -e "$d" ] && du -sh "$d" 2>/dev/null
  done
  hr
  echo "== code / projects =="
  for base in "$HOME/code" "$HOME/Projects" "$HOME/dev" "$HOME/src"; do
    [ -d "$base" ] || continue
    echo "-- $base (top 10) --"; du -sh "$base"/* 2>/dev/null | sort -rh | head -10
    n=$(find "$base" -type d -name node_modules -prune 2>/dev/null | wc -l | tr -d ' ')
    echo "   node_modules dirs under $base: $n"
  done
  hr
  echo "== Docker =="
  local RAW="$HOME/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw"
  [ -f "$RAW" ] && echo "Docker.raw: $(du -sh "$RAW" 2>/dev/null | cut -f1)"
  docker system df 2>/dev/null || echo "(docker not running / not installed)"
  hr
  echo "== Trash & Downloads =="
  du -sh "$HOME/.Trash" "$HOME/Downloads" 2>/dev/null
  hr
  echo "Next: clean-safe-caches.sh --apply  (wipes regenerable caches; biggest safe win)"
}

case "${1:-full}" in
  downloads) assess_downloads ;;
  *)         assess_full ;;
esac
