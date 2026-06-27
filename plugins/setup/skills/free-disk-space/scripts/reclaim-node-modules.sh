#!/usr/bin/env bash
# reclaim-node-modules.sh — find & remove node_modules under a directory.
# Regenerable via npm/yarn/pnpm install, but removal breaks those projects
# until reinstalled — so this is the 🟠 tier. Dry-run by default.
#
# Usage:
#   reclaim-node-modules.sh <dir>                 dry-run: count + total size
#   reclaim-node-modules.sh <dir> --apply         delete them
#   reclaim-node-modules.sh <dir> --apply --older-than 30   only if untouched 30+ days

set -uo pipefail

DIR="${1:-}"
[ -d "$DIR" ] || { echo "Usage: reclaim-node-modules.sh <dir> [--apply] [--older-than DAYS]"; exit 1; }
shift

APPLY=0; OLDER=""
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --older-than) shift; OLDER="$1" ;;
  esac; shift
done

FIND=(find "$DIR" -type d -name node_modules -prune)
[ -n "$OLDER" ] && FIND+=(-mtime "+$OLDER")

mapfile -t DIRS < <("${FIND[@]}" 2>/dev/null)
echo "Found ${#DIRS[@]} node_modules dir(s) under $DIR${OLDER:+ (untouched ${OLDER}+ days)}"
[ ${#DIRS[@]} -eq 0 ] && exit 0

TOTAL_KB=0
for d in "${DIRS[@]}"; do
  kb=$(du -sk "$d" 2>/dev/null | cut -f1); TOTAL_KB=$((TOTAL_KB + kb))
  if [ $APPLY -eq 1 ]; then rm -rf "$d" && echo "  removed  $d"; else echo "  $(du -sh "$d" 2>/dev/null | cut -f1)  $d"; fi
done

printf 'Total: %.1f GB across %d dirs\n' "$(echo "$TOTAL_KB/1048576" | bc -l)" "${#DIRS[@]}"
[ $APPLY -eq 0 ] && echo "(dry-run — re-run with --apply to delete)"
