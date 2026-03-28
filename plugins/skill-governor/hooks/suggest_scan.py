#!/usr/bin/env python3
"""Suggest running /skill-governor after new plugin or skill installs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CACHE_DIR = CLAUDE_DIR / "plugins" / "cache"
STATE_DIR = CLAUDE_DIR / "skill-governor"
STATE_PATH = STATE_DIR / "install-state.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def get_settings_paths(project_dir: Path | None) -> list[Path]:
    paths = [CLAUDE_DIR / "settings.json"]
    if project_dir:
        paths.append(project_dir / ".claude" / "settings.json")
        paths.append(project_dir / ".claude" / "settings.local.json")
    return paths


def get_enabled_plugins(settings_paths: list[Path]) -> list[dict]:
    seen: set[str] = set()
    plugins: list[dict] = []
    for src in settings_paths:
        settings = load_json(src)
        for key, enabled in settings.get("enabledPlugins", {}).items():
            if not enabled or key in seen or "@" not in key:
                continue
            seen.add(key)
            plugin, suite = key.split("@", 1)
            plugins.append({"id": key, "plugin": plugin, "suite": suite})
    return sorted(plugins, key=lambda item: item["id"])


def resolve_plugin_cache(plugin: str, suite: str) -> Path | None:
    base = CACHE_DIR / suite / plugin
    if not base.exists():
        return None

    versions = [entry for entry in base.iterdir() if entry.is_dir()]
    if not versions:
        return None

    def sort_key(path: Path) -> tuple[int, tuple]:
        try:
            return (1, tuple(int(part) for part in path.name.split(".")))
        except ValueError:
            return (0, (path.stat().st_mtime,))

    return sorted(versions, key=sort_key)[-1]


def discover_plugin_skills(plugins: list[dict]) -> list[str]:
    skills: set[str] = set()
    for item in plugins:
        cache_dir = resolve_plugin_cache(item["plugin"], item["suite"])
        if not cache_dir:
            continue
        for pattern in ("skills/**/SKILL.md", ".claude/skills/**/SKILL.md"):
            for skill_path in cache_dir.glob(pattern):
                skill_name = skill_path.parent.name
                skills.add(f"{item['id']}::{skill_name}")
    return sorted(skills)


def discover_direct_skills(project_dir: Path | None) -> list[str]:
    skills: set[str] = set()
    bases = [CLAUDE_DIR / "skills"]
    if project_dir:
        bases.append(project_dir / ".claude" / "skills")

    for base in bases:
        if not base.exists():
            continue
        for skill_path in base.glob("**/SKILL.md"):
            source = "user" if base == CLAUDE_DIR / "skills" else "project"
            skills.add(f"{source}::{skill_path.parent.name}")
    return sorted(skills)


def build_snapshot(project_dir: Path | None) -> dict:
    settings_paths = get_settings_paths(project_dir)
    plugins = get_enabled_plugins(settings_paths)
    direct_skills = discover_direct_skills(project_dir)
    plugin_skills = discover_plugin_skills(plugins)
    return {
        "plugins": [item["id"] for item in plugins],
        "skills": sorted(set(direct_skills + plugin_skills)),
    }


def diff_snapshots(previous: dict, current: dict) -> dict[str, list[str]]:
    prev_plugins = set(previous.get("plugins", []))
    prev_skills = set(previous.get("skills", []))
    current_plugins = set(current.get("plugins", []))
    current_skills = set(current.get("skills", []))
    return {
        "plugins": sorted(current_plugins - prev_plugins),
        "skills": sorted(current_skills - prev_skills),
    }


def summarize_items(items: list[str], limit: int = 8) -> str:
    if len(items) <= limit:
        return ", ".join(items)
    remaining = len(items) - limit
    return f"{', '.join(items[:limit])}, and {remaining} more"


def build_additional_context(diff: dict[str, list[str]]) -> str:
    lines = [
        "skill-governor detected newly installed plugins or skills since the previous session.",
    ]
    if diff["plugins"]:
        lines.append(f"New plugins: {summarize_items(diff['plugins'])}.")
    if diff["skills"]:
        lines.append(f"New skills: {summarize_items(diff['skills'])}.")
    lines.append("Ask the user whether they want to run `/skill-governor` now.")
    lines.append("Do not run the scan automatically unless the user explicitly agrees.")
    return "\n".join(lines)


def save_snapshot(snapshot: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))


def main() -> int:
    payload = load_hook_input()
    cwd = payload.get("cwd")
    project_dir = Path(cwd) if cwd else None

    previous = load_json(STATE_PATH)
    current = build_snapshot(project_dir)

    diff = diff_snapshots(previous, current)
    if not previous or (not diff["plugins"] and not diff["skills"]):
        save_snapshot(current)
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": build_additional_context(diff),
                }
            },
            ensure_ascii=False,
        )
    )
    save_snapshot(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
