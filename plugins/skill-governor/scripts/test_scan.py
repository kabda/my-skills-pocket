import subprocess, json, sys, os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from scan import detect_mechanical_issues, extract_frontmatter, _parse_yaml_description, _find_plugin_root


# --- Integration tests (run against real environment) ---

def _run_scan():
    result = subprocess.run(
        [sys.executable, "scan.py"],
        capture_output=True, text=True, cwd=SCRIPTS_DIR
    )
    return result

_SCAN_RESULT = _run_scan()


def test_outputs_valid_json():
    assert _SCAN_RESULT.returncode == 0, f"scan.py failed: {_SCAN_RESULT.stderr}"
    data = json.loads(_SCAN_RESULT.stdout)
    for key in ("skills", "commands", "agents", "hooks", "mcps", "findings", "skipped"):
        assert key in data, f"missing key: {key}"


def test_findings_have_required_fields():
    data = json.loads(_SCAN_RESULT.stdout)
    for f in data["findings"]:
        for field in ("id", "type", "severity", "skills", "reason", "recommendation"):
            assert field in f, f"finding missing field: {field}"


def test_skipped_have_required_fields():
    data = json.loads(_SCAN_RESULT.stdout)
    for s in data["skipped"]:
        assert "path" in s and "reason" in s, f"skipped entry missing fields: {s}"


def test_no_duplicate_finding_ids():
    data = json.loads(_SCAN_RESULT.stdout)
    ids = [f["id"] for f in data["findings"]]
    assert len(ids) == len(set(ids)), f"duplicate finding IDs: {[x for x in ids if ids.count(x) > 1]}"


# --- Unit tests for detect_mechanical_issues ---

def test_detects_same_name_cross_suite_duplicate():
    skills = [
        {"name": "foo", "suite": "suite-a", "plugin": "p1", "path": "/a/SKILL.md", "description": "Use when X", "body_preview": ""},
        {"name": "foo", "suite": "suite-b", "plugin": "p2", "path": "/b/SKILL.md", "description": "Use when Y", "body_preview": ""},
    ]
    findings = detect_mechanical_issues(skills)
    dup = [f for f in findings if f["type"] == "duplicate"]
    assert len(dup) == 1, f"expected 1 duplicate finding, got {len(dup)}"
    assert dup[0]["severity"] == "critical"
    assert "foo" in dup[0]["id"]


def test_regex_does_not_match_through_markdown_links():
    r"""Regression: \\S+ used to match through markdown link syntax like [file.md](references/file.md)."""
    skills = [{
        "name": "test-skill", "suite": "test", "plugin": "p",
        "path": "/nonexistent/SKILL.md",
        "description": "Use when testing",
        "body_preview": "See [quality-criteria.md](references/quality-criteria.md) for details",
    }]
    findings = detect_mechanical_issues(skills)
    stale = [f for f in findings if f["type"] == "stale" and "ref" in f["id"]]
    for f in stale:
        assert "](references/" not in f["id"], f"regex matched through markdown link: {f['id']}"
        assert "](references/" not in f["reason"], f"regex matched through markdown link: {f['reason']}"


def test_dedup_same_reference_mentioned_twice():
    """Body mentioning scripts/scan.py twice should produce only one finding."""
    skills = [{
        "name": "test-skill", "suite": "test", "plugin": "p",
        "path": "/nonexistent/SKILL.md",
        "description": "Use when testing",
        "body_preview": "Run scripts/scan.py first.\nAlternatively: scripts/scan.py",
    }]
    findings = detect_mechanical_issues(skills)
    ref_findings = [f for f in findings if f["id"] == "S-auto-ref-test-skill-scan.py"]
    assert len(ref_findings) <= 1, f"expected at most 1 finding, got {len(ref_findings)}"


def test_missing_trigger_condition_detected():
    skills = [{
        "name": "no-trigger", "suite": "test", "plugin": "p",
        "path": "/test/SKILL.md",
        "description": "A helpful skill for doing things",
        "body_preview": "",
    }]
    findings = detect_mechanical_issues(skills)
    trigger = [f for f in findings if "trigger" in f["id"]]
    assert len(trigger) == 1
    assert trigger[0]["severity"] == "info"


def test_short_description_detected():
    skills = [{
        "name": "brevity", "suite": "test", "plugin": "p",
        "path": "/test/SKILL.md",
        "description": "Brief",
        "body_preview": "",
    }]
    findings = detect_mechanical_issues(skills)
    short_findings = [f for f in findings if f["id"] == "Q-auto-short-brevity"]
    assert len(short_findings) == 1


def test_good_description_no_quality_finding():
    skills = [{
        "name": "good-skill", "suite": "test", "plugin": "p",
        "path": "/test/SKILL.md",
        "description": "Use when auditing skills for quality issues and checking duplicates",
        "body_preview": "",
    }]
    findings = detect_mechanical_issues(skills)
    quality = [f for f in findings if f["id"].startswith("Q-")]
    assert len(quality) == 0


# --- Unit tests for _parse_yaml_description ---

def test_parse_single_line_description():
    fm = '\nname: foo\ndescription: Use when doing X\n'
    assert _parse_yaml_description(fm) == "Use when doing X"


def test_parse_quoted_description():
    fm = '\nname: foo\ndescription: "Use when doing X"\n'
    assert _parse_yaml_description(fm) == "Use when doing X"


def test_parse_multiline_folded_description():
    fm = '\nname: foo\ndescription: >\n  Use when doing X\n  or Y or Z\n'
    result = _parse_yaml_description(fm)
    assert "Use when doing X" in result
    assert "Y or Z" in result


def test_parse_multiline_literal_description():
    fm = '\nname: foo\ndescription: |\n  Use when doing X\n  or Y or Z\n'
    result = _parse_yaml_description(fm)
    assert "Use when doing X" in result


# --- Unit tests for extract_frontmatter ---

def test_extract_frontmatter_returns_skipped_for_no_frontmatter(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("# No frontmatter here")
    result = extract_frontmatter(f)
    assert result["_skipped"] is True
    assert "frontmatter" in result["reason"]


def test_extract_frontmatter_returns_skipped_for_missing_fields(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: foo\n---\nBody here")
    result = extract_frontmatter(f)
    assert result["_skipped"] is True


def test_extract_frontmatter_valid(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: foo\ndescription: Use when testing\n---\nBody line 1\nBody line 2")
    result = extract_frontmatter(f)
    assert result["name"] == "foo"
    assert result["description"] == "Use when testing"
    assert "Body line 1" in result["body_preview"]
    assert "_skipped" not in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
