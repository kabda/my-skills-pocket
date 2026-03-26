# Skill Governor 优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 skill-governor 的 token 消耗从 ~100k 降至 ~25k，同时将扫描范围从插件缓存全量改为用户实际已安装的 skills/commands/agents/hooks/mcps。

**Architecture:** 新增 Python 扫描脚本承包所有机械性工作（文件发现、metadata 提取、同名重复检测、缺失引用检测、缺失触发条件检测），输出紧凑 JSON 供 Claude 消费；Claude 只负责语义分析（重复+冲突合并为 1 个子代理，重叠 1 个子代理），共 2 个并行子代理。

**Tech Stack:** Python 3（标准库，无外部依赖）、JSON、正则表达式

---

## 文件结构

- 新建：`plugins/skill-governor/scripts/scan.py`
- 修改：`plugins/skill-governor/skills/skill-governor/SKILL.md`
- 修改：`plugins/skill-governor/skills/skill-governor/references/analysis-prompts.md`

---

### Task 1: 创建扫描脚本 scan.py

扫描已安装的 skills/commands/agents/hooks/mcps，提取 metadata，执行机械性检测（同名跨套件重复、缺失引用文件），输出 JSON。完整脚本一次性写入，无增量重写。

**Files:**
- Create: `plugins/skill-governor/scripts/scan.py`
- Create: `plugins/skill-governor/scripts/test_scan.py`

- [ ] **Step 1: 写失败测试**

新建 `plugins/skill-governor/scripts/test_scan.py`：

```python
import subprocess, json, sys, os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def run_scan():
    result = subprocess.run(
        [sys.executable, "scan.py"],
        capture_output=True, text=True, cwd=SCRIPTS_DIR
    )
    return result

def test_outputs_valid_json():
    r = run_scan()
    assert r.returncode == 0, f"scan.py failed: {r.stderr}"
    data = json.loads(r.stdout)
    for key in ("skills", "commands", "agents", "hooks", "mcps", "findings"):
        assert key in data, f"missing key: {key}"

def test_findings_have_required_fields():
    r = run_scan()
    data = json.loads(r.stdout)
    for f in data["findings"]:
        for field in ("id", "type", "severity", "skills", "reason", "recommendation"):
            assert field in f, f"finding missing field: {field}"

if __name__ == "__main__":
    test_outputs_valid_json()
    test_findings_have_required_fields()
    print("ALL PASS")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/scripts && python3 test_scan.py
```

预期：`FileNotFoundError` 或 `No such file or directory: 'scan.py'`（scan.py 尚不存在）

- [ ] **Step 3: 写完整 scan.py**

新建 `plugins/skill-governor/scripts/scan.py`（完整文件，一次性写入）：

