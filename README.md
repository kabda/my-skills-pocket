# my-skills-pocket

Personal Claude Code plugin collection.

## Installation

### Step 1: Add the marketplace

```
/plugin marketplace add kabda/my-skills-pocket
```

### Step 2: Install a plugin

```
/plugin install skill-governor@my-skills-pocket
```

## Plugins

| Name | Description | Category |
|------|-------------|----------|
| [skill-governor](plugins/skill-governor/) | Manual slash command for auditing installed Claude Code skills for duplicates, overlaps, conflicts, and stale entries | productivity |

## Adding a new plugin

1. Copy `plugins/example-plugin/` to `plugins/<name>/`
2. Edit `.claude-plugin/plugin.json` with real metadata
3. Add your content to `skills/`, `commands/`, `agents/`, etc.
4. Register in `.claude-plugin/marketplace.json`
5. Push — Claude Code picks it up on next `/plugin` refresh
