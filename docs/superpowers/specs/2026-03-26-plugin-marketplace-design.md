# Design: my-skills-pocket Claude Code Plugin Marketplace

**Date:** 2026-03-26
**Status:** Approved

## Overview

`my-skills-pocket` is a personal Claude Code plugin marketplace hosted as a GitHub monorepo. It follows the same structure as `anthropics/claude-plugins-official`, making it fully compatible with Claude Code's `/plugin` system. Users add it via `extraKnownMarketplaces` in their `settings.json` and can then install plugins directly with `/plugin install <name>@my-skills-pocket`.

## Repository Structure

```
my-skills-pocket/
├── .claude-plugin/
│   └── marketplace.json          # Plugin registry (read by Claude Code)
├── plugins/                      # All plugin source code
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json       # Plugin metadata (required)
│       ├── skills/               # Skill markdown files (optional)
│       ├── commands/             # Slash commands (optional)
│       ├── agents/               # Agent definitions (optional)
│       ├── hooks/                # Hook scripts (optional)
│       ├── .mcp.json             # MCP server config (optional)
│       └── README.md
├── .gitignore
└── README.md                     # Installation instructions + plugin catalog
```

## Key Files

### `.claude-plugin/marketplace.json`

The registry file Claude Code reads to discover plugins.

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "my-skills-pocket",
  "description": "Personal Claude Code plugin collection by fanyuandong",
  "owner": { "name": "fanyuandong" },
  "plugins": [
    {
      "name": "plugin-name",
      "description": "One-line description",
      "source": "./plugins/plugin-name",
      "category": "productivity"
    }
  ]
}
```

Valid categories (from official marketplace): `development`, `productivity`, `testing`, `design`, `deployment`, `monitoring`, `automation`, `security`, `database`, `learning`, `migration`.

### `plugins/<name>/.claude-plugin/plugin.json`

Plugin metadata. Required fields: `name`, `description`. Recommended: `version` (semver), `author`, `homepage`.

```json
{
  "name": "plugin-name",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": {
    "name": "fanyuandong"
  },
  "homepage": "https://github.com/fanyuandong/my-skills-pocket/tree/main/plugins/plugin-name"
}
```

## Plugin Lifecycle

1. Create `plugins/<name>/` directory
2. Write `.claude-plugin/plugin.json`
3. Add content: `skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json` as needed
4. Append entry to `.claude-plugin/marketplace.json` `plugins` array
5. `git commit && git push` — users pull and see the new plugin

**Versioning:** `version` in `plugin.json` is human-readable semver. Claude Code tracks versions via git commit SHA internally.

## Plugin Content Conventions

- `skills/` — one `.md` file per skill; filename = skill name
- `commands/` — one file per command; filename = command name (no `/` prefix)
- `agents/` — agent definition files
- `hooks/` — executable scripts invoked by Claude Code hook system

## Initial State

The framework ships with `plugins/` empty and `marketplace.json` `plugins: []`. An `example-plugin` may be added as a template reference. Real plugins are added as needed.

## User Installation

Add to `~/.claude/settings.json`:

```json
"extraKnownMarketplaces": {
  "my-skills-pocket": {
    "source": {
      "source": "github",
      "repo": "fanyuandong/my-skills-pocket"
    }
  }
}
```

Then install a plugin:

```
/plugin install <plugin-name>@my-skills-pocket
```

## README Structure

**Root README.md:**
1. One-line description
2. Installation snippet (settings.json config)
3. Plugin catalog table (Name / Description / Type)

**Per-plugin README.md:**
1. Purpose
2. Included skills/commands/agents list
3. Usage examples
