"""
Tests for ai_manager.py

Procedural testing for the AI response parsing and validation logic.
Works two ways:
    python test_ai_manager.py     -> built-in mini runner
    pytest test_ai_manager.py     -> pytest picks up the test_* functions

NOTE: These tests intentionally bypass the live Gemini API to ensure fast, 
deterministic, and free execution in CI/CD pipelines.
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import ai_manager as am


# ------------------ #
# _parse_reply Tests
# ------------------ #

def test_parse_valid_json():
    """Test that a perfectly formatted AI string is converted to a dictionary."""
    valid_ai_text = '{"reply": "Hello", "is_complete": false, "report": {"location": "Sector A"}}'
    result = am._parse_reply(valid_ai_text)
    assert result is not None
    assert result["reply"] == "Hello"
    assert result["report"]["location"] == "Sector A"

def test_parse_invalid_json_format():
    """Test that raw text or broken JSON is safely caught and returns None."""
    broken_json = 'Here is your report: {"reply": "Hello"'
    assert am._parse_reply(broken_json) is None

def test_parse_missing_required_keys():
    """Test that valid JSON missing our strict structural keys (reply, is_complete, report) is rejected."""
    # Missing 'is_complete'
    missing_keys = '{"reply": "Hello", "report": {}}'
    assert am._parse_reply(missing_keys) is None

def test_parse_report_is_not_dict():
    """Test that if the AI returns a string for the report instead of a dictionary, it is rejected."""
    bad_structure = '{"reply": "Hello", "is_complete": false, "report": "Sector A"}'
    assert am._parse_reply(bad_structure) is None


# ----------------------- #
# find_missing_fields Tests
# ----------------------- #

def test_find_missing_fields_all_present():
    """Test that a fully populated report returns an empty missing list."""
    # Create a dummy report with all fields filled
    report = {field: "Filled" for field in list(am.USER_FIELDS) + list(am.AI_FIELDS)}
    missing = am.find_missing_fields(report)
    assert len(missing) == 0

def test_find_missing_fields_identifies_blanks():
    """Test that nulls, empty strings, and missing keys are all flagged as missing."""
    report = {
        "reporter_name": "Alice",
        "location": "",           # Empty string
        "incident_date": None     # Explicit Null
        # "incident_time" is missing entirely
    }
    missing = am.find_missing_fields(report)
    assert "location" in missing
    assert "incident_date" in missing
    assert "incident_time" in missing
    assert "reporter_name" not in missing


# ----------------------- #
# _build_fix_message Tests
# ----------------------- #

def test_build_fix_message_for_user_details():
    """Test that the internal prompt directs the AI to ask the user for missing details."""
    missing = ["reporter_name", "location"]
    message = am._build_fix_message(missing)
    assert "ask the worker for:" in message
    assert "reporter_name" in message
    assert "location" in message

def test_build_fix_message_for_ai_analysis():
    """Test that the internal prompt directs the AI to fill in its own missing analysis."""
    missing = ["ai_severity", "root_cause_category"]
    message = am._build_fix_message(missing)
    assert "Fill these in yourself" in message
    assert "ai_severity" in message


# ------------------ #
# Mini runner
# ------------------ #
def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except AssertionError as e:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n      {e}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
            
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures

if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)