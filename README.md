# ai-registry

A public registry of my personal [Claude Code](https://code.claude.com) customizations,
packaged as a **plugin marketplace** so they can be installed on any machine and kept in
sync. One source of truth, many laptops.

## Plugins

| Plugin | Skills | What it does |
|---|---|---|
| **planning** | `plan-hardening`, `spec-handoff-review` | Harden engineering plans and specs before implementation — iterative claim-against-code hardening, plus a final pre-handoff structural review. |
| **review** | `code-quality-scan`, `fact-check-document`, `cite-or-refuse` | Review code and verify claims — structural code-quality scanning, forensic document claim-verification, and a sourced "answer only if you can cite it" mode. |
| **git-tools** | `nuke-branches` | Git workflow utilities. |

## Install

Add the marketplace, then install the plugins you want:

```bash
/plugin marketplace add Ephasme/ai-registry
/plugin install planning@ai-registry
/plugin install review@ai-registry
/plugin install git-tools@ai-registry
/plugin marketplace update            # pull the latest after I push changes
```

Or use the bundled installer (adds the marketplace and installs every plugin at once):

```bash
scripts/ai-registry.sh install            # project scope by default
scripts/ai-registry.sh install user       # or install for all projects
```

See [`scripts/ai-registry.sh --help`](scripts/ai-registry.sh) for `--scope`, `--skip`, and
`--profile` options.

## Layout

```
ai-registry/
├── .claude-plugin/marketplace.json   # marketplace manifest
├── plugins/<name>/                   # one dir per plugin
│   ├── .claude-plugin/plugin.json
│   └── skills/<name>/SKILL.md
└── scripts/ai-registry.sh            # one-shot installer
```

## License

[MIT](LICENSE) © Loup Peluso
