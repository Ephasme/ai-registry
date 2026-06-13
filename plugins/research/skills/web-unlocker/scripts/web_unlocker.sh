#!/usr/bin/env bash
# web_unlocker.sh — fetch a URL through BrightData's Web Unlocker API.
#
# Use this when a normal fetch is blocked (403 / 429, Cloudflare or other
# anti-bot interstitials, CAPTCHA, geo-restriction, or a JS-only page). The
# Web Unlocker routes the request through a residential proxy that solves
# challenges and renders the page, then returns the resolved content.
#
# The API key is never hardcoded. It is resolved at runtime in this order:
#   1. $BRIGHTDATA_API_KEY                         (explicit override)
#   2. SOPS-decrypt the first brightdata.sops.json found among candidate
#      locations (the committed, age-encrypted secret in this repo).
#
# Requires: curl, jq. SOPS resolution additionally needs: sops + the age
# private key (~/.config/sops/age/keys.txt). If you don't have the age key,
# set BRIGHTDATA_API_KEY in the environment instead.
#
# Usage:
#   web_unlocker.sh [options] <url>
#
# Options:
#   --markdown        Return clean Markdown (data_format=markdown) instead of
#                     raw HTML — best when the goal is to read/extract content.
#   --country <cc>    Two-letter country code to geo-target the request
#                     (e.g. us, gb, de, fr) — use for region-locked pages.
#   --zone <name>     BrightData zone to use (default: web_unlocker).
#   --format <fmt>    Response envelope: raw (default, body only) | json
#                     (BrightData wraps the body with metadata).
#   -o, --output <f>  Write the response body to file <f> instead of stdout.
#   --timeout <secs>  curl max time (default: 120). Unlocking can be slow.
#   -h, --help        Show this help.
#
# Examples:
#   web_unlocker.sh https://example.com/blocked-page
#   web_unlocker.sh --markdown https://news.site/article
#   web_unlocker.sh --country gb --markdown https://shop.example/uk-only -o page.md
set -euo pipefail

# ---- defaults --------------------------------------------------------------
ZONE="web_unlocker"
FORMAT="raw"
DATA_FORMAT=""
COUNTRY=""
OUTPUT=""
TIMEOUT="120"
URL=""

die() { printf 'web_unlocker: %s\n' "$1" >&2; exit "${2:-1}"; }

usage() { sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

# ---- parse args ------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --markdown)      DATA_FORMAT="markdown"; shift ;;
    --country)       COUNTRY="$(printf '%s' "${2:-}" | tr '[:upper:]' '[:lower:]')"; shift 2 ;;
    --zone)          ZONE="${2:-}"; shift 2 ;;
    --format)        FORMAT="${2:-}"; shift 2 ;;
    -o|--output)     OUTPUT="${2:-}"; shift 2 ;;
    --timeout)       TIMEOUT="${2:-}"; shift 2 ;;
    -h|--help)       usage ;;
    --)              shift; URL="${1:-}"; break ;;
    -*)              die "unknown option: $1 (try --help)" ;;
    *)               if [ -z "$URL" ]; then URL="$1"; else die "unexpected extra argument: $1"; fi; shift ;;
  esac
done

[ -n "$URL" ] || die "no URL given (try --help)" 2
case "$URL" in
  http://*|https://*) : ;;
  *) die "URL must start with http:// or https:// — got: $URL" 2 ;;
esac

command -v curl >/dev/null 2>&1 || die "curl not found on PATH"
command -v jq   >/dev/null 2>&1 || die "jq not found on PATH"

# ---- resolve the API key ---------------------------------------------------
resolve_key() {
  # 1. explicit env override
  if [ -n "${BRIGHTDATA_API_KEY:-}" ]; then
    printf '%s' "$BRIGHTDATA_API_KEY"; return 0
  fi

  # 2. SOPS-decrypt the committed secret. Search candidate locations; the
  #    secret travels with the marketplace clone and the source repo.
  command -v sops >/dev/null 2>&1 || return 1

  local script_dir candidates=() c
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  [ -n "${BRIGHTDATA_APIKEY_SOPS:-}" ] && candidates+=("$BRIGHTDATA_APIKEY_SOPS")

  local cfg_dirs=("${CLAUDE_CONFIG_DIR:-}" "$HOME/.claude-perso" "$HOME/.claude-work" "$HOME/.claude")
  for cd_dir in "${cfg_dirs[@]}"; do
    [ -n "$cd_dir" ] && candidates+=("$cd_dir/plugins/marketplaces/ai-registry/secrets/brightdata.sops.json")
  done

  # Walk up from the script's own directory (handles running inside a clone
  # of the repo, where secrets/ sits at the repo root).
  local d="$script_dir"
  while [ "$d" != "/" ]; do
    candidates+=("$d/secrets/brightdata.sops.json")
    d="$(dirname "$d")"
  done

  for c in "${candidates[@]}"; do
    if [ -f "$c" ]; then
      local val
      if val="$(sops -d "$c" 2>/dev/null | jq -r '.BRIGHTDATA_API_KEY // empty' 2>/dev/null)" && [ -n "$val" ]; then
        printf '%s' "$val"; return 0
      fi
    fi
  done
  return 1
}

API_KEY="$(resolve_key)" || die \
"could not resolve the BrightData API key.
  - Set BRIGHTDATA_API_KEY in the environment, or
  - ensure 'sops' is installed and the age key (~/.config/sops/age/keys.txt)
    can decrypt secrets/brightdata.sops.json in the ai-registry repo."

# ---- build the request payload (jq escapes everything safely) --------------
PAYLOAD="$(
  jq -n \
    --arg zone "$ZONE" \
    --arg url "$URL" \
    --arg format "$FORMAT" \
    --arg data_format "$DATA_FORMAT" \
    --arg country "$COUNTRY" \
    '{zone: $zone, url: $url, format: $format}
     + (if $data_format != "" then {data_format: $data_format} else {} end)
     + (if $country     != "" then {country: $country}         else {} end)'
)"

# ---- call the API ----------------------------------------------------------
# Capture body + trailing HTTP status so we can report API-level errors
# (auth, quota, bad zone) instead of silently emitting an error page.
TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

HTTP_CODE="$(
  curl -sS --max-time "$TIMEOUT" \
    -w '%{http_code}' \
    -o "$TMP_BODY" \
    -X POST 'https://api.brightdata.com/request' \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${API_KEY}" \
    -d "$PAYLOAD"
)" || die "curl failed to reach api.brightdata.com (network/timeout)"

if [ "$HTTP_CODE" -ge 400 ] 2>/dev/null; then
  printf 'web_unlocker: BrightData API returned HTTP %s\n' "$HTTP_CODE" >&2
  printf -- '--- response body ---\n' >&2
  cat "$TMP_BODY" >&2
  exit 1
fi

if [ -n "$OUTPUT" ]; then
  cp "$TMP_BODY" "$OUTPUT"
  BYTES="$(wc -c < "$OUTPUT" | tr -d ' ')"
  printf 'web_unlocker: wrote %s bytes to %s (HTTP %s)\n' "$BYTES" "$OUTPUT" "$HTTP_CODE" >&2
else
  cat "$TMP_BODY"
fi
