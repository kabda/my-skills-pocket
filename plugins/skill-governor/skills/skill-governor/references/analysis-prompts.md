# Analysis Subagent Prompt Templates

These are the prompt templates for Phase 2's four parallel subagents. Each subagent receives the full skill index table from Phase 1 as context.

---

## Duplicate Detection Subagent

**Prompt template** (insert the index table where marked):

````
You are a skill duplicate detector. Analyze the following skill index and identify skills that solve the same core task.

## Skill Index
{INDEX_TABLE}

## Detection Rules

1. **Same-name cross-suite**: If two skills have the same `name` but different `suite`, flag immediately as duplicate.
2. **Semantic duplicate**: If two skills' descriptions indicate they would both trigger for >80% of the same user requests, flag as duplicate.

## Process

1. Scan the index for same-name entries across different suites.
2. For each potential semantic duplicate pair, Read both SKILL.md files in full to confirm.
3. Only flag pairs where the core task is genuinely the same — shared keywords alone are not enough.

## Budget

You may Read at most 15 SKILL.md files total.

## Output Format

Return ONLY valid JSON:

```
{
  "type": "duplicate",
  "findings": [
    {
      "id": "D-1",
      "severity": "critical",
      "skills": ["skill-a (suite-a)", "skill-b (suite-b)"],
      "reason": "Both skills create implementation plans from specs. make-plan uses claude-mem's memory system while writing-plans uses superpowers' brainstorming flow, but the core task is identical.",
      "recommendation": "Designate one as primary for plan creation; update the other's description to clarify its unique scope (e.g., memory-backed plans vs. spec-driven plans).",
      "details": {}
    }
  ]
}
```

If no duplicates found, return: {"type": "duplicate", "findings": []}
````

---

## Overlap Detection Subagent

**Prompt template**:

````
You are a skill overlap detector. Analyze the following skill index and identify skills with partially overlapping trigger conditions.

## Skill Index
{INDEX_TABLE}

## Detection Rules

1. Two skills overlap when their descriptions suggest they would BOTH trigger for some user requests, but each also has unique scenarios the other does not cover.
2. Overlap is distinct from duplicate: overlapping skills have different core purposes but share edge-case scenarios.
3. If the overlapping scenarios exceed 50% of either skill's total trigger scenarios, escalate severity to "critical".

## Process

1. Identify skill pairs whose descriptions share trigger keywords or scenarios.
2. For each candidate pair, Read both SKILL.md files to understand their full scope.
3. List the specific overlapping scenarios and each skill's unique scenarios.
4. Assess overlap percentage and determine severity.

## Budget

You may Read at most 15 SKILL.md files total.

## Output Format

Return ONLY valid JSON:

```
{
  "type": "overlap",
  "findings": [
    {
      "id": "O-1",
      "severity": "warning",
      "skills": ["design-system (ui-ux-pro-max)", "brand-guidelines (anthropic-agent-skills)"],
      "reason": "Both trigger when creating brand color and typography specs. design-system focuses on code-level design tokens; brand-guidelines focuses on non-technical brand documents.",
      "recommendation": "Add explicit boundary in descriptions: design-system for code/tokens, brand-guidelines for marketing/print materials.",
      "details": {
        "overlap_scenarios": ["brand color definition", "typography specification", "spacing standards"],
        "boundary_suggestion": "design-system -> code-level design tokens and CSS variables; brand-guidelines -> PDF/document brand guides for non-technical stakeholders"
      }
    }
  ]
}
```

If no overlaps found, return: {"type": "overlap", "findings": []}
````

---

## Conflict Detection Subagent

**Prompt template**:

````
You are a skill conflict detector. Analyze the following skill index and identify skills that give contradictory rules for the same type of task.

## Skill Index
{INDEX_TABLE}

## Detection Rules

Conflicts occur when two skills:
1. Both claim authority over the same task type, AND
2. Give OPPOSITE instructions for how to handle it (different directory conventions, different output formats, different tool usage strategies, different workflow orders)

A conflict is NOT just overlap — it's active contradiction. Skill A says "always do X" while Skill B says "never do X" for the same scenario.

## Process

1. Identify skill pairs that both claim to handle the same task type.
2. Read both SKILL.md files in full.
3. Compare their instructions line-by-line for contradictions in:
   - Workflow steps (different order, missing steps)
   - Tool usage (different tools for same purpose)
   - Output format (different schemas, different locations)
   - Directory conventions (different paths for same artifacts)
   - Rules and constraints (opposite restrictions)

## Budget

You may Read at most 15 SKILL.md files total.

## Output Format

Return ONLY valid JSON:

```
{
  "type": "conflict",
  "findings": [
    {
      "id": "C-1",
      "severity": "critical",
      "skills": ["make-plan (claude-mem)", "writing-plans (superpowers)"],
      "reason": "Both claim to be the entry point for creating implementation plans. make-plan outputs to a different directory and uses a different format than writing-plans. A user asking 'plan this feature' could trigger either with incompatible results.",
      "recommendation": "Establish priority: writing-plans for spec-driven plans in the superpowers workflow; make-plan for ad-hoc plans with memory integration. Update descriptions to be mutually exclusive.",
      "details": {
        "conflict_points": ["plan output directory", "plan format/template", "entry point claim"]
      }
    }
  ]
}
```

If no conflicts found, return: {"type": "conflict", "findings": []}
````

---

## Stale Detection Subagent

**Prompt template**:

````
You are a skill staleness detector. Analyze the following skill index and identify skills that are outdated, broken, or poorly defined.

## Skill Index
{INDEX_TABLE}

## Detection Rules

Check each skill for these issues:

### 1. Missing references (severity: warning)
The SKILL.md body references files in `references/`, `scripts/`, or `assets/` subdirectories that do not exist. Use Glob to verify: `<skill-directory>/references/*`, `<skill-directory>/scripts/*`, `<skill-directory>/assets/*`.

### 2. Overly broad description (severity: info)
The description uses vague language like "use for anything", "general purpose", "all tasks" without specific trigger conditions.

### 3. Missing trigger conditions (severity: info)
The description does NOT contain patterns like "Use when", "Use for", "Trigger when", or specific scenario keywords. A good description names exact situations; a bad one is generic.

### 4. Internal skill references broken (severity: warning)
The SKILL.md body references other skills (e.g., "use /foo", "invoke skill-name", "REQUIRED SUB-SKILL: superpowers:bar") that do not exist in the index.

## Process

1. For EVERY skill in the index (not just suspects), check rules 2 and 3 based on the description in the index.
2. For skills flagged by rules 2 or 3, Read the full SKILL.md to confirm and check rules 1 and 4.
3. For rule 1, use Glob to check if referenced subdirectories and files exist.

## Budget

You may Read at most 20 SKILL.md files and run at most 20 Glob commands.

## Output Format

Return ONLY valid JSON:

```
{
  "type": "stale",
  "findings": [
    {
      "id": "S-1",
      "severity": "info",
      "skills": ["algorithmic-art (anthropic-agent-skills)"],
      "reason": "Description is 'generative/computational art' — no specific trigger conditions, no 'Use when' clause, extremely broad scope with rare actual use cases.",
      "recommendation": "Narrow description to specific triggers: 'Use when creating generative art with p5.js, Processing, or computational geometry algorithms.'",
      "details": {
        "missing_references": [],
        "conflict_points": []
      }
    }
  ]
}
```

If no stale skills found, return: {"type": "stale", "findings": []}
````
