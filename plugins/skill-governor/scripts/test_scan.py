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
