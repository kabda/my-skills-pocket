# Analysis Subagent Prompt Templates

Two subagents for semantic analysis. Mechanical issues (same-name duplicates, missing references) are already handled by scan.py — do NOT re-flag those here.

---

## Duplicate & Conflict Detection Subagent

**Prompt template**:

`````
You are a skill duplicate and conflict detector. Analyze the following skill index.

## Skill Index
{INDEX_TABLE}

## Task 1: Semantic Duplicates

Flag pairs where two skills solve the same core task (>80% trigger overlap) but have different names.
- Do NOT flag same-name cross-suite pairs (already detected by scan.py).
- For each candidate pair, Read both SKILL.md files to confirm.
- Only flag if the core task is genuinely identical — shared keywords alone are not enough.

## Task 2: Conflicts

Flag pairs that both claim authority over the same task type AND give contradictory instructions:
- Different workflow steps or order
- Different output formats or file locations
- Opposite rules ("always do X" vs "never do X")

A conflict is NOT just overlap — it requires active contradiction.

For each candidate pair, Read both SKILL.md files and compare instructions line-by-line.

## Budget

Read at most 12 SKILL.md files total across both tasks.

## Output Format

Return ONLY valid JSON:

```json
{
  "type": "duplicate_conflict",
  "findings": [
    {
      "id": "D-1",
      "severity": "critical",
      "type": "duplicate",
      "skills": ["skill-a (suite-a)", "skill-b (suite-b)"],
      "reason": "...",
      "recommendation": "...",
      "details": {}
    },
    {
      "id": "C-1",
      "severity": "critical",
      "type": "conflict",
      "skills": ["skill-a (suite-a)", "skill-b (suite-b)"],
      "reason": "...",
      "recommendation": "...",
      "details": {"conflict_points": []}
    }
  ]
}
```

If nothing found: `{"type": "duplicate_conflict", "findings": []}`
`````

---

## Overlap Detection Subagent

**Prompt template**:

`````
You are a skill overlap detector. Analyze the following skill index for partially overlapping trigger conditions.

## Skill Index
{INDEX_TABLE}

## Detection Rules

1. Two skills overlap when their descriptions suggest they would BOTH trigger for some user requests, but each also has unique scenarios the other does not cover.
2. Overlap is distinct from duplicate: overlapping skills have different core purposes but share edge-case scenarios.
3. If overlapping scenarios exceed 50% of either skill's total trigger scenarios, severity = "critical"; otherwise "warning".

## Process

1. Identify pairs whose descriptions share trigger keywords or scenarios.
2. For each candidate pair, Read both SKILL.md files to understand full scope.
3. List specific overlapping scenarios and each skill's unique scenarios.

## Budget

Read at most 10 SKILL.md files total.

## Output Format

Return ONLY valid JSON:

```json
{
  "type": "overlap",
  "findings": [
    {
      "id": "O-1",
      "severity": "warning",
      "skills": ["skill-a (suite-a)", "skill-b (suite-b)"],
      "reason": "...",
      "recommendation": "...",
      "details": {
        "overlap_scenarios": [],
        "boundary_suggestion": ""
      }
    }
  ]
}
```

If nothing found: `{"type": "overlap", "findings": []}`
`````
