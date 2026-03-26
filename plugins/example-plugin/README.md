# example-plugin

> Template plugin. Copy this directory to `plugins/<your-plugin-name>/` to create a new plugin.

## Contents

| Type | File | Description |
|------|------|-------------|
| Skill | `skills/example.md` | Example skill template |

## Adding to the marketplace

After creating your plugin, register it in `.claude-plugin/marketplace.json`:

```json
{
  "name": "your-plugin-name",
  "description": "One-line description",
  "source": "./plugins/your-plugin-name",
  "category": "productivity"
}
```

Valid categories: `development`, `productivity`, `testing`, `design`, `deployment`, `monitoring`, `automation`, `security`, `database`, `learning`, `migration`.

## Supported content types

- `skills/` — one `.md` file per skill; filename = skill name
- `commands/` — one file per slash command; filename = command name (no `/` prefix)
- `agents/` — agent definition files
- `hooks/` — hook scripts (must be explicitly registered in `plugin.json`)
- `.mcp.json` — MCP server configuration
