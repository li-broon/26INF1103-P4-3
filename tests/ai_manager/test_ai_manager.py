# ---------------- #
# Import and Setup
# ---------------- #
import os
import json
from unittest import mock

from google.genai import errors
from src.ai_manager import AIManager, GeminiService, AIServiceError
from src.ai_manager.constants import SEVERITY_LEVELS, UNKNOWN_VALUE
from src.ai_manager.fields.text_field import TextField
from src.ai_manager.fields.date_field import DateField
from src.ai_manager.fields.time_field import TimeField
from src.ai_manager.fields.boolean_field import BooleanField
from src.ai_manager.fields.number_field import NumberField
from src.ai_manager.fields.choice_field import ChoiceField
from src.ai_manager.fields.field_set import FieldSet
from src.ai_manager.services import gemini_service  # Its 'time' Module is Patched so Retry Waits are Skipped
from src.ai_manager.services.ai_service import AIService
from src.ai_manager.conversation.incident_conversation import IncidentConversation
from tests.ai_manager.class_fake_ai_service import FakeAIService
from tests.ai_manager.class_fake_gemini_chat import FakeGeminiChat

# ------------ #
# Test Helpers
# ------------ #

# Worker Details All Filled In and Valid
GOOD_WORKER_DETAILS = {
    "reporter_name": "Muthu", "location": "Tuas site, loading bay", "incident_date": "2026-10-13",
    "incident_time": "10:00", "description": "Slipped on oil", "injury_status": "Bruised knee",
    "hospitalised": False, "immediate_action_taken": "Cleared the area", "work_stoppage_hours": 1,
}

# A Valid Analysis
GOOD_ANALYSIS = {
    "detected_language": "English", "ai_severity": "Low", "is_near_miss": False,
    "root_cause_category": "Slip or Trip", "lost_time_injury": False,
    "safety_recommendation": "Clean oil spills straight away.",
}

# Build a Chat Reply in the JSON Format the AI is Told to Use
def chat_reply(report: dict, is_complete: bool = True, reply: str = "Thank you!") -> str:
    return json.dumps({"reply": reply, "is_complete": is_complete, "report": report})

# Start a Conversation that Talks to the Fake Service
def new_conversation(service: AIService) -> IncidentConversation:
    return AIManager(service).start_conversation()

# ------------------ #
# Report Field Tests
# ------------------ #

# Text Must be Non-Empty Text (Lists, Numbers and Blank Strings are Rejected)
def test_text_field():
    field = TextField("location", "where it happened")
    assert field.is_valid("Tuas site")
    for bad in ["", "   ", None, 5, ["Tuas"]]:
        assert not field.is_valid(bad), bad

# Dates Must be Real YYYY-MM-DD Dates and Not in the Future; "unknown" is Not Allowed
def test_date_field():
    field = DateField("incident_date", "date in YYYY-MM-DD")
    assert field.is_valid("2026-10-13")
    for bad in ["13/10/2026", "2026-13-45", "yesterday", "2999-01-01", UNKNOWN_VALUE, None]:
        assert not field.is_valid(bad), bad

# "unknown" is Accepted Only by Fields Created with allows_unknown=True
def test_unknown_only_where_allowed():
    allows = TimeField("incident_time", "time", allows_unknown=True)
    strict = TimeField("incident_time", "time")
    assert allows.is_valid(UNKNOWN_VALUE)
    assert not strict.is_valid(UNKNOWN_VALUE)
    assert allows.is_valid("00:00") and not allows.is_valid("25:99")

# true/false Must be Real Booleans, Not Text
def test_boolean_field():
    field = BooleanField("hospitalised", "sent to hospital")
    assert field.is_valid(True) and field.is_valid(False)
    for bad in ["true", "yes", "no", 1, None]:
        assert not field.is_valid(bad), bad

# Numbers Must be 0 or More (True/False and Text are Not Numbers)
def test_number_field():
    field = NumberField("work_stoppage_hours", "hours")
    assert field.is_valid(0) and field.is_valid(2.5)
    for bad in [-1, "2", True, None, float("inf")]:
        assert not field.is_valid(bad), bad

# Choice Fields Only Accept their Exact Choices, and Describe Them for the Prompt
def test_choice_field():
    field = ChoiceField("ai_severity", SEVERITY_LEVELS)
    assert field.is_valid("Critical")
    assert not field.is_valid("critical")  # Wrong Casing would Score 0 in 'logic_manager'
    assert field.describe() == "- ai_severity: one of Low, Medium, High, Critical"

# A FieldSet Checks Different Field Types Through the Same is_valid() Call (Polymorphism)
def test_field_set_lists_invalid_fields():
    fields = FieldSet([
        TextField("reporter_name", "name"),
        DateField("incident_date", "date"),
        BooleanField("hospitalised", "hospital"),
    ])
    invalid = fields.invalid({"reporter_name": "Ravi", "incident_date": "13/10/2026", "hospitalised": "no"})
    assert [field.name for field in invalid] == ["incident_date", "hospitalised"]
    assert fields.names() == ["reporter_name", "incident_date", "hospitalised"]

