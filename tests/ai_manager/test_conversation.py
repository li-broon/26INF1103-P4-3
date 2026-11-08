# ------- #
# Imports
# ------- #

import json

from src.ai_manager import AIManager, AIServiceError
from src.ai_manager.conversation.incident_conversation import IncidentConversation
from tests.fakes.fake_ai_service import FakeAIService


# Tests for IncidentConversation, Using a Fake AI Service (No Live API Calls)
class TestIncidentConversation:

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
    def _chat_reply(self, report: dict, is_complete: bool = True, reply: str = "Thank you!") -> str:
        return json.dumps({"reply": reply, "is_complete": is_complete, "report": report})

    # Start a Conversation that Talks to the Fake Service
    def _new_conversation(self, service: FakeAIService) -> IncidentConversation:
        return AIManager(service).start_conversation()

    # A Complete Report with the Analysis Left Empty (the Bug Seen in Live Testing)
    def _report_without_analysis(self) -> dict:
        empty_analysis = {name: None for name in self.GOOD_ANALYSIS}
        return {**self.GOOD_WORKER_DETAILS, **empty_analysis}

    # ---------------- Conversation Replies ---------------- #

    # The System Prompt Lists Every Field and the Allowed Values
    def test_system_prompt_lists_fields(self):
        service = FakeAIService([self._chat_reply({}, is_complete=False)])
        self._new_conversation(service)
        assert "- incident_date: date in YYYY-MM-DD" in service.system_prompt
        assert "one of Low, Medium, High, Critical" in service.system_prompt

    # A Normal Mid-Conversation Reply is Passed Straight Through
    def test_mid_conversation_reply(self):
        service = FakeAIService([self._chat_reply({"reporter_name": "Muthu"}, is_complete=False, reply="Where did it happen?")])
        reply = self._new_conversation(service).send("hi, I am Muthu")
        assert reply.error is None
        assert reply.reply == "Where did it happen?"
        assert reply.is_complete is False
        assert reply.report["reporter_name"] == "Muthu"

    # Broken JSON is Sent Back to the AI to Fix, then the Fixed Reply is Used
    def test_bad_json_is_retried(self):
        service = FakeAIService(["not json", self._chat_reply({}, is_complete=False, reply="Fixed")])
        reply = self._new_conversation(service).send("hi")
        assert reply.reply == "Fixed"
        assert service.sent_messages[1] == IncidentConversation.BAD_JSON_MESSAGE

    # If the AI Never Sends Valid JSON, the Worker Gets an Error (Never a Crash)
    def test_bad_json_every_time_gives_error(self):
        service = FakeAIService(["not json"])
        reply = self._new_conversation(service).send("hi")
        assert reply.error == "The AI kept replying in the wrong format."
        assert len(service.sent_messages) == 1 + IncidentConversation.MAX_FORMAT_RETRIES

    # Wrong Types for reply / is_complete Count as the Wrong Format (Text "false" would Otherwise be Treated as True)
    def test_wrong_reply_types_are_rejected(self):
        for bad in ['{"reply": null, "is_complete": false, "report": {}}',
                    '{"reply": "", "is_complete": false, "report": {}}',
                    '{"reply": "Hi", "is_complete": "false", "report": {}}',
                    '{"reply": "Hi", "is_complete": false, "report": "Sector A"}']:
            reply = self._new_conversation(FakeAIService([bad])).send("hi")
            assert reply.error is not None, bad

    # Extra Keys from the AI are Dropped (They would Otherwise become New Columns in data.csv)
    def test_unknown_report_keys_are_dropped(self):
        service = FakeAIService([self._chat_reply({"location": "Bay 2", "witnesses": "Ali"}, is_complete=False)])
        reply = self._new_conversation(service).send("hi")
        assert "witnesses" not in reply.report
        assert reply.report["location"] == "Bay 2"

    # API Errors Reach the Worker with their Code and Status
    def test_api_error_becomes_error_reply(self):
        service = FakeAIService([AIServiceError("quota exceeded", 429, "RESOURCE_EXHAUSTED")])
        reply = self._new_conversation(service).send("hi")
        assert reply.error == "quota exceeded"
        assert reply.error_code == 429 and reply.error_status == "RESOURCE_EXHAUSTED"
        assert reply.is_complete is False

    # ---------------- Completed Reports ---------------- #

    # A Fully Valid Report is Complete with No Extra Requests
    def test_complete_report_needs_no_extra_request(self):
        service = FakeAIService([self._chat_reply({**self.GOOD_WORKER_DETAILS, **self.GOOD_ANALYSIS})])
        reply = self._new_conversation(service).send("stopped 1 hour")
        assert reply.is_complete is True
        assert len(service.sent_messages) == 1
        assert service.json_prompts == []

    # A Badly Formatted Date is Sent Back to the AI, and Fixed after One Follow-Up
    def test_ai_fixes_bad_date_after_follow_up(self):
        bad = self._chat_reply({**self.GOOD_WORKER_DETAILS, **self.GOOD_ANALYSIS, "incident_date": "13/10/2026"})
        good = self._chat_reply({**self.GOOD_WORKER_DETAILS, **self.GOOD_ANALYSIS})
        service = FakeAIService([bad, good])
        reply = self._new_conversation(service).send("ok")
        assert reply.is_complete is True
        assert "incident_date (date in YYYY-MM-DD)" in service.sent_messages[1]

    # If the AI Keeps a Bad Date, the Report is Never Marked Complete, and the Worker is Told what is Wrong
    def test_bad_date_is_never_marked_complete(self):
        service = FakeAIService([self._chat_reply({**self.GOOD_WORKER_DETAILS, **self.GOOD_ANALYSIS, "incident_date": "yesterday"})])
        reply = self._new_conversation(service).send("ok")
        assert reply.is_complete is False
        assert "incident date" in reply.error
        assert "severity" not in reply.error  # The Worker is Never Asked for the AI's Own Fields

    # Empty Analysis is Filled by a Separate Request that Includes the Worker's Own Words
    def test_empty_analysis_is_filled_by_separate_request(self):
        service = FakeAIService([self._chat_reply(self._report_without_analysis())], [json.dumps(self.GOOD_ANALYSIS)])
        reply = self._new_conversation(service).send("tergelincir minyak, lutut lebam")
        assert reply.is_complete is True
        assert reply.report["ai_severity"] == "Low"
        assert "tergelincir minyak, lutut lebam" in service.json_prompts[0]

    # An Invalid Analysis (e.g. Wrong Casing) is Requested Again
    def test_invalid_analysis_is_retried(self):
        bad = json.dumps({**self.GOOD_ANALYSIS, "ai_severity": "critical"})
        service = FakeAIService([self._chat_reply(self._report_without_analysis())], [bad, "not json", json.dumps(self.GOOD_ANALYSIS)])
        reply = self._new_conversation(service).send("ok")
        assert reply.is_complete is True
        assert len(service.json_prompts) == 3

    # If the Analysis Keeps Failing (or the API Fails), the Worker Gets a Clear Message to Try Again
    def test_analysis_failure_gives_clear_error(self):
        for analysis_replies in (["not json"], [AIServiceError("offline")]):
            service = FakeAIService([self._chat_reply(self._report_without_analysis())], analysis_replies)
            reply = self._new_conversation(service).send("ok")
            assert reply.error == IncidentConversation.ANALYSIS_FAILED_MESSAGE
            assert reply.is_complete is False
