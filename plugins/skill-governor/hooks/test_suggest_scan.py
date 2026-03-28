from suggest_scan import build_additional_context, diff_snapshots, summarize_items


def test_diff_snapshots_only_reports_new_items():
    previous = {
        "plugins": ["alpha@suite", "beta@suite"],
        "skills": ["alpha@suite::planner", "user::notes"],
    }
    current = {
        "plugins": ["alpha@suite", "beta@suite", "gamma@suite"],
        "skills": ["alpha@suite::planner", "user::notes", "gamma@suite::audit", "project::lint"],
    }

    diff = diff_snapshots(previous, current)

    assert diff["plugins"] == ["gamma@suite"]
    assert diff["skills"] == ["gamma@suite::audit", "project::lint"]


def test_diff_snapshots_empty_previous():
    diff = diff_snapshots({}, {"plugins": ["a@b"], "skills": ["a@b::s"]})
    assert diff["plugins"] == ["a@b"]
    assert diff["skills"] == ["a@b::s"]


def test_diff_snapshots_no_changes():
    snap = {"plugins": ["a@b"], "skills": ["a@b::s"]}
    diff = diff_snapshots(snap, snap)
    assert diff["plugins"] == []
    assert diff["skills"] == []


def test_build_additional_context_includes_explicit_user_choice():
    context = build_additional_context(
        {
            "plugins": ["gamma@suite"],
            "skills": ["project::lint"],
        }
    )

    assert "gamma@suite" in context
    assert "project::lint" in context
    assert "Ask the user whether they want to run `/skill-governor` now." in context
    assert "Do not run the scan automatically" in context


def test_summarize_items_within_limit():
    assert summarize_items(["a", "b", "c"], limit=5) == "a, b, c"


def test_summarize_items_exceeds_limit():
    result = summarize_items(["a", "b", "c", "d", "e"], limit=3)
    assert "a, b, c" in result
    assert "2 more" in result