# ------------------------ #
# Conversation Reply Tests
# ------------------------ #

# The System Prompt Lists Every Field and the Allowed Values
def test_system_prompt_lists_fields():
    service = FakeAIService([chat_reply({}, is_complete=False)])
    new_conversation(service)
    assert "- incident_date: date in YYYY-MM-DD" in service.system_prompt
    assert "one of Low, Medium, High, Critical" in service.system_prompt

# A Normal Mid-Conversation Reply is Passed Straight Through
def test_mid_conversation_reply():
    service = FakeAIService([chat_reply({"reporter_name": "Muthu"}, is_complete=False, reply="Where did it happen?")])
    reply = new_conversation(service).send("hi, I am Muthu")
    assert reply.error is None
    assert reply.reply == "Where did it happen?"
    assert reply.is_complete is False
    assert reply.report["reporter_name"] == "Muthu"

# Broken JSON is Sent Back to the AI to Fix, then the Fixed Reply is Used
def test_bad_json_is_retried():
    service = FakeAIService(["not json", chat_reply({}, is_complete=False, reply="Fixed")])
    reply = new_conversation(service).send("hi")
    assert reply.reply == "Fixed"
    assert service.sent_messages[1] == IncidentConversation.BAD_JSON_MESSAGE

# If the AI Never Sends Valid JSON, the Worker Gets an Error (Never a Crash)
def test_bad_json_every_time_gives_error():
    service = FakeAIService(["not json"])
    reply = new_conversation(service).send("hi")
    assert reply.error == "The AI kept replying in the wrong format."
    assert len(service.sent_messages) == 1 + IncidentConversation.MAX_FORMAT_RETRIES

# Wrong Types for reply / is_complete Count as the Wrong Format (Text "false" would Otherwise be Treated as True)
def test_wrong_reply_types_are_rejected():
    for bad in ['{"reply": null, "is_complete": false, "report": {}}',
                '{"reply": "", "is_complete": false, "report": {}}',
                '{"reply": "Hi", "is_complete": "false", "report": {}}',
                '{"reply": "Hi", "is_complete": false, "report": "Sector A"}']:
        reply = new_conversation(FakeAIService([bad])).send("hi")
        assert reply.error is not None, bad

# Extra Keys from the AI are Dropped (They would Otherwise become New Columns in data.csv)
def test_unknown_report_keys_are_dropped():
    service = FakeAIService([chat_reply({"location": "Bay 2", "witnesses": "Ali"}, is_complete=False)])
    reply = new_conversation(service).send("hi")
    assert "witnesses" not in reply.report
    assert reply.report["location"] == "Bay 2"

# API Errors Reach the Worker with their Code and Status
def test_api_error_becomes_error_reply():
    service = FakeAIService([AIServiceError("quota exceeded", 429, "RESOURCE_EXHAUSTED")])
    reply = new_conversation(service).send("hi")
    assert reply.error == "quota exceeded"
    assert reply.error_code == 429 and reply.error_status == "RESOURCE_EXHAUSTED"
    assert reply.is_complete is False

# ---------------------- #
# Completed Report Tests
# ---------------------- #

# A Fully Valid Report is Complete with No Extra Requests
def test_complete_report_needs_no_extra_request():
    service = FakeAIService([chat_reply({**GOOD_WORKER_DETAILS, **GOOD_ANALYSIS})])
    reply = new_conversation(service).send("stopped 1 hour")
    assert reply.is_complete is True
    assert len(service.sent_messages) == 1
    assert service.json_prompts == []

# A Badly Formatted Date is Sent Back to the AI, and Fixed after One Follow-Up
def test_ai_fixes_bad_date_after_follow_up():
    bad = chat_reply({**GOOD_WORKER_DETAILS, **GOOD_ANALYSIS, "incident_date": "13/10/2026"})
    good = chat_reply({**GOOD_WORKER_DETAILS, **GOOD_ANALYSIS})
    service = FakeAIService([bad, good])
    reply = new_conversation(service).send("ok")
    assert reply.is_complete is True
    assert "incident_date (date in YYYY-MM-DD)" in service.sent_messages[1]

# If the AI Keeps a Bad Date, the Report is Never Marked Complete, and the Worker is Told what is Wrong
def test_bad_date_is_never_marked_complete():
    service = FakeAIService([chat_reply({**GOOD_WORKER_DETAILS, **GOOD_ANALYSIS, "incident_date": "yesterday"})])
    reply = new_conversation(service).send("ok")
    assert reply.is_complete is False
    assert "incident date" in reply.error
    assert "severity" not in reply.error  # The Worker is Never Asked for the AI's Own Fields

