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
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    desc_m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    if not name_m or not desc_m:
        return None
    lines = text.splitlines()
    fm_end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
    body_preview = "\n".join(lines[fm_end + 1:fm_end + 51])
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
                "skills": [f"{s['name']} ({s['suite']})" for s in group],
                "reason": f"同名 skill '{name}' 存在于多个套件：{', '.join(suites)}",
                "recommendation": "保留一个为主，其余重命名或移除。",
            })
    # S 类：缺失引用文件（warning）
    for s in skills:
        skill_dir = Path(s["path"]).parent
        for subdir in ["references", "scripts", "assets"]:
            for match in re.finditer(rf'{subdir}/(\S+\.(?:md|py|js|sh|json))', s.get("body_preview", "")):
                ref_file = skill_dir / subdir / match.group(1)
                if not ref_file.exists():
                    findings.append({
                        "id": f"S-auto-ref-{s['name']}-{match.group(1)}",
                        "type": "stale",
                        "severity": "warning",
                        "skills": [f"{s['name']} ({s['suite']})"],
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
