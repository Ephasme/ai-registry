#!/usr/bin/env bash
# docker-reclaim.sh — reclaim Docker disk space with safety gates (macOS).
#
# KEY FACTS:
#  * The Docker.raw disk image does NOT shrink when you delete images/volumes.
#    Only a full reset (delete the .raw) actually returns the space to the disk.
#  * Volumes can hold real data (e.g. a live dev database). A full reset destroys
#    them. ALWAYS run `inspect` and show the user before any reset.
#
# Usage:
#   docker-reclaim.sh inspect            show containers/images/volumes + raw size
#   docker-reclaim.sh prune-safe         build cache + dangling images (no data loss)
#   docker-reclaim.sh full-reset --yes   quit Docker, delete Docker.raw (DESTROYS ALL)

set -uo pipefail
RAW="$HOME/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw"

case "${1:-inspect}" in
  inspect)
    echo "== Containers =="; docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null
    echo; echo "== Images =="; docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' 2>/dev/null
    echo; echo "== Volumes (size & links — LINKS>0 means in use) =="
    docker system df -v 2>/dev/null | sed -n '/VOLUME NAME/,/^[[:space:]]*$/p'
    echo; echo "== Summary =="; docker system df 2>/dev/null
    echo; [ -f "$RAW" ] && echo "Docker.raw on disk: $(du -sh "$RAW" 2>/dev/null | cut -f1)"
    echo; echo "⚠ Before a full reset, identify any volume that looks like a database"
    echo "  (big size, name like *db*, *data*, *pgdata*) and confirm with the user."
    ;;

  prune-safe)
    echo "Pruning build cache + dangling images (no data loss)..."
    docker builder prune -af 2>/dev/null | tail -1
    docker image prune -f   2>/dev/null | tail -1
    echo "Note: this frees space INSIDE Docker.raw but the .raw file won't shrink."
    ;;

  full-reset)
    if [ "${2:-}" != "--yes" ]; then
      echo "REFUSING: full-reset destroys ALL containers, images, and volumes."
      echo "Run inspect first, confirm with the user, then: docker-reclaim.sh full-reset --yes"
      exit 1
    fi
    echo "Quitting Docker Desktop..."
    osascript -e 'quit app "Docker Desktop"' 2>/dev/null || osascript -e 'quit app "Docker"' 2>/dev/null
    # wait for the VM to release the file lock
    for i in $(seq 1 15); do
      sleep 1
      lsof "$RAW" >/dev/null 2>&1 || break
    done
    if lsof "$RAW" >/dev/null 2>&1; then
      echo "Docker.raw is still locked — Docker did not fully quit. Aborting."
      echo "Quit Docker Desktop manually, then re-run."
      exit 1
    fi
    BEFORE=$(diskutil info / 2>/dev/null | grep -i "Free Space")
    rm -f "$RAW" && echo "Docker.raw deleted (will be recreated empty on next Docker launch)."
    echo "Free before: $BEFORE"
    echo "Free after : $(diskutil info / 2>/dev/null | grep -i 'Free Space')"
    echo "Reminder: relaunch Docker Desktop and re-create/seed any containers & data."
    ;;

  *) echo "Usage: docker-reclaim.sh {inspect|prune-safe|full-reset --yes}"; exit 1 ;;
esac
