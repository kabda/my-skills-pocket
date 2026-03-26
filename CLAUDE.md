# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal Claude Code plugin marketplace. Plugins are installed via:

```
/plugin marketplace add kabda/my-skills-pocket
/plugin install <plugin-name>@my-skills-pocket
```

## Repository structure

```
.claude-plugin/
  marketplace.json          # Registry of all published plugins
plugins/
  example-plugin/           # Template — copy to create new plugins
  <plugin-name>/
    .claude-plugin/
      plugin.json           # Plugin metadata (name, version, author, etc.)
    skills/
      <skill-name>/
        SKILL.md            # Skill definition with YAML frontmatter
        references/         # Supporting reference files for the skill
    commands/               # Slash commands (.gitkeep if empty)
    agents/                 # Agent definitions (.gitkeep if empty)
    hooks/                  # Hook scripts (.gitkeep if empty)
    README.md
```

## Adding a new plugin

1. Copy `plugins/example-plugin/` to `plugins/<name>/`
2. Update `.claude-plugin/plugin.json` with real metadata
3. Add skill content to `skills/<skill-name>/SKILL.md`
4. Register the plugin in `.claude-plugin/marketplace.json` under `plugins[]`
5. Update the root `README.md` plugins table

## Plugin conventions

**plugin.json** required fields: `name`, `description`, `version`, `author.name`, `homepage`, `repository`, `license`

**SKILL.md** must start with YAML frontmatter:
```yaml
---
name: skill-name
description: Use when <trigger condition>. Use when asked to "<phrase1>", "<phrase2>".
---
```

**marketplace.json** entry shape:
```json
{
  "name": "plugin-name",
  "description": "One-line description",
  "source": "./plugins/plugin-name",
  "category": "productivity"
}
```

Valid categories: `development`, `productivity`, `testing`, `design`, `deployment`, `monitoring`, `automation`, `security`, `database`, `learning`, `migration`

## Skill description quality rules

Good skill descriptions must include "Use when" trigger conditions — vague capability lists without trigger patterns make skills hard to discover. See `plugins/skill-governor/` for an audit tool that checks this.
