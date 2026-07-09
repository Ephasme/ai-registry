---
name: plugin-config
description: Set, change, and diagnose Claude Code plugin userConfig values (API keys, tokens, Cloudflare Access credentials, and other plugin secrets) straight from the shell, without the interactive /plugin configure prompt. Use this whenever someone wants to configure or reconfigure a plugin non-interactively, bulk-configure many plugins or a whole profile at once (including decrypting a SOPS secrets dir and routing values to the plugins that declare them), the interactive plugin-config flow is buggy / stuck / "weird", a sensitive value needs rotating, or they ask where a plugin's config or secret is stored or why ${user_config.KEY} resolves empty / a plugin's MCP server fails to authenticate after being configured. Also use for multi-profile (CLAUDE_CONFIG_DIR) setups, and for setups that generate settings.json from a template (jsonnet, Nix, etc.) where sensitive values must NOT live in settings.json. Covers the storage split (macOS keychain vs Linux/headless .credentials.json vs settings.json) and bundles scripts to diagnose storage, set values across profiles, bulk-configure from env/JSON/SOPS sources, and discover the keychain entry.
---

# Plugin config (non-interactive)

Claude Code plugins can declare `userConfig` fields (API keys, tokens, service credentials). The interactive way to fill them is the `/plugin` configure dialog — which is fine until it isn't (it can be fiddly, and it gives you no visibility into _where_ a value ends up). This skill is the shell-driven alternative: set values deterministically, and diagnose them when something isn't resolving.

## The one thing to understand first: where values are stored

A field's storage location is decided by its `sensitive` flag **in the installed manifest** (not the source repo):

| `sensitive`    | Stored in                                                          | Confirm it's set?                    |
| -------------- | ----------------------------------------------------------------- | ------------------------------------ |
| `false`/absent | `<config-dir>/settings.json` → `pluginConfigs["<id>"].options`     | yes — it's plaintext                 |
| `true`         | macOS keychain; **else** `<config-dir>/.credentials.json`          | Linux/headless: **yes** (key present); macOS: no (opaque) |

Both kinds interpolate as `${user_config.KEY}` in the plugin's `.mcp.json`, LSP, hook, and monitor configs, and are exported to plugin subprocesses as `CLAUDE_PLUGIN_OPTION_<KEY>`.

On Linux / Windows / headless there's no OS keychain, so sensitive values land in `<config-dir>/.credentials.json` under `pluginSecrets["<id>"][KEY]`. That's parseable, so `diagnose.py` there **confirms a sensitive field is actually set** (by key presence — never the value), instead of guessing. On macOS the keychain naming is opaque, so confirmation still needs `keychain_probe.py` or just exercising the plugin.

This split is the source of almost every "I set it but it's empty" bug, because of one trap:

> **The installed manifest decides the destination.** If you set a value while the locally-cached manifest still marks the field non-sensitive, the value goes to `settings.json`. If the manifest later flips to `sensitive: true`, Claude Code now reads from the keychain (empty) and the `settings.json` copy is silently ignored — `${user_config.KEY}` resolves to empty. So **refresh the marketplace cache before setting**, so the manifest's flags are current.

For the full model, citations, and platform notes, read [references/storage-model.md](references/storage-model.md).

## The reliable path: `claude plugin install --config`

`claude plugin install <id> --config KEY=VALUE` (repeatable) writes each value through the _same_ code path as the interactive dialog — schema-validated, sensitive→keychain, plain→settings.json — but scriptably. There is no separate `claude plugin reconfigure`; re-running `install` with `--config` on an already-installed plugin is how you change values.

The bundled scripts wrap this with the marketplace-refresh step, multi-profile support, and verification. Prefer them over raw `claude` calls.

Run with `python3`; paths are under `${CLAUDE_PLUGIN_ROOT}/skills/plugin-config/scripts/`.

### 1. Diagnose first — `diagnose.py`

Always start here when something's off or before you change anything. It's read-only and never prints secrets.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/plugin-config/scripts/diagnose.py" <plugin>@<marketplace>
```

It reports, per config dir: each declared field, its `sensitive` flag, where the value currently sits, and — crucially — **mismatch warnings** (e.g. a sensitive field whose value is stranded in plaintext `settings.json` and is therefore being ignored). `--config-dir` is repeatable; `--json` for machine-readable out.

### 2. Set values — `set_config.py`

```bash
# Secrets: put the value in the environment so it stays out of shell history.
export MY_TOKEN="$(... however you fetch it ...)"     # vault, sops -d, 1password, etc.
python3 "${CLAUDE_PLUGIN_ROOT}/skills/plugin-config/scripts/set_config.py" \
    <plugin>@<marketplace> \
    --config-from-env MY_TOKEN \
    --config-dir ~/.claude-perso --config-dir ~/.claude-work \
    --keychain-probe

