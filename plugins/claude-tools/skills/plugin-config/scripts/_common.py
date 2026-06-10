"""Shared helpers for the plugin-config skill scripts.

Stdlib only, Python 3.8+. These functions encode where Claude Code keeps plugin
``userConfig`` values so the other scripts (diagnose / set_config) can reason
about them without duplicating the logic.

Storage model (verified against code.claude.com/docs/en/plugins-reference, the
"User configuration" section):

  - Non-sensitive fields  -> <config-dir>/settings.json under
                             pluginConfigs["<plugin>@<marketplace>"].options
  - Sensitive fields      -> OS keychain, or <config-dir>/.credentials.json
                             where the keychain is unavailable.

Both kinds interpolate as ${user_config.KEY} in the plugin's .mcp.json / LSP /
hook / monitor configs, and are exported to plugin subprocesses as
CLAUDE_PLUGIN_OPTION_<KEY>.

The keychain *service/account naming* for plugin secrets is not documented, so
nothing here claims to read a sensitive value back by name -- see keychain_probe.py
for empirical discovery.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Config dirs
# --------------------------------------------------------------------------- #

def default_config_dir() -> Path:
    """The config dir Claude Code would use right now.

    Honors CLAUDE_CONFIG_DIR (the documented override used by profile setups),
    falling back to ~/.claude.
    """
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def resolve_config_dirs(values: Optional[List[str]]) -> List[Path]:
    """Turn --config-dir arguments into paths, defaulting to the active one."""
    if not values:
        return [default_config_dir()]
    return [Path(v).expanduser() for v in values]


# --------------------------------------------------------------------------- #
# Plugin id / marketplace / manifest resolution
# --------------------------------------------------------------------------- #

def parse_plugin_id(plugin_id: str) -> Tuple[str, Optional[str]]:
    """Split "name@marketplace" into (name, marketplace). marketplace may be None."""
    if "@" in plugin_id:
        name, market = plugin_id.split("@", 1)
        return name, (market or None)
    return plugin_id, None


def _marketplaces_dir(config_dir: Path) -> Path:
    return config_dir / "plugins" / "marketplaces"


def load_json(path: Path) -> Optional[dict]:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def resolve_manifest(
    config_dir: Path, plugin_name: str, marketplace: Optional[str]
) -> Tuple[Optional[str], Optional[Path]]:
    """Locate the installed plugin.json for a plugin in a config dir.

    Returns (marketplace_name, manifest_path). Either may be None when the
    plugin/marketplace can't be found. The marketplace's own marketplace.json is
    consulted so a plugin whose source dir differs from its name still resolves;
    we fall back to plugins/<name> when that lookup fails.
    """
    mdir = _marketplaces_dir(config_dir)
    if not mdir.is_dir():
        return marketplace, None

    if marketplace:
        candidates = [mdir / marketplace]
    else:
        candidates = sorted(p for p in mdir.iterdir() if p.is_dir())

    for cand in candidates:
        if not cand.is_dir():
            continue
        market_json = load_json(cand / ".claude-plugin" / "marketplace.json")
        source_rel = None
        if market_json:
            for entry in market_json.get("plugins", []):
                if isinstance(entry, dict) and entry.get("name") == plugin_name:
                    src = entry.get("source")
                    if isinstance(src, str):
                        source_rel = src
                    break
            else:
                # plugin not listed in this marketplace; keep looking
                if marketplace is None:
                    continue
        manifest = None
        if source_rel:
            manifest = (cand / source_rel / ".claude-plugin" / "plugin.json").resolve()
        if manifest is None or not manifest.is_file():
            # fallback: conventional plugins/<name> layout
            fallback = cand / "plugins" / plugin_name / ".claude-plugin" / "plugin.json"
            manifest = fallback if fallback.is_file() else manifest
        if manifest and manifest.is_file():
            return cand.name, manifest
    return marketplace, None


def full_plugin_id(plugin_name: str, marketplace: Optional[str]) -> str:
    return f"{plugin_name}@{marketplace}" if marketplace else plugin_name


def manifest_user_config(manifest_path: Optional[Path]) -> Dict[str, dict]:
    """Return the userConfig block: {KEY: {type, title, description, sensitive}}."""
    if not manifest_path:
        return {}
    data = load_json(manifest_path) or {}
    uc = data.get("userConfig", {})
    return uc if isinstance(uc, dict) else {}


# --------------------------------------------------------------------------- #
# Where values currently live
# --------------------------------------------------------------------------- #

def read_settings_options(config_dir: Path, full_id: str) -> List[Tuple[str, dict]]:
    """pluginConfigs[full_id].options from settings.json and settings.local.json.

    Returns a list of (filename, options-dict) for every settings file that has
    an entry, so callers can point at exactly which file holds a value.
    """
    found: List[Tuple[str, dict]] = []
    for fname in ("settings.json", "settings.local.json"):
        data = load_json(config_dir / fname)
        if not data:
            continue
        entry = (data.get("pluginConfigs") or {}).get(full_id)
        if isinstance(entry, dict) and isinstance(entry.get("options"), dict):
            found.append((fname, entry["options"]))
    return found


def credentials_state(config_dir: Path, plugin_name: str, keys: List[str]) -> dict:
    """Best-effort look at <config-dir>/.credentials.json (the keychain fallback).

    Never returns secret values -- only whether the file exists and whether it
    textually references the plugin or any of its config keys.
    """
    path = config_dir / ".credentials.json"
    state = {"path": str(path), "exists": path.is_file(), "mentions": []}
    if state["exists"]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return state
        for token in [plugin_name, *keys]:
            if token and token in text:
                state["mentions"].append(token)
    return state


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #

def is_macos() -> bool:
    return platform.system() == "Darwin"


def mask(value: Optional[str]) -> str:
    """Redact a secret for display: keep a 2-char shape hint, hide the rest."""
    if not value:
        return "****"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}…{value[-2:]} ({len(value)} chars)"
