# skill-governor

Audits all installed Claude Code skills for quality issues: duplicates, overlaps, conflicts, and stale entries.

## Contents

| Type | File | Description |
|------|------|-------------|
| Skill | `skills/skill-governor/SKILL.md` | Three-phase skill audit workflow |
| Reference | `skills/skill-governor/references/analysis-prompts.md` | Subagent prompt templates for Phase 2 |

## Usage

Invoke by asking Claude to audit your skills:

- "audit skills"
- "check skill health"
- "find duplicate skills"
- "skill conflicts"
- "skill quality"

## How it works

Runs a three-phase analysis:

1. **Discover & Index** — scans `~/.claude/plugins/cache/` for all installed SKILL.md files, deduplicates by version
2. **Deep Analysis** — dispatches 4 parallel subagents (duplicate, overlap, conflict, stale detection)
3. **Merge & Report** — combines findings into a structured audit report