# Non-secrets can go inline:
python3 .../set_config.py <plugin>@<marketplace> --config SOME_ID=public-value
```

What it does, in order: refreshes the marketplace cache (so manifest flags are current — disable with `--no-update-marketplace`), prints where each value will land, runs the install per config dir, optionally diffs the keychain (`--keychain-probe`, macOS), then re-runs the diagnosis. Use `--dry-run` to see the exact commands (secrets masked) without executing.

Pass values with `--config-from-env KEY` for anything secret. The value is still handed to the underlying `claude` process as an argument (briefly visible to `ps` — a property of the CLI, not avoidable here), but it won't sit in your shell history. This skill is **secret-store-agnostic**: it never fetches secrets itself. Decrypt/retrieve them however the user already does, into an env var.

### 3. Configure many plugins at once — `bulk_config.py`

When you're setting up a whole machine or profile — every plugin's credentials in one go — don't loop `set_config.py` by hand. `bulk_config.py` builds one **value pool** from any mix of sources, discovers every installed plugin and its `userConfig` schema, and **auto-routes** each value to the plugin(s) that declare that key. It reports pool keys that matched no plugin (secrets with no home — expected for server-side config) and declared fields left unset.

```bash
# Decrypt a repo's SOPS secrets dir and fan the values out to every plugin that
# wants one, across both profiles. --dry-run first to see the routing (masked).
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
python3 "${CLAUDE_PLUGIN_ROOT}/skills/plugin-config/scripts/bulk_config.py" \
    --from-sops ~/code/ai-registry/secrets \
    --config-dir ~/.claude-work --config-dir ~/.claude-perso \
    --dry-run          # drop --dry-run to write
```

Value sources (combine freely; later overrides earlier): `--config KEY=VALUE`, `--config-from-env KEY`, `--from-json FILE` (flat `{KEY: value}`), `--from-sops PATH` (a `*.sops.json` file or a dir of them, decrypted via the `sops` binary), and `--env-all` (opportunistically pick up any *declared* key present as an env var). Nested/non-string JSON values are ignored — they aren't plugin `userConfig`. Scope with `--include`/`--exclude` (plugin name or `name@marketplace`). Full source/routing details: [references/bulk-and-sources.md](references/bulk-and-sources.md).

### 4. Find the keychain entry — `keychain_probe.py` (macOS)

The keychain service/account naming Claude Code uses for plugin secrets is undocumented, so you can't look an entry up by name with confidence. To learn where a value lives, snapshot → set → snapshot → diff (names only, never secrets):

```bash
python3 .../keychain_probe.py snapshot -o /tmp/before.txt
# ...set the value (set_config.py --keychain-probe does this diff for you)...
python3 .../keychain_probe.py snapshot -o /tmp/after.txt
python3 .../keychain_probe.py diff /tmp/before.txt /tmp/after.txt
```

Once discovered, you _can_ edit a sensitive value by hand with macOS tooling — Keychain Access.app (tick **Show password**, edit, Save) or `security add-generic-password -U -s "<service>" -a "<account>" -w "<value>"`. Going through `set_config.py` is safer because it uses Claude Code's own schema validation and storage path; reach for manual keychain edits only when the `claude` CLI itself is unavailable.

## Multi-profile setups

`CLAUDE_CONFIG_DIR` selects which config dir Claude Code uses (common for work/personal profiles). Plugin config is per-config-dir, so set it in each profile that enables the plugin — `set_config.py` takes repeatable `--config-dir` to do them in one call. The keychain itself is shared across profiles on a machine, but whether Claude Code namespaces an entry per config dir is undocumented, so setting per profile is the safe default.

## Generated-settings setups (jsonnet / Nix / etc.)

If `settings.json` is rendered from a template, **sensitive values must not be managed there**: Claude Code ignores the plaintext copy (it reads the keychain), and the next deploy would wipe it anyway. Keep only non-sensitive options in the template and set sensitive ones via `set_config.py` so they live in the keychain. `diagnose.py` will flag a sensitive value that has leaked into `settings.json`.

## Verifying it worked

On **Linux/headless**, `diagnose.py` reads `.credentials.json` and reports each sensitive field as `set` / `unset` by key presence — a real confirmation (never the value). On **macOS** the keychain is opaque: a clean run only proves no stale plaintext copy lingers, not that the write resolves at runtime. Either way, the decisive check is exercising the plugin — its MCP server should connect with no auth/login error. If `${user_config.KEY}` still comes back empty after a confirmed set, that's the manifest-mismatch trap above — re-run with the marketplace refreshed, or fall back to marking the field non-sensitive so the `settings.json` value is used. See the Troubleshooting section of [references/storage-model.md](references/storage-model.md).