# Empty Analysis is Filled by a Separate Request that Includes the Worker's Own Words
def test_empty_analysis_is_filled_by_separate_request():
    empty_analysis = {name: None for name in GOOD_ANALYSIS}
    service = FakeAIService([chat_reply({**GOOD_WORKER_DETAILS, **empty_analysis})], [json.dumps(GOOD_ANALYSIS)])
    reply = new_conversation(service).send("tergelincir minyak, lutut lebam")
    assert reply.is_complete is True
    assert reply.report["ai_severity"] == "Low"
    assert "tergelincir minyak, lutut lebam" in service.json_prompts[0]

# An Invalid Analysis (e.g. Wrong Casing) is Requested Again
def test_invalid_analysis_is_retried():
    empty_analysis = {name: None for name in GOOD_ANALYSIS}
    bad = json.dumps({**GOOD_ANALYSIS, "ai_severity": "critical"})
    service = FakeAIService([chat_reply({**GOOD_WORKER_DETAILS, **empty_analysis})], [bad, "not json", json.dumps(GOOD_ANALYSIS)])
    reply = new_conversation(service).send("ok")
    assert reply.is_complete is True
    assert len(service.json_prompts) == 3

# If the Analysis Keeps Failing (or the API Fails), the Worker Gets a Clear Message to Try Again
def test_analysis_failure_gives_clear_error():
    empty_analysis = {name: None for name in GOOD_ANALYSIS}
    for analysis_replies in (["not json"], [AIServiceError("offline")]):
        service = FakeAIService([chat_reply({**GOOD_WORKER_DETAILS, **empty_analysis})], analysis_replies)
        reply = new_conversation(service).send("ok")
        assert reply.error == IncidentConversation.ANALYSIS_FAILED_MESSAGE
        assert reply.is_complete is False

# ------------------------------------ #
# Gemini Service Tests (No Live Calls)
# ------------------------------------ #


# Make a Gemini API Error with the Given HTTP Code
def api_error(code: int, status: str) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": f"error {code}", "status": status}})

# Build a GeminiService with a Dummy Key (Creating the Client Does Not Contact Google)
def dummy_gemini_service() -> GeminiService:
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        return GeminiService()

# A Missing API Key is Reported Before Any Chat Starts
def test_missing_api_key_raises():
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        try:
            GeminiService()
            assert False, "Expected AIServiceError"
        except AIServiceError as error:
            assert "GEMINI_API_KEY is missing" in error.message

# Busy (503) and Rate Limited (429) Requests are Retried, then Succeed
def test_busy_and_rate_limited_are_retried():
    chat = FakeGeminiChat([api_error(503, "UNAVAILABLE"), api_error(429, "RESOURCE_EXHAUSTED")])
    with mock.patch.object(gemini_service.time, "sleep") as fake_sleep:
        assert dummy_gemini_service().send_chat_message(chat, "hi") == "ok"
    assert chat.attempts == 3
    assert [call.args[0] for call in fake_sleep.call_args_list] == [3, 6]

# Other API Errors (e.g. Invalid Key) are Not Retried, Since Waiting Won't Fix Them
def test_other_api_errors_are_not_retried():
    chat = FakeGeminiChat([api_error(400, "INVALID_ARGUMENT")])
    try:
        dummy_gemini_service().send_chat_message(chat, "hi")
        assert False, "Expected AIServiceError"
    except AIServiceError as error:
        assert error.code == 400 and error.status == "INVALID_ARGUMENT"
    assert chat.attempts == 1

# An API Error with No Message Still Reaches the Worker as an Error (Not a Blank "Success")
def test_api_error_without_message_still_shows_error():
    chat = FakeGeminiChat([errors.APIError(500, {})])
    try:
        dummy_gemini_service().send_chat_message(chat, "hi")
        assert False, "Expected AIServiceError"
    except AIServiceError as error:
        assert error.message == "Gemini returned an error with no details (code 500)."
        reply = new_conversation(FakeAIService([error])).send("hi")
        assert reply.error == error.message
        assert reply.is_complete is False

# Gives Up after MAX_ATTEMPTS when Gemini Stays Busy
def test_gives_up_when_always_busy():
    chat = FakeGeminiChat([api_error(503, "UNAVAILABLE")] * 10)
    with mock.patch.object(gemini_service.time, "sleep"):
        try:
            dummy_gemini_service().send_chat_message(chat, "hi")
            assert False, "Expected AIServiceError"
        except AIServiceError as error:
            assert error.code == 503
    assert chat.attempts == GeminiService.MAX_ATTEMPTS

# No Internet or a Timeout Becomes an AIServiceError Instead of Crashing
def test_connection_problem_becomes_service_error():
    chat = FakeGeminiChat([TimeoutError("timed out")])
    try:
        dummy_gemini_service().send_chat_message(chat, "hi")
        assert False, "Expected AIServiceError"
    except AIServiceError as error:
        assert "Could not reach the AI" in error.message
        assert error.code is None
