# ai-registry

A public registry of my personal [Claude Code](https://code.claude.com) customizations,
packaged as a **plugin marketplace** so they can be installed on any machine and kept in
sync. One source of truth, many laptops.

Plugins are organized **by purpose** — what you're trying to do — not by mechanism. A skill
and an MCP server live in the same plugin when they serve the same goal (e.g. `research`
bundles the fact-checking skills together with Exa web search).

## Plugins

| Plugin | Purpose | What's inside |
|---|---|---|
| **engineering** | Build & ship software | skills: `writing-technical-specs`, `plan-hardening`, `spec-handoff-review`, `code-quality-scan`, `document-codebase`, `prune-branches` · MCP: GitHub |
| **research** | Find & verify information | skills: `cite-or-refuse`, `fact-check-document` · MCP: Exa web search |
| **communication** | Reach people | MCP: Slack, WhatsApp (wacli) |
| **workspace** | Email, calendar, files | MCP: Google Workspace ×3 (perso / work / cassandra) |
| **navigation** | Places & directions | MCP: Google Maps |
| **finance** | Money | MCP: bank-mcp (read-only banking) |
| **automation** | Automate workflows | MCP: n8n |
| **claude-tools** | Configure Claude Code itself | skill: `plugin-config` |

The `communication`, `workspace`, and `navigation` servers are self-hosted behind Cloudflare
Access; they share one service token, kept once in `secrets/cloudflare-access.sops.json` and
symlinked into each plugin. `research` (Exa) uses `secrets/exa.sops.json`. Both are
SOPS-encrypted — the plaintext never touches the repo.

## Install

Add the marketplace, then install the plugins you want:

```bash
/plugin marketplace add Ephasme/ai-registry
/plugin install engineering@ai-registry
/plugin install research@ai-registry        # prompts for an Exa API key (optional)
/plugin install communication@ai-registry   # prompts for Cloudflare Access creds
/plugin install workspace@ai-registry
/plugin install navigation@ai-registry
/plugin install finance@ai-registry
/plugin install automation@ai-registry       # prompts for n8n URL + API key (both optional)
/plugin install claude-tools@ai-registry
/plugin marketplace update                    # pull the latest after I push changes
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
├── plugins/<purpose>/                # one dir per purpose-domain
│   ├── .claude-plugin/plugin.json
│   ├── skills/<name>/SKILL.md        # skills (if any)
│   ├── .mcp.json                     # MCP servers (if any)
│   └── mcp-secrets.sops.json         # symlink into secrets/ (if it needs a shared secret)
├── secrets/                          # SOPS-encrypted maintainer secrets (shared, symlinked)
└── scripts/ai-registry.sh            # one-shot installer
```

## License

[MIT](LICENSE) © Loup Peluso
