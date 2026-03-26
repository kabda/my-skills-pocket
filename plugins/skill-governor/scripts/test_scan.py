import subprocess, json, sys, os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

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
    for key in ("skills", "commands", "agents", "hooks", "mcps", "findings"):
        assert key in data, f"missing key: {key}"

def test_findings_have_required_fields():
    data = json.loads(_SCAN_RESULT.stdout)
    for f in data["findings"]:
        for field in ("id", "type", "severity", "skills", "reason", "recommendation"):
            assert field in f, f"finding missing field: {field}"

sys.path.insert(0, SCRIPTS_DIR)
from scan import detect_mechanical_issues

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

if __name__ == "__main__":
    test_outputs_valid_json()
    test_findings_have_required_fields()
    test_detects_same_name_cross_suite_duplicate()
    print("ALL PASS")
