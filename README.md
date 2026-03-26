# my-skills-pocket

Personal Claude Code plugin collection.

## Installation

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

Then run `/plugin` in Claude Code to refresh the marketplace, and install a plugin:

```
/plugin install <plugin-name>@my-skills-pocket
```

## Plugins

| Name | Description | Category |
|------|-------------|----------|
| *(none yet)* | | |

## Adding a new plugin

1. Copy `plugins/example-plugin/` to `plugins/<name>/`
2. Edit `.claude-plugin/plugin.json` with real metadata
3. Add your content to `skills/`, `commands/`, `agents/`, etc.
4. Register in `.claude-plugin/marketplace.json`
5. Push — Claude Code picks it up on next `/plugin` refresh
