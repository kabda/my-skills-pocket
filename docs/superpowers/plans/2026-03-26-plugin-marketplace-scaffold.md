# Plugin Marketplace Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold `my-skills-pocket` as a fully functional Claude Code plugin marketplace monorepo, compatible with the `/plugin` system via `extraKnownMarketplaces`.

**Architecture:** A single GitHub repo where `.claude-plugin/marketplace.json` serves as the plugin registry, and `plugins/` contains all plugin source code. An `example-plugin` ships with the framework as a copy-paste template for new plugins.

**Tech Stack:** Plain JSON + Markdown. No build tooling required.

---

### Task 1: Create marketplace registry

**Files:**
- Create: `.claude-plugin/marketplace.json`

> Context: This is the file Claude Code reads to discover plugins in this marketplace. The `$schema` field references Anthropic's schema. `plugins` starts empty — `example-plugin` is a template, not a real plugin for distribution.

- [ ] **Step 1: Create `.claude-plugin/` directory and `marketplace.json`**

```bash
mkdir -p .claude-plugin
```

Create `.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "my-skills-pocket",
  "description": "Personal Claude Code plugin collection by kabda",
  "owner": { "name": "kabda" },
  "plugins": []
}
```

- [ ] **Step 2: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add marketplace registry"
```

---

### Task 2: Create example-plugin as a template

**Files:**
- Create: `plugins/example-plugin/.claude-plugin/plugin.json`
- Create: `plugins/example-plugin/skills/example.md`
- Create: `plugins/example-plugin/README.md`

> Context: This plugin exists purely as a template. It is NOT registered in `marketplace.json`. Developers copy it when adding a new plugin. It demonstrates all supported content types (skills shown; commands/agents/hooks are shown as empty dirs with comments in README).

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p plugins/example-plugin/.claude-plugin
mkdir -p plugins/example-plugin/skills
mkdir -p plugins/example-plugin/commands
mkdir -p plugins/example-plugin/agents
mkdir -p plugins/example-plugin/hooks
```

- [ ] **Step 2: Create `plugins/example-plugin/.claude-plugin/plugin.json`**

```json
{
  "name": "example-plugin",
  "description": "Template plugin — copy this directory to create a new plugin",
  "version": "1.0.0",
  "author": {
    "name": "kabda"
  },
  "homepage": "https://github.com/kabda/my-skills-pocket/tree/main/plugins/example-plugin",
  "repository": "https://github.com/kabda/my-skills-pocket",
  "license": "MIT",
  "keywords": ["example", "template"]
}
```

- [ ] **Step 3: Create `plugins/example-plugin/skills/example.md`**

```markdown
---
name: example
description: Example skill — replace this with your skill's description
---

# Example Skill

This is a template skill file. Replace this content with your skill's instructions.

## Usage

Describe when and how to invoke this skill.

## Steps

1. Step one
2. Step two
3. Step three
```

- [ ] **Step 4: Create `plugins/example-plugin/README.md`**

Write the following content to `plugins/example-plugin/README.md` (use the Write tool, not a shell heredoc):

````
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
````

- [ ] **Step 5: Add `.gitkeep` to empty dirs so git tracks them**

```bash
touch plugins/example-plugin/commands/.gitkeep
touch plugins/example-plugin/agents/.gitkeep
touch plugins/example-plugin/hooks/.gitkeep
```

- [ ] **Step 6: Verify plugin.json is valid**

```bash
python3 -c "import json; json.load(open('plugins/example-plugin/.claude-plugin/plugin.json')); print('OK')"
```

Expected output: `OK`

- [ ] **Step 7: Commit**

```bash
git add plugins/
git commit -m "feat: add example-plugin template"
```

---

### Task 3: Create root README

**Files:**
- Create: `README.md`

> Context: The root README is the public face of this marketplace. It should tell users how to add the marketplace to their Claude Code settings and what plugins are available.

- [ ] **Step 1: Create `README.md`**

Write the following content to `README.md` (use the Write tool, not a shell heredoc):

````
# my-skills-pocket

Personal Claude Code plugin collection.

## Installation

Add to `~/.claude/settings.json`:

```json
"extraKnownMarketplaces": {
  "my-skills-pocket": {
    "source": {
      "source": "github",
      "repo": "kabda/my-skills-pocket"
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
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "feat: add root README with installation instructions"
```

---

### Task 4: Create .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```
.DS_Store
*.swp
*.swo
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

### Task 5: Verify marketplace structure

> Context: Manually verify Claude Code can recognize the marketplace by checking the structure matches what the plugin system expects.

- [ ] **Step 1: Confirm directory structure matches spec**

```bash
find . -not -path './.git/*' | sort
```

Expected output should include:
```
./.claude-plugin/marketplace.json
./plugins/example-plugin/.claude-plugin/plugin.json
./plugins/example-plugin/README.md
./plugins/example-plugin/agents/.gitkeep
./plugins/example-plugin/commands/.gitkeep
./plugins/example-plugin/hooks/.gitkeep
./plugins/example-plugin/skills/example.md
./README.md
./.gitignore
```

- [ ] **Step 2: Validate all JSON files**

```bash
for f in $(find . -name "*.json" -not -path './.git/*'); do
  python3 -c "import json; json.load(open('$f')); print('OK: $f')"
done
```

Expected: all files print `OK`.

- [ ] **Step 3: Check git log looks clean**

```bash
git log --oneline
```

Expected: 6 commits visible (spec + spec-fix + marketplace + example-plugin + readme + gitignore).

- [ ] **Step 4: Push to GitHub**

```bash
git push -u origin main
```

Then open `https://github.com/kabda/my-skills-pocket` and verify the repo is visible.

- [ ] **Step 5: Test marketplace discovery in Claude Code**

Add to `~/.claude/settings.json` under `extraKnownMarketplaces`:

```json
"my-skills-pocket": {
  "source": {
    "source": "github",
    "repo": "kabda/my-skills-pocket"
  }
}
```

Run `/plugin` in Claude Code and verify `my-skills-pocket` appears as a known marketplace.

---

## Adding your first real plugin (post-scaffold reference)

Once the scaffold is live, add a real plugin:

1. `cp -r plugins/example-plugin plugins/<name>`
2. Edit `plugins/<name>/.claude-plugin/plugin.json` — set real `name`, `description`, `version`, `keywords`
3. Replace `plugins/<name>/skills/example.md` with your actual skill files
4. Remove `.gitkeep` files from dirs you're using; keep them only in unused dirs
5. Append to `.claude-plugin/marketplace.json` `plugins` array:
   ```json
   { "name": "<name>", "description": "...", "source": "./plugins/<name>", "category": "productivity" }
   ```
6. Update root `README.md` plugin catalog table
7. `git commit && git push`
