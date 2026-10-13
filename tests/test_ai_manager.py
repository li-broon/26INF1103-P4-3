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


# ------------------------------------------- #
# Separate Analysis Request Tests (Fake Gemini)
# ------------------------------------------- #

import json
import types as pytypes
from unittest import mock

# Worker Details All Filled In (What the Chat Collects)
FILLED_USER_DETAILS = {
    "reporter_name": "Muthu", "location": "Tuas site, loading bay", "incident_date": "2026-10-13",
    "incident_time": "10:00", "description": "Slipped on oil", "injury_status": "Bruised knee",
    "hospitalised": False, "immediate_action_taken": "Cleared the area", "work_stoppage_hours": 1,
}

# A Valid Analysis (What the Separate Request Should Return)
GOOD_ANALYSIS = {
    "detected_language": "English", "ai_severity": "Low", "is_near_miss": False,
    "root_cause_category": "Slip or Trip", "lost_time_injury": False,
    "safety_recommendation": "Clean oil spills straight away.",
}

# Chat Reply that Says "complete" but Leaves the Analysis Empty (the Bug Seen in Testing)
def _complete_reply_without_analysis():
    report = dict(FILLED_USER_DETAILS, **{name: None for name in am.AI_FIELDS})
    return json.dumps({"reply": "Thank you, your report is complete.", "is_complete": True, "report": report})

# Fake Chat that Always Gives the Same Reply and Remembers What the Worker Typed
def _fake_chat(reply_text):
    sent = []
    def send_message(message):
        sent.append(message)
        return pytypes.SimpleNamespace(text=reply_text)
    def get_history():
        return [pytypes.SimpleNamespace(role="user", parts=[pytypes.SimpleNamespace(text=m)]) for m in sent]
    return pytypes.SimpleNamespace(send_message=send_message, get_history=get_history)

# Fake Gemini Client whose Separate Analysis Request Returns the Given Texts in Order
def _fake_client(*analysis_texts):
    texts = iter(analysis_texts)
    calls = []
    def generate_content(model, contents, config):
        calls.append(contents)
        return pytypes.SimpleNamespace(text=next(texts))
    return pytypes.SimpleNamespace(models=pytypes.SimpleNamespace(generate_content=generate_content)), calls

def test_empty_analysis_is_filled_by_separate_request():
    client, calls = _fake_client(json.dumps(GOOD_ANALYSIS))
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(_complete_reply_without_analysis()), "cleared the area, stopped 1 hour")
    assert "error" not in result
    assert result["is_complete"] is True
    assert result["report"]["ai_severity"] == "Low"
    assert am.find_missing_fields(result["report"]) == []
    assert len(calls) == 1
    assert "cleared the area, stopped 1 hour" in calls[0]  # Worker's own words sent for language detection

def test_invalid_analysis_is_retried():
    bad = dict(GOOD_ANALYSIS, ai_severity="critical")  # Wrong casing is not an allowed value
    client, calls = _fake_client(json.dumps(bad), "not json", json.dumps(GOOD_ANALYSIS))
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(_complete_reply_without_analysis()), "ok")
    assert result["is_complete"] is True
    assert len(calls) == 3

def test_analysis_failure_gives_clear_error():
    client, _ = _fake_client("not json", "not json", "not json")
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(_complete_reply_without_analysis()), "ok")
    assert result["error"] == am.ANALYSIS_FAILED_MESSAGE
    assert result["is_complete"] is False

def test_analysis_api_error_does_not_crash():
    def broken(model, contents, config):
        raise ConnectionError("no internet")
    client = pytypes.SimpleNamespace(models=pytypes.SimpleNamespace(generate_content=broken))
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(_complete_reply_without_analysis()), "ok")
    assert result["error"] == am.ANALYSIS_FAILED_MESSAGE

def test_complete_report_needs_no_extra_request():
    reply = json.dumps({"reply": "Done", "is_complete": True, "report": dict(FILLED_USER_DETAILS, **GOOD_ANALYSIS)})
    client, calls = _fake_client()
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(reply), "ok")
    assert result["is_complete"] is True
    assert calls == []

def test_missing_worker_details_never_ask_worker_for_ai_fields():
    report = dict(FILLED_USER_DETAILS, location=None, **{name: None for name in am.AI_FIELDS})
    reply = json.dumps({"reply": "Done", "is_complete": True, "report": report})
    client, calls = _fake_client()
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(reply), "ok")
    assert "location" in result["error"]
    assert "severity" not in result["error"]
    assert calls == []

def test_invalid_ai_fields_check():
    assert am._invalid_ai_fields(GOOD_ANALYSIS) == []
    assert am._invalid_ai_fields(dict(GOOD_ANALYSIS, is_near_miss="false", root_cause_category="Cable")) == [
        "is_near_miss", "root_cause_category"]


# ------------------------------------------------- #
# Stress-Test Regressions (Bad AI Values Found Offline)
# ------------------------------------------------- #

def test_parse_rejects_wrong_types_for_reply_and_is_complete():
    report = '"report": {}'
    assert am._parse_reply('{"reply": null, "is_complete": false, ' + report + '}') is None
    assert am._parse_reply('{"reply": "", "is_complete": false, ' + report + '}') is None
    assert am._parse_reply('{"reply": "Hi", "is_complete": "false", ' + report + '}') is None  # Text "false" is truthy

def test_parse_drops_unknown_report_keys():
    result = am._parse_reply('{"reply": "Hi", "is_complete": false, "report": {"location": "Bay 2", "witnesses": "Ali"}}')
    assert "witnesses" not in result["report"]  # Would otherwise become a new column in data.csv
    assert result["report"]["location"] == "Bay 2"

def test_invalid_user_fields_check():
    assert am._invalid_user_fields(FILLED_USER_DETAILS) == []
    bad = dict(FILLED_USER_DETAILS, incident_date="13/10/2026", incident_time="25:99", hospitalised="no",
               work_stoppage_hours=-1, reporter_name=["Muthu"])
    assert sorted(am._invalid_user_fields(bad)) == sorted(
        ["incident_date", "incident_time", "hospitalised", "work_stoppage_hours", "reporter_name"])

def test_unknown_allowed_where_worker_may_not_know():
    unknown = dict(FILLED_USER_DETAILS, location=am.UNKNOWN_VALUE, incident_time=am.UNKNOWN_VALUE,
                   work_stoppage_hours=am.UNKNOWN_VALUE)
    assert am._invalid_user_fields(unknown) == []
    assert "incident_date" in am._invalid_user_fields(dict(FILLED_USER_DETAILS, incident_date=am.UNKNOWN_VALUE))

def test_badly_formatted_date_is_never_marked_complete():
    report = dict(FILLED_USER_DETAILS, incident_date="13/10/2026", **GOOD_ANALYSIS)
    reply = json.dumps({"reply": "Done", "is_complete": True, "report": report})
    client, _ = _fake_client()
    with mock.patch.object(am, "_get_client", return_value=client):
        result = am.send_message(_fake_chat(reply), "ok")
    assert result["is_complete"] is False
    assert "incident date" in result["error"]

def test_response_without_text_does_not_crash():
    chat = pytypes.SimpleNamespace(send_message=lambda message: pytypes.SimpleNamespace(), get_history=lambda: [])
    result = am.send_message(chat, "hi")
    assert "error" in result


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