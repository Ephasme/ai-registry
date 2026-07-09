# Bulk configuration & secret sources

Reference for `bulk_config.py`. Read this to configure many plugins at once and
to feed values from files or an encrypted secrets store instead of typing them.

- [The value-pool model](#the-value-pool-model)
- [Sources](#sources)
- [Decrypting a SOPS secrets dir](#decrypting-a-sops-secrets-dir)
- [Routing, filtering, profiles](#routing-filtering-profiles)
- [Reading the report](#reading-the-report)

## The value-pool model

`bulk_config.py` does three things:

1. **Collect** every value you give it — from any mix of sources — into one flat
   `KEY -> value` pool.
2. **Discover** every plugin installed in each target config dir (from
   `plugins/installed_plugins.json`) and read each one's `userConfig` schema.
3. **Route** each pool key to the plugin(s) that *declare* it, then set those via
   the same `claude plugin install --config` path as `set_config.py` (so
   sensitive → keychain/`.credentials.json`, plain → `settings.json`).

You never say "this key belongs to that plugin" — the plugins' own manifests
decide. A key no plugin declares is reported, not force-fit. This is the
whole-machine / whole-profile setup path; for a single plugin use `set_config.py`.

## Sources

Combine any of these; they merge into one pool. On a key collision a later source
overrides an earlier one (with a printed `note:`).

| Flag | Value | Notes |
| ---- | ----- | ----- |
| `--config KEY=VALUE` | inline | Ends up in shell history — fine for non-secrets. |
| `--config-from-env KEY` | `$KEY` | Keeps the secret out of history. |
| `--from-json FILE` | flat `{ "KEY": "value" }` | Nested objects and non-string values are **ignored** (they aren't `userConfig` — e.g. structured server-side config). |
| `--from-sops PATH` | `*.sops.json` file, or a dir of them | Decrypted with the `sops` binary; same flat-JSON rule as `--from-json`. |
| `--env-all` | — | After the explicit sources, also pull any **declared** key that exists as an env var and isn't already pooled. Scoped to declared keys so it never dumps unrelated env. |

## Decrypting a SOPS secrets dir

`--from-sops` shells out to [`sops`](https://github.com/getsops/sops) `-d` for
each `*.sops.json`, so you need two things on the machine:

1. **The `sops` binary** on `PATH` (a single static release binary).
2. **A decryption key** sops can find. For age that's a private key at
   `~/.config/sops/age/keys.txt`, or a path in `$SOPS_AGE_KEY_FILE`.

Bootstrapping the age key (retrieve the private key from wherever you keep it — a
password manager, a vault, another machine — this skill never fetches secrets for
you):

```bash
mkdir -p ~/.config/sops/age && umask 077
# ... write the AGE-SECRET-KEY-1... line into keys.txt however you retrieve it ...
chmod 600 ~/.config/sops/age/keys.txt

# Sanity-check the key matches the recipient the files were encrypted to:
grep -v '^#' ~/.config/sops/age/keys.txt | age-keygen -y     # prints the public key
grep -o 'age1[0-9a-z]*' <your-repo>/.sops.yaml                # must match
```

Then decrypt-and-route in one shot (always `--dry-run` first — it prints the full
routing with secrets masked and writes nothing):

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
python3 bulk_config.py --from-sops <repo>/secrets \
    --config-dir ~/.claude-work --config-dir ~/.claude-perso --dry-run
```

Values that live outside SOPS (e.g. a session token minted at setup time, like a
Bitwarden `BW_SESSION`) won't be in the pool — set those separately with
`set_config.py`, or add them via `--config-from-env`. They show up under
"declared fields with no value" in the report, which is the reminder to do so.

## Routing, filtering, profiles

- **Profiles:** `--config-dir` is repeatable; each dir is configured
  independently against *its own* installed plugins and manifests. Marketplaces
  are refreshed once per dir (not once per plugin) unless `--no-update-marketplace`.
- **Filtering:** `--include` / `--exclude` take a plugin `name` or full
  `name@marketplace` (repeatable). Include restricts to the listed plugins;
  exclude removes them.
- **Scope:** `--scope user|project|local` (default `user`), passed straight to
  `claude plugin install`.
- **Idempotent:** re-running with the same pool just re-sets the same values;
  safe to run repeatedly (e.g. after adding a new plugin or rotating one secret).

## Reading the report

The summary tells you three things that matter:

- **`N plugin(s), M value(s) routed`** with a `→ plugin: keys` line each — what
  actually got set.
- **`unused pool keys`** — pool values no installed plugin declares. Expected for
  server-side secrets that were decrypted alongside the plugin ones (they simply
  have no `userConfig` home); a surprise here can also mean a typo'd key or a
  plugin that isn't installed.
- **`declared fields with no value`** — `userConfig` fields left unset because the
  pool didn't carry them. Fine for optional fields; a to-do for required ones.

Verify the result per plugin with `diagnose.py` (on Linux/headless it confirms
each sensitive field is present), and decisively by checking the plugin's MCP
server connects.