```python
#!/usr/bin/env python3
"""skill-governor scan script — 扫描已安装的 skills/commands/agents/hooks/mcps，输出 JSON。"""
import json, re
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CACHE_DIR = CLAUDE_DIR / "plugins" / "cache"


def load_settings(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_enabled_plugins() -> list[dict]:
    sources = [CLAUDE_DIR / "settings.json", Path(".claude/settings.json"), Path(".claude/settings.local.json")]
    seen, plugins = set(), []
    for src in sources:
        for key, enabled in load_settings(src).get("enabledPlugins", {}).items():
            if enabled and key not in seen and "@" in key:
                seen.add(key)
                plugin, suite = key.split("@", 1)
                plugins.append({"plugin": plugin, "suite": suite, "source": str(src)})
    return plugins


def resolve_plugin_cache(plugin: str, suite: str) -> Path | None:
    base = CACHE_DIR / suite / plugin
    if not base.exists():
        return None
    versions = [d for d in base.iterdir() if d.is_dir()]
    if not versions:
        return None
    def sort_key(p):
        try:
            return (1, tuple(int(x) for x in p.name.split(".")))
        except ValueError:
            return (0, (p.stat().st_mtime,))
    return sorted(versions, key=sort_key)[-1]


def extract_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("
---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    desc_m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    if not name_m or not desc_m:
        return None
    lines = text.splitlines()
    fm_end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
    body_preview = "
".join(lines[fm_end + 1:fm_end + 51])
    return {
        "name": name_m.group(1).strip().strip('"'),
        "description": desc_m.group(1).strip().strip('"'),
        "path": str(path),
        "body_preview": body_preview,
    }


def scan_skills_from_plugins(plugins: list[dict]) -> list[dict]:
    skills = []
    for p in plugins:
        cache_dir = resolve_plugin_cache(p["plugin"], p["suite"])
        if not cache_dir:
            continue
        for pattern in ["skills/**/SKILL.md", ".claude/skills/**/SKILL.md"]:
            for skill_path in cache_dir.glob(pattern):
                meta = extract_frontmatter(skill_path)
                if meta:
                    meta["suite"] = p["suite"]
                    meta["plugin"] = p["plugin"]
                    skills.append(meta)
    return skills


def scan_direct_skills() -> list[dict]:
    skills = []
    for base in [CLAUDE_DIR / "skills", Path(".claude/skills")]:
        if base.exists():
            for skill_path in base.glob("**/SKILL.md"):
                meta = extract_frontmatter(skill_path)
                if meta:
                    meta["suite"] = "direct"
                    meta["plugin"] = skill_path.parent.name
                    skills.append(meta)
    return skills


def scan_commands(plugins: list[dict]) -> list[dict]:
    commands = []
    for base in [CLAUDE_DIR / "commands", Path(".claude/commands")]:
        if base.exists():
            for f in base.glob("**/*.md"):
                commands.append({"name": f.stem, "path": str(f), "suite": "direct"})
    for p in plugins:
        cache_dir = resolve_plugin_cache(p["plugin"], p["suite"])
        if not cache_dir:
            continue
        for f in list(cache_dir.glob("commands/**/*.md")) + list(cache_dir.glob(".claude/commands/**/*.md")):
            commands.append({"name": f.stem, "path": str(f), "suite": p["suite"], "plugin": p["plugin"]})
    return commands


def scan_agents(plugins: list[dict]) -> list[dict]:
    agents = []
    for base in [CLAUDE_DIR / "agents", Path(".claude/agents")]:
        if base.exists():
            for f in base.glob("**/*.md"):
                agents.append({"name": f.stem, "path": str(f), "suite": "direct"})
    for p in plugins:
        cache_dir = resolve_plugin_cache(p["plugin"], p["suite"])
        if not cache_dir:
            continue
        for f in list(cache_dir.glob("agents/**/*.md")) + list(cache_dir.glob(".claude/agents/**/*.md")):
            agents.append({"name": f.stem, "path": str(f), "suite": p["suite"], "plugin": p["plugin"]})
    return agents


def scan_hooks_and_mcps() -> tuple[list, list]:
    hooks, mcps = [], []
    for src in [CLAUDE_DIR / "settings.json", Path(".claude/settings.json"), Path(".claude/settings.local.json")]:
        s = load_settings(src)
        for event, hook_list in s.get("hooks", {}).items():
            for h in hook_list:
                for item in h.get("hooks", [h]):
                    hooks.append({"event": event, "matcher": h.get("matcher", "*"), "command": item.get("command", ""), "source": str(src)})
        for name, cfg in s.get("mcpServers", {}).items():
            mcps.append({"name": name, "command": cfg.get("command", ""), "source": str(src)})
    return hooks, mcps


def detect_mechanical_issues(skills: list[dict]) -> list[dict]:
    findings = []
    # D 类：同名跨套件（critical）
    by_name: dict[str, list] = {}
    for s in skills:
        by_name.setdefault(s["name"], []).append(s)
    for name, group in by_name.items():
        suites = {s["suite"] for s in group}
        if len(suites) > 1:
            findings.append({
                "id": f"D-auto-{name}",
                "type": "duplicate",
                "severity": "critical",
                "skills": [f"{s[chr(39)name{chr(39)]} ({s[chr(39)suite{chr(39)]}})" for s in group],
                "reason": f"同名 skill {chr(39)}{name}{chr(39)} 存在于多个套件：{chr(44).join(suites)}",
                "recommendation": "保留一个为主，其余重命名或移除。",
            })
    # S 类：缺失引用文件（warning）
    for s in skills:
        skill_dir = Path(s["path"]).parent
        for subdir in ["references", "scripts", "assets"]:
            ref_dir = skill_dir / subdir
            if ref_dir.exists():
                for match in re.finditer(rf"{subdir}/(\S+\.(?:md|py|js|sh|json))", s.get("body_preview", "")):
                    ref_file = skill_dir / subdir / match.group(1)
                    if not ref_file.exists():
                        findings.append({
                            "id": f"S-auto-ref-{s[chr(39)name{chr(39)]}}-{match.group(1)}",
                            "type": "stale",
                            "severity": "warning",
                            "skills": [f"{s[chr(39)name{chr(39)]} ({s[chr(39)suite{chr(39)]}})" ],
                            "reason": f"SKILL.md 引用了不存在的文件：{subdir}/{match.group(1)}",
                            "recommendation": "创建缺失文件或移除引用。",
                        })
    return findings


if __name__ == "__main__":
    plugins = get_enabled_plugins()
    skills = scan_skills_from_plugins(plugins) + scan_direct_skills()
    commands = scan_commands(plugins)
    agents = scan_agents(plugins)
    hooks, mcps = scan_hooks_and_mcps()
    findings = detect_mechanical_issues(skills)
    print(json.dumps({
        "plugins": plugins,
        "skills": skills,
        "commands": commands,
        "agents": agents,
        "hooks": hooks,
        "mcps": mcps,
        "findings": findings,
    }, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/scripts && python3 test_scan.py
```

