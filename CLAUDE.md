# ai-registry (public)

A public registry of personal Claude Code customizations — skills and the plugins that
bundle them — kept in one git repository and distributed as a **plugin marketplace** so they
can be cloned onto any machine and wired into a local Claude install.

## Goals

- **Single source of truth.** Every reusable customization lives here, version-controlled.
- **Clone-and-go.** On a new machine: add the marketplace, install the plugins. No copy-paste.
- **Public & secret-free.** Nothing here is machine-specific or sensitive; the repo is public.

## How it's consumed

Treat the repo as a **plugin marketplace**: `.claude-plugin/marketplace.json` at the root
catalogs the plugins under `plugins/`.

```bash
/plugin marketplace add Ephasme/ai-registry      # public repo → plain HTTPS, no auth
/plugin install <plugin-name>@ai-registry
/plugin marketplace update                        # pull latest after pushing changes
```

`scripts/ai-registry.sh install` does the add + install-all in one shot (see `--help`).

## Repository structure

```
ai-registry/
├── CLAUDE.md
├── LICENSE                         # MIT
├── README.md
├── .claude-plugin/marketplace.json # marketplace manifest
├── plugins/                        # one subdir per plugin
│   └── <plugin>/
│       ├── .claude-plugin/plugin.json
│       └── skills/<name>/SKILL.md
└── scripts/                        # helper scripts (the installer)
```

## Rules

### Allowed
- The author's own skills (`SKILL.md` + supporting files), slash commands, subagent definitions.
- Plugin and marketplace manifests, and documentation about the above.

### Forbidden (never commit)
- **Secrets**: API keys, tokens, passwords, OAuth credentials, `.credentials.json`.
- **Volatile/local state**: anything resembling `~/.claude.json`, session transcripts, `*.local.json`.
- **Hardcoded machine paths**: use `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`, or
  `${VAR:-default}` instead of absolute `/Users/...` paths.
- **Anything org-specific or non-public.** This repo is public — only the author's own,
  publishable skills belong here.

### Conventions
- Plugin/marketplace/skill `name` values are **kebab-case**, no spaces.
- A skill's invocation name is namespaced by plugin (`plugin-name:skill-name`).
- Keep `SKILL.md` bodies concise (target < 500 lines); push reference material into sibling
  files loaded on demand.
- Leave `version` unset in `plugin.json` so each commit counts as a new version.

## Adding / removing a plugin

1. Create `plugins/<plugin>/` with components at the plugin root (`skills/`, etc.); only
   `plugin.json` goes in `.claude-plugin/`.
2. Add an entry to `.claude-plugin/marketplace.json` (`name` + `source: "./plugins/<plugin>"`).
3. Validate: `claude plugin validate .` and `claude plugin validate ./plugins/<plugin>`.
4. Commit and push. Consumers run `/plugin marketplace update`.

To remove: delete `plugins/<plugin>/`, drop its `marketplace.json` entry, commit, push.
