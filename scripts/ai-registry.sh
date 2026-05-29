#!/usr/bin/env bash
# ai-registry — install this public Claude Code plugin marketplace.
#
# Adds the marketplace and installs ALL of its plugins into the current project
# (or another scope). Invoke via the `ai-registry` shell alias (`air` == `ai-registry install`).
set -euo pipefail

MARKETPLACE_NAME="ai-registry"
# Public repo → plain HTTPS shorthand, no credentials needed.
SOURCE="${AI_REGISTRY_SOURCE:-Ephasme/ai-registry}"
MANIFEST="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/$MARKETPLACE_NAME/.claude-plugin/marketplace.json"

usage() {
  cat <<'EOF'
ai-registry — install this public Claude Code plugin marketplace.

Usage:
  ai-registry install [scope] [--scope <scope>] [--skip "a,b,c"] [--profile <name>]

  install         add the marketplace and install ALL its plugins into the project
  scope           project (default) | user | local   (positional or --scope)
  --skip LIST     comma- or space-separated plugin names to skip
  --profile NAME  config dir to install into (sets CLAUDE_CONFIG_DIR):
                  perso|work → ~/.claude-NAME, default → ~/.claude, or an explicit path.
                  Omit to use the active CLAUDE_CONFIG_DIR (or ~/.claude).

Short form:  air  ==  ai-registry install

Env:
  AI_REGISTRY_SOURCE   git source (default: Ephasme/ai-registry)
  AI_REGISTRY_SKIP     default skip list (overridden by --skip)
  CLAUDE_CONFIG_DIR    active profile dir, respected if set (overridden by --profile)
EOF
}

# --- subcommand dispatch ----------------------------------------------------
cmd="${1:-}"
case "$cmd" in
  install)        shift ;;
  ""|-h|--help|help) usage; exit 0 ;;
  *) echo "error: unknown command '$cmd' (try: ai-registry install)" >&2; exit 1 ;;
esac

# --- `install` argument parsing --------------------------------------------
SCOPE=""
SKIP_CSV="${AI_REGISTRY_SKIP:-}"
PROFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip=*)     SKIP_CSV="${1#--skip=}" ;;
    --skip)       shift; SKIP_CSV="${1:-}" ;;
    --scope=*)    SCOPE="${1#--scope=}" ;;
    --scope)      shift; SCOPE="${1:-}" ;;
    --profile=*)  PROFILE="${1#--profile=}" ;;
    --profile)    shift; PROFILE="${1:-}" ;;
    project|user|local) SCOPE="$1" ;;
    *) echo "error: unknown argument '$1' (try: ai-registry install --help)" >&2; exit 1 ;;
  esac
  shift
done
SCOPE="${SCOPE:-project}"

# Resolve --profile into CLAUDE_CONFIG_DIR so plugins land in the intended profile.
if [ -n "$PROFILE" ]; then
  case "$PROFILE" in
    */*)     CFG="$PROFILE" ;;            # explicit path
    default) CFG="$HOME/.claude" ;;
    *)       CFG="$HOME/.claude-$PROFILE" ;;
  esac
  [ -d "$CFG" ] || { echo "error: profile dir '$CFG' does not exist (from --profile '$PROFILE')" >&2; exit 1; }
  export CLAUDE_CONFIG_DIR="$CFG"
  MANIFEST="$CFG/plugins/marketplaces/$MARKETPLACE_NAME/.claude-plugin/marketplace.json"
fi

command -v claude >/dev/null 2>&1 || { echo "error: 'claude' CLI not found on PATH" >&2; exit 1; }
command -v jq     >/dev/null 2>&1 || { echo "error: 'jq' not found on PATH" >&2; exit 1; }

case "$SCOPE" in
  project|user|local) ;;
  *) echo "error: scope must be 'project', 'user', or 'local' (got '$SCOPE')" >&2; exit 1 ;;
esac

# Normalize the skip list (commas or spaces) into a space-padded string for matching.
skip=" ${SKIP_CSV//,/ } "

echo "==> ai-registry: marketplace '$MARKETPLACE_NAME' (scope: $SCOPE)"
echo "    profile:  ${CLAUDE_CONFIG_DIR:-$HOME/.claude (default)}"
[ "$skip" = "  " ] || echo "    skipping:$(echo "$skip" | sed 's/  */ /g')"

# Add if missing, then always refresh to latest. 'add' is a no-op / expected
# failure when the marketplace is already registered, so the real gate is 'update'.
claude plugin marketplace add "$SOURCE" --scope "$SCOPE" >/dev/null 2>&1 || true
if ! claude plugin marketplace update "$MARKETPLACE_NAME"; then
  echo "error: could not add/update marketplace '$MARKETPLACE_NAME' from $SOURCE." >&2
  exit 1
fi

[ -f "$MANIFEST" ] || { echo "error: marketplace manifest not found at $MANIFEST" >&2; exit 1; }

while IFS= read -r plugin; do
  [ -n "$plugin" ] || continue
  if [ "$skip" != "${skip/ $plugin / }" ]; then
    echo "  · skip    $plugin"
    continue
  fi
  echo "  → install $plugin@$MARKETPLACE_NAME"
  claude plugin install "$plugin@$MARKETPLACE_NAME" --scope "$SCOPE"
done < <(jq -r '.plugins[].name' "$MANIFEST")

echo "==> done. Installed plugins:"
claude plugin list 2>/dev/null || true
echo "    (restart Claude Code in this project to load them)"