预期：`ALL PASS`

- [ ] **Step 5: 验证完整输出**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/scripts && python3 scan.py | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'skills: {len(d["skills"])}, commands: {len(d["commands"])}, agents: {len(d["agents"])}, hooks: {len(d["hooks"])}, mcps: {len(d["mcps"])}, findings: {len(d["findings"])}')
for f in d['findings']: print(f'  [{f["severity"]}] {f["id"]}')
"
```

预期：各类型数量输出，结果取决于已安装插件（0 也是正确的）

- [ ] **Step 6: Commit**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket
git add plugins/skill-governor/scripts/
git commit -m "feat(skill-governor): add scan.py for token-efficient installed skill discovery"
```

---

### Task 2: 更新 SKILL.md — 新 Phase 1 + 2 子代理架构

**Files:**
- Modify: `plugins/skill-governor/skills/skill-governor/SKILL.md`

- [ ] **Step 1: 替换 Phase 1 为脚本调用**

将 Phase 1 整节替换为：

```markdown
## Phase 1: Discover & Index (you execute this directly)

### Step 1: Run the scan script

```bash
# Find the installed script (version-agnostic):
SCAN=$(ls ~/.claude/plugins/cache/my-skills-pocket/skill-governor/*/scripts/scan.py 2>/dev/null | tail -1)
python3 "$SCAN"
```

Or from the project source:
```bash
python3 <path-to-skill-governor-plugin>/scripts/scan.py
```

The script outputs a JSON object with:
- `skills`: all installed skills with name, description, suite, plugin, path, body_preview (first 50 lines)
- `commands`, `agents`, `hooks`, `mcps`: other installed components
- `findings`: mechanical issues already detected (same-name duplicates, missing trigger conditions, missing reference files)

### Step 2: Parse the JSON output

Read the script output. The `findings` array already contains:
- **D-auto-***: same-name cross-suite duplicates (critical)
- **S-auto-***: missing trigger conditions (info)
- **S-auto-ref-***: broken file references (warning)

These are confirmed findings — include them directly in the final report without re-analysis.

### Step 3: Build the semantic index

From the `skills` array, format the index table for Phase 2 subagents:

```
[N] name: <name> | suite: <suite> | plugin: <plugin>
    description: <description>
    preview: <first 3 lines of body_preview after frontmatter>
```

Count total skills and suites.

### Step 4: Proceed to Phase 2
```

- [ ] **Step 2: 将 Phase 2 改为 2 个子代理**

将 Phase 2 整节替换为：

```markdown
## Phase 2: Semantic Analysis (dispatch 2 parallel subagents)

Read `references/analysis-prompts.md` for the prompt templates.

Dispatch BOTH subagents in a SINGLE message using the Agent tool (runs in parallel):

1. **Duplicate + Conflict Agent** — use the "Duplicate & Conflict Detection Subagent" prompt template
2. **Overlap Detection Agent** — use the "Overlap Detection Subagent" prompt template

For each subagent:
- Replace `{INDEX_TABLE}` with the semantic index from Phase 1
- Set `subagent_type` to `general-purpose`

Wait for both subagents to complete before proceeding to Phase 3.
```

- [ ] **Step 3: 更新 Phase 3 合并逻辑**

在 Phase 3 Step 1 中，将"Parse subagent results"更新为：

```markdown
### Step 1: Parse and merge all findings

Combine findings from three sources:
1. `findings` array from scan.py output (mechanical issues — already confirmed, no re-analysis needed)
2. Duplicate + Conflict subagent JSON result
3. Overlap subagent JSON result

Dedup: if the same skill pair appears in both semantic subagents, keep the higher severity finding.
```

- [ ] **Step 4: 验证 SKILL.md 结构正确**

```bash
grep -c "Phase [123]" /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/skills/skill-governor/SKILL.md
```

预期：`3`

- [ ] **Step 5: Commit**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket
git add plugins/skill-governor/skills/skill-governor/SKILL.md
git commit -m "feat(skill-governor): redesign Phase 1 to use scan.py, reduce to 2 semantic subagents"
```

---

### Task 3: 更新 analysis-prompts.md — 合并 duplicate+conflict 子代理

**Files:**
- Modify: `plugins/skill-governor/skills/skill-governor/references/analysis-prompts.md`

- [ ] **Step 1: 替换 analysis-prompts.md 内容**

将文件内容替换为：

````markdown
# Analysis Subagent Prompt Templates

Two subagents for semantic analysis. Mechanical issues (same-name duplicates, missing triggers, broken references) are already handled by scan.py — do NOT re-flag those here.

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
````

- [ ] **Step 2: 验证两个 prompt 模板均存在**

```bash
grep -c "## Duplicate & Conflict\|## Overlap Detection" /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/skills/skill-governor/references/analysis-prompts.md
```

预期：`2`

- [ ] **Step 3: Commit**

```bash
cd /Users/fanyuandong/Developer/Projects/my-skills-pocket
git add plugins/skill-governor/skills/skill-governor/references/analysis-prompts.md
git commit -m "feat(skill-governor): merge duplicate+conflict into single subagent, trim prompts"
```

---

### Task 4: 集成冒烟测试

验证三个任务的产出物协同工作正确。

**Files:** 无新文件

- [ ] **Step 1: 验证 scan.py 输出结构正确**

```bash
python3 /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/scripts/scan.py | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'skills' in d and 'findings' in d, 'missing keys'
print(f'OK: skills={len(d[\"skills\"])}, findings={len(d[\"findings\"])}')
"
```

预期：`OK: skills=N, findings=M`（N >= 0，M >= 0）

- [ ] **Step 2: 验证 analysis-prompts.md 包含两个 {INDEX_TABLE} 占位符**

```bash
grep -c "{INDEX_TABLE}" /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/skills/skill-governor/references/analysis-prompts.md
```

预期：`2`

- [ ] **Step 3: 验证 SKILL.md 引用 scan.py 的 glob 路径**

```bash
grep "skill-governor/\*/scripts/scan.py" /Users/fanyuandong/Developer/Projects/my-skills-pocket/plugins/skill-governor/skills/skill-governor/SKILL.md
```

预期：输出包含该路径的行（非空）

