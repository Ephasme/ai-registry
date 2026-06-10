# Plugin userConfig storage model & troubleshooting

Reference for the `plugin-config` skill. Read this when you need the precise rules, the file locations, or a failure-mode walkthrough.

- [Storage rules](#storage-rules)
- [Where things live on disk](#where-things-live-on-disk)
- [The keychain](#the-keychain)
- [CLI reference](#cli-reference)
- [Troubleshooting](#troubleshooting)

## Storage rules

From the official plugin reference (code.claude.com/docs/en/plugins-reference, "User configuration" section):

- A plugin's `userConfig` declares fields Claude Code prompts for when the plugin is enabled. Each field can set `type`, `title`, `description`, and `sensitive`.
- **Non-sensitive** values are stored in `settings.json` under `pluginConfigs[<plugin-id>].options`.
- **Sensitive** values (`"sensitive": true`) go to the **system keychain**, or to `~/.claude/.credentials.json` where the keychain is unavailable.
- Every value is substitutable as `${user_config.KEY}` in MCP and LSP server configs, hook commands, and monitor commands. Non-sensitive values can *also* be substituted in skill and agent content (sensitive ones cannot).
- All values are exported to plugin subprocesses as environment variables named `CLAUDE_PLUGIN_OPTION_<KEY>`.

`<plugin-id>` is `<plugin-name>@<marketplace-name>`.

The documentation does **not** specify the keychain service/account naming for plugin secrets, nor a non-interactive way to set them beyond the install `--config` flag below. Those gaps are why this skill exists.

## Where things live on disk

Relative to a config dir (`$CLAUDE_CONFIG_DIR`, default `~/.claude`):

```
<config-dir>/
├── settings.json                         # pluginConfigs[...].options (non-sensitive)
├── settings.local.json                   # same shape, local overrides
├── .credentials.json                     # keychain fallback (when no keychain)
└── plugins/
    └── marketplaces/
        └── <marketplace>/
            ├── .claude-plugin/marketplace.json   # maps plugin name -> source dir
            └── plugins/<plugin>/.claude-plugin/plugin.json   # the INSTALLED manifest
```

The **installed manifest** is the cached copy under `plugins/marketplaces/...`, refreshed by `claude plugin marketplace update`. Its `sensitive` flags — not the flags in your source repo — decide where a value is stored at set-time. The skill's `diagnose.py` resolves this path (via `marketplace.json`, falling back to `plugins/<name>/`).

## The keychain

On macOS, generic-password items. Empirically (via `security dump-keychain`, which lists item attributes without exposing secrets):

- `Claude Code-credentials` and `Claude Code-credentials-<hash>` (account `<user>`) are **OAuth/login tokens**, one per config dir — *not* plugin config.
- No item is named after a plugin or a config key, confirming the naming for plugin secrets is opaque/undocumented.

So the only reliable way to find where a sensitive plugin value landed is a before/after diff — see `keychain_probe.py`. Once you know the service+account, manual edits are possible:

```bash
# read attributes only (no secret):  security find-generic-password -s "<svc>" -a "<acct>"
# overwrite the secret in place:
security add-generic-password -U -s "<service>" -a "<account>" -w "<new-value>"
```

…but prefer `set_config.py`, which uses Claude Code's own validated storage path.

**Linux / Windows / headless:** if no OS keychain is available, sensitive values fall back to `<config-dir>/.credentials.json`. `keychain_probe.py` is macOS-only (`security`); on other platforms, inspect `.credentials.json` (it also holds OAuth tokens — treat it as secret).

## CLI reference

```bash
# set userConfig non-interactively (repeatable); same storage path as the dialog
claude plugin install <plugin>@<marketplace> --config KEY=VALUE [--config K2=V2 ...]
  --scope user|project|local        # default: user

# refresh the cached marketplace (and thus installed manifests) from source
claude plugin marketplace update [<marketplace>]     # all if no name

# inspect
claude plugin list
claude plugin marketplace list
```

There is no `claude plugin reconfigure` — re-running `install --config` updates values. `CLAUDE_CONFIG_DIR=<dir>` in front of any of these targets a specific profile.

## Troubleshooting

### `${user_config.KEY}` resolves empty (MCP server fails auth, "text/html" login, etc.)

Most often the **manifest-mismatch trap**: the value was written to one store but Claude Code reads the other.

1. `diagnose.py <id>` — it flags "sensitive field, value in plaintext settings.json → ignored", or "currently unset".
2. If the field *should* be sensitive: ensure the installed manifest says so (`claude plugin marketplace update <marketplace>`, or let `set_config.py` do it), then re-set the value with `set_config.py` so it goes to the keychain.
3. If you *want* the value to live in `settings.json` (e.g. it's templated by jsonnet/Nix and you don't want keychain involvement), make the field **non-sensitive** in the manifest instead — then the `settings.json` value is honored. This is the pragmatic fix when keychain storage misbehaves.

### Set succeeded but you're not sure the keychain write took

Sensitive values can't be read back by name. Run `set_config.py --keychain-probe` (it diffs the keychain around the change) and, decisively, exercise the plugin — a working MCP connection is the real confirmation.

### Value disappears after a deploy

A sensitive value written into a generated `settings.json` will be both ignored and overwritten on the next render. Keep sensitive values out of the template and set them via `set_config.py`; keep only non-sensitive options templated.

### Multiple marketplaces provide the same plugin name

Pass the explicit `<name>@<marketplace>` form so the right manifest and `pluginConfigs` key are used. `diagnose.py` without a marketplace picks the first match and may be ambiguous.
