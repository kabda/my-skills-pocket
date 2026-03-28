#!/usr/bin/env python3
"""skill-governor scan script — 扫描已安装的 skills/commands/agents/hooks/mcps，输出 JSON。"""
import json, re
from pathlib import Path

# Note: project-level paths (.claude/settings.json, .claude/skills/, etc.)
# are resolved relative to cwd at runtime. Run from the project root for
# project-level settings to be discovered.

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CACHE_DIR = CLAUDE_DIR / "plugins" / "cache"
INSTALLED_PLUGINS_PATH = CLAUDE_DIR / "plugins" / "installed_plugins.json"


def load_settings(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_installed_plugins() -> list[dict]:
    """Read installed plugins from installed_plugins.json (authoritative source).

    Uses the exact installPath recorded at install time, so orphaned cache
    entries that were never registered are automatically excluded.

    Scope rules:
    - user:    always active
    - project: active only when cwd is within the recorded projectPath

    Falls back to get_enabled_plugins() if installed_plugins.json is missing.
    """
    try:
        data = json.loads(INSTALLED_PLUGINS_PATH.read_text())
        cwd = Path.cwd().resolve()
        seen, plugins = set(), []
        for key, entries in data.get("plugins", {}).items():
            if "@" not in key:
                continue
            plugin, suite = key.split("@", 1)
            for entry in entries:
                install_path = Path(entry.get("installPath", ""))
                if not install_path.exists():
                    continue  # installPath gone — orphaned entry, skip
                scope = entry.get("scope", "user")
                if scope == "project":
                    project_path = Path(entry.get("projectPath", "")).resolve()
                    try:
                        cwd.relative_to(project_path)
                    except ValueError:
                        continue  # not inside this project's directory
                if key not in seen:
                    seen.add(key)
                    plugins.append({
                        "plugin": plugin,
                        "suite": suite,
                        "install_path": install_path,
                        "source": str(INSTALLED_PLUGINS_PATH),
                    })
        return plugins
    except Exception:
        return get_enabled_plugins()


def get_enabled_plugins() -> list[dict]:
    """Fallback: read plugins from enabledPlugins in settings.json files."""
    sources = [CLAUDE_DIR / "settings.json", Path(".claude/settings.json"), Path(".claude/settings.local.json")]
    seen, plugins = set(), []
    for src in sources:
        for key, enabled in load_settings(src).get("enabledPlugins", {}).items():
            if enabled and key not in seen and "@" in key:
                seen.add(key)
                plugin, suite = key.split("@", 1)
                plugins.append({"plugin": plugin, "suite": suite, "source": str(src)})
    return plugins


def _parse_yaml_description(fm: str) -> str | None:
    """Parse YAML description supporting single-line and multiline (>, |) formats."""
    m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    if not m:
        return None
    first_line = m.group(1).strip().strip('"')
    if first_line in (">", "|", ">-", "|-"):
        lines = fm[m.end():].split("\n")
        continued = []
        for line in lines:
            if line and not line[0].isspace():
                break
            continued.append(line.strip())
        return " ".join(part for part in continued if part) or None
    return first_line or None


def extract_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return {"_skipped": True, "path": str(path), "reason": "无法读取文件"}
    if not text.startswith("---"):
        return {"_skipped": True, "path": str(path), "reason": "缺少 YAML frontmatter"}
    end = text.find("\n---", 3)
    if end == -1:
        return {"_skipped": True, "path": str(path), "reason": "YAML frontmatter 未闭合"}
    fm = text[3:end]
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    desc = _parse_yaml_description(fm)
    if not name_m or not desc:
        return {"_skipped": True, "path": str(path), "reason": "缺少 name 或 description 字段"}
    lines = text.splitlines()
    fm_end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
    body_preview = "\n".join(lines[fm_end + 1:fm_end + 51])
    return {
        "name": name_m.group(1).strip().strip('"'),
        "description": desc,
        "path": str(path),
        "body_preview": body_preview,
    }


def scan_skills_from_plugins(plugins: list[dict]) -> tuple[list[dict], list[dict]]:
    skills, skipped = [], []
    for p in plugins:
        cache_dir = p.get("install_path")
        if not cache_dir or not Path(cache_dir).exists():
            continue
        cache_dir = Path(cache_dir)
        for pattern in ["skills/**/SKILL.md", ".claude/skills/**/SKILL.md"]:
            for skill_path in cache_dir.glob(pattern):
                meta = extract_frontmatter(skill_path)
                if meta.get("_skipped"):
                    skipped.append(meta)
                else:
                    meta["suite"] = p["suite"]
                    meta["plugin"] = p["plugin"]
                    skills.append(meta)
    return skills, skipped


def scan_direct_skills() -> tuple[list[dict], list[dict]]:
    skills, skipped = [], []
    for base in [CLAUDE_DIR / "skills", Path(".claude/skills")]:
        if base.exists():
            # Use */SKILL.md (one level deep) to avoid matching nested SKILL.md
            # files inside subdirectories like .agents/skills/<name>/SKILL.md.
            for skill_path in base.glob("*/SKILL.md"):
                meta = extract_frontmatter(skill_path)
                if meta.get("_skipped"):
                    skipped.append(meta)
                else:
                    meta["suite"] = "direct"
                    meta["plugin"] = skill_path.parent.name
                    skills.append(meta)
    return skills, skipped


def scan_commands(plugins: list[dict]) -> list[dict]:
    commands = []
    for base in [CLAUDE_DIR / "commands", Path(".claude/commands")]:
        if base.exists():
            for f in base.glob("**/*.md"):
                commands.append({"name": f.stem, "path": str(f), "suite": "direct"})
    for p in plugins:
        cache_dir = p.get("install_path")
        if not cache_dir or not Path(cache_dir).exists():
            continue
        cache_dir = Path(cache_dir)
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
        cache_dir = p.get("install_path")
        if not cache_dir or not Path(cache_dir).exists():
            continue
        cache_dir = Path(cache_dir)
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


def _find_plugin_root(skill_path: Path) -> Path | None:
    """Walk up from a SKILL.md to find the plugin root (contains .claude-plugin/)."""
    current = skill_path.parent
    for _ in range(10):
        if (current / ".claude-plugin").exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return None


def detect_mechanical_issues(skills: list[dict]) -> list[dict]:
    findings = []
    seen_ids: set[str] = set()

    def _add(finding: dict) -> None:
        if finding["id"] not in seen_ids:
            seen_ids.add(finding["id"])
            findings.append(finding)

    # D 类：同名跨套件（critical）
    by_name: dict[str, list] = {}
    for s in skills:
        by_name.setdefault(s["name"], []).append(s)
    for name, group in by_name.items():
        suites = {s["suite"] for s in group}
        if len(suites) > 1:
            _add({
                "id": f"D-auto-{name}",
                "type": "duplicate",
                "severity": "critical",
                "skills": [f"{s['name']} ({s['suite']})" for s in group],
                "reason": f"同名 skill '{name}' 存在于多个套件：{', '.join(sorted(suites))}",
                "recommendation": "保留一个为主，其余重命名或移除。",
            })

    # S 类：缺失引用文件（warning）
    for s in skills:
        skill_dir = Path(s["path"]).parent
        plugin_root = _find_plugin_root(Path(s["path"]))
        for subdir in ["references", "scripts", "assets"]:
            for match in re.finditer(rf'{subdir}/([\w.-]+\.(?:md|py|js|sh|json))', s.get("body_preview", "")):
                ref_name = match.group(1)
                candidates = [skill_dir / subdir / ref_name]
                if plugin_root:
                    candidates.append(plugin_root / subdir / ref_name)
                if not any(c.exists() for c in candidates):
                    _add({
                        "id": f"S-auto-ref-{s['name']}-{ref_name}",
                        "type": "stale",
                        "severity": "warning",
                        "skills": [f"{s['name']} ({s['suite']})"],
                        "reason": f"SKILL.md 引用了不存在的文件：{subdir}/{ref_name}",
                        "recommendation": "创建缺失文件或移除引用。",
                    })

    # Q 类：描述质量问题（info）
    for s in skills:
        desc = s.get("description", "")
        name = s["name"]
        suite = s["suite"]
        if not re.search(r'[Uu]se when|用于当|当.*时使用', desc, re.IGNORECASE):
            _add({
                "id": f"Q-auto-trigger-{name}",
                "type": "stale",
                "severity": "info",
                "skills": [f"{name} ({suite})"],
                "reason": "description 中缺少触发条件（无 'Use when' 或等效模式）。",
                "recommendation": "添加 'Use when <条件>' 触发模式，便于系统自动匹配。",
            })
        if len(desc) < 20:
            _add({
                "id": f"Q-auto-short-{name}",
                "type": "stale",
                "severity": "info",
                "skills": [f"{name} ({suite})"],
                "reason": f"description 过短（{len(desc)} 字符），难以判断触发场景。",
                "recommendation": "扩展 description，包含具体使用场景和触发短语。",
            })

    return findings


if __name__ == "__main__":
    plugins = get_installed_plugins()
    plugin_skills, plugin_skipped = scan_skills_from_plugins(plugins)
    direct_skills, direct_skipped = scan_direct_skills()
    skills = plugin_skills + direct_skills
    skipped = plugin_skipped + direct_skipped
    commands = scan_commands(plugins)
    agents = scan_agents(plugins)
    hooks, mcps = scan_hooks_and_mcps()
    findings = detect_mechanical_issues(skills)
    # Serialize install_path (Path) as string for JSON output
    plugins_out = [{**p, "install_path": str(p["install_path"])} if "install_path" in p else p for p in plugins]
    print(json.dumps({
        "plugins": plugins_out,
        "skills": skills,
        "commands": commands,
        "agents": agents,
        "hooks": hooks,
        "mcps": mcps,
        "findings": findings,
        "skipped": [{"path": s["path"], "reason": s["reason"]} for s in skipped],
    }, ensure_ascii=False, indent=2))
