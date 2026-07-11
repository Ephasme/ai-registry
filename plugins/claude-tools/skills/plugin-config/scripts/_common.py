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


def _installed_plugin_paths(
    config_dir: Path, plugin_name: str, marketplace: Optional[str]
):
    """Yield (marketplace_name, install_path) recorded in installed_plugins.json.

    This is the source of truth for what is *actually installed*, and it works for
    every marketplace source type -- git, directory, or local -- because the path
    points straight at the unpacked plugin in the cache rather than re-deriving it
    from a (possibly absent) marketplaces/<name> mirror.
    """
    data = load_json(config_dir / "plugins" / "installed_plugins.json")
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return
    for full_id, entries in plugins.items():
        name, market = parse_plugin_id(full_id)
        if name != plugin_name:
            continue
        if marketplace and market != marketplace:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("installPath"):
                yield market, Path(entry["installPath"]).expanduser()


def _manifest_from_marketplace_root(
    root: Path, plugin_name: str, marketplace_name: Optional[str]
) -> Optional[Path]:
    """Resolve plugin.json under a marketplace root (dir holding marketplace.json).

    Honors the marketplace.json `source` for the plugin (so a source dir differing
    from the plugin name still resolves), then falls back to the conventional
    plugins/<name> layout. Returns the manifest Path or None.
    """
    market_json = load_json(root / ".claude-plugin" / "marketplace.json")
    source_rel = None
    if market_json:
        for entry in market_json.get("plugins", []):
            if isinstance(entry, dict) and entry.get("name") == plugin_name:
                src = entry.get("source")
                if isinstance(src, str):
                    source_rel = src
                break
    manifest = None
    if source_rel:
        manifest = (root / source_rel / ".claude-plugin" / "plugin.json").resolve()
    if manifest is None or not manifest.is_file():
        fallback = root / "plugins" / plugin_name / ".claude-plugin" / "plugin.json"
        manifest = fallback if fallback.is_file() else manifest
    return manifest if (manifest and manifest.is_file()) else None


def _marketplace_roots(
    config_dir: Path, marketplace: Optional[str]
) -> List[Tuple[str, Path]]:
    """Candidate (marketplace_name, root_dir) pairs to search for a plugin manifest.

    Covers directory/local-source marketplaces -- whose root lives wherever the
    user cloned it, recorded in known_marketplaces.json and NOT mirrored under
    plugins/marketplaces/ -- as well as the cached git marketplaces that are.
    """
    roots: List[Tuple[str, Path]] = []
    known = load_json(config_dir / "plugins" / "known_marketplaces.json")
    if isinstance(known, dict):
        for name, meta in known.items():
            if marketplace and name != marketplace:
                continue
            if not isinstance(meta, dict):
                continue
            loc = meta.get("installLocation")
            if not loc and isinstance(meta.get("source"), dict):
                loc = meta["source"].get("path")
            if isinstance(loc, str) and loc:
                roots.append((name, Path(loc).expanduser()))
    mdir = _marketplaces_dir(config_dir)
    if mdir.is_dir():
        cands = [mdir / marketplace] if marketplace else sorted(
            p for p in mdir.iterdir() if p.is_dir()
        )
        for cand in cands:
            if cand.is_dir():
                roots.append((cand.name, cand))
    return roots


def resolve_manifest(
    config_dir: Path, plugin_name: str, marketplace: Optional[str]
) -> Tuple[Optional[str], Optional[Path]]:
    """Locate the installed plugin.json for a plugin in a config dir.

    Returns (marketplace_name, manifest_path). Either may be None when the
    plugin/marketplace can't be found.

    Resolution order:
      1. installed_plugins.json -> installPath/.claude-plugin/plugin.json. Most
         reliable: it pins the *installed* manifest (whose `sensitive` flags
         actually govern storage) and is source-type agnostic.
      2. A marketplace root -- including directory/local-source marketplaces taken
         from known_marketplaces.json, not only the cached git mirrors under
         plugins/marketplaces/. The marketplace.json `source` is honored with a
         plugins/<name> fallback.
    """
    for market, install_path in _installed_plugin_paths(
        config_dir, plugin_name, marketplace
    ):
        manifest = install_path / ".claude-plugin" / "plugin.json"
        if manifest.is_file():
            return market or marketplace, manifest

    for market_name, root in _marketplace_roots(config_dir, marketplace):
        manifest = _manifest_from_marketplace_root(root, plugin_name, market_name)
        if manifest:
            return market_name, manifest

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


def credentials_secret_keys(config_dir: Path, full_id: str) -> Optional[List[str]]:
    """Declared secret keys present for a plugin in <config-dir>/.credentials.json.

    On Linux/Windows/headless (no OS keychain) Claude Code stores sensitive
    userConfig values in .credentials.json under::

        {"pluginSecrets": {"<plugin>@<marketplace>": {"<KEY>": "<wrapped-value>"}}}

    and this file is the *actual* sensitive store, so its contents -- or its
    total absence -- confidently tell us whether a key is set. On macOS the
    keychain is the real store; this file may exist for unrelated reasons
    (e.g. holding only an OAuth login token) or be absent entirely while a
    plugin's secret still lives safely in the keychain, so nothing read from
    here can be trusted as a confident answer on that platform.

    This returns the list of KEY names present for ``full_id`` -- names only,
    never the values -- so callers can *confirm a sensitive field is actually
    set* rather than guessing. Returns:

      - a list of key names (possibly empty, including when the file doesn't
        exist at all) on non-macOS platforms, where this file is
        authoritative; or
      - None when the sensitive store can't be confirmed from here: on macOS,
        or when .credentials.json exists but isn't parseable JSON (genuinely
        unreadable, as opposed to simply lacking an entry).
    """
    path = config_dir / ".credentials.json"
    if not path.is_file():
        # Absence is only conclusive on the platform where this file is the
        # actual store -- on macOS the keychain may still hold the value.
        return None if is_macos() else []
    data = load_json(path)
    if not isinstance(data, dict):
        return None
    if is_macos():
        return None
    ps = data.get("pluginSecrets")
    if not isinstance(ps, dict):
        # File exists (e.g. holds only OAuth tokens) but no plugin secrets map.
        return []
    entry = ps.get(full_id)
    if not isinstance(entry, dict):
        return []
    return sorted(entry.keys())


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
# Installed-plugin inventory
# --------------------------------------------------------------------------- #

def list_installed_plugins(config_dir: Path) -> List[str]:
    """Full ids ("<name>@<marketplace>") of plugins installed in a config dir.

    Reads plugins/installed_plugins.json, the source of truth for what is
    actually installed. Only ids with at least one entry carrying an installPath
    are returned. Sorted, de-duplicated.
    """
    data = load_json(config_dir / "plugins" / "installed_plugins.json")
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return []
    out = set()
    for full_id, entries in plugins.items():
        if not isinstance(entries, list):
            continue
        if any(isinstance(e, dict) and e.get("installPath") for e in entries):
            out.add(full_id)
    return sorted(out)


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #

def is_macos() -> bool:
    return platform.system() == "Darwin"


def sensitive_store_label() -> str:
    """Human name for where sensitive values land on this platform."""
    return "macOS keychain" if is_macos() else ".credentials.json"


def mask(value: Optional[str]) -> str:
    """Redact a secret for display: keep a 2-char shape hint, hide the rest."""
    if not value:
        return "****"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}…{value[-2:]} ({len(value)} chars)"
