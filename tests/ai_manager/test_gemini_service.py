# ------- #
# Imports
# ------- #

import os
from unittest import mock

from google.genai import errors

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.ai_manager.services import gemini_service  # Its 'time' Module is Patched so Retry Waits are Skipped
from tests.fakes.fake_ai_service import FakeAIService
from tests.fakes.fake_gemini_chat import FakeGeminiChat


# Tests for GeminiService's Key Check, Retries and Error Handling (No Live Calls: a Fake Chat Raises the Errors)
class TestGeminiService:

    # Make a Gemini API Error with the Given HTTP Code
    def _api_error(self, code: int, status: str) -> errors.APIError:
        return errors.APIError(code, {"error": {"message": f"error {code}", "status": status}})

    # Build a GeminiService with a Dummy Key (Creating the Client Does Not Contact Google)
    def _service(self) -> GeminiService:
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            return GeminiService()

    # A Missing API Key is Reported Before Any Chat Starts
    def test_missing_api_key_raises(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            try:
                GeminiService()
                assert False, "Expected AIServiceError"
            except AIServiceError as error:
                assert "GEMINI_API_KEY is missing" in error.message

    # Busy (503) and Rate Limited (429) Requests are Retried, then Succeed
    def test_busy_and_rate_limited_are_retried(self):
        chat = FakeGeminiChat([self._api_error(503, "UNAVAILABLE"), self._api_error(429, "RESOURCE_EXHAUSTED")])
        with mock.patch.object(gemini_service.time, "sleep") as fake_sleep:
            assert self._service().send_chat_message(chat, "hi") == "ok"
        assert chat.attempts == 3
        assert [call.args[0] for call in fake_sleep.call_args_list] == [3, 6]

    # Other API Errors (e.g. Invalid Key) are Not Retried, Since Waiting Won't Fix Them
    def test_other_api_errors_are_not_retried(self):
        chat = FakeGeminiChat([self._api_error(400, "INVALID_ARGUMENT")])
        try:
            self._service().send_chat_message(chat, "hi")
            assert False, "Expected AIServiceError"
        except AIServiceError as error:
            assert error.code == 400 and error.status == "INVALID_ARGUMENT"
        assert chat.attempts == 1

    # An API Error with No Message Still Reaches the Worker as an Error (Not a Blank "Success")
    def test_api_error_without_message_still_shows_error(self):
        chat = FakeGeminiChat([errors.APIError(500, {})])
        try:
            self._service().send_chat_message(chat, "hi")
            assert False, "Expected AIServiceError"
        except AIServiceError as error:
            assert error.message == "Gemini returned an error with no details (code 500)."
            reply = AIManager(FakeAIService([error])).start_conversation().send("hi")
            assert reply.error == error.message
            assert reply.is_complete is False

    # Gives Up after MAX_ATTEMPTS when Gemini Stays Busy
    def test_gives_up_when_always_busy(self):
        chat = FakeGeminiChat([self._api_error(503, "UNAVAILABLE")] * 10)
        with mock.patch.object(gemini_service.time, "sleep"):
            try:
                self._service().send_chat_message(chat, "hi")
                assert False, "Expected AIServiceError"
            except AIServiceError as error:
                assert error.code == 503
        assert chat.attempts == GeminiService.MAX_ATTEMPTS

    # No Internet or a Timeout Becomes an AIServiceError Instead of Crashing
    def test_connection_problem_becomes_service_error(self):
        chat = FakeGeminiChat([TimeoutError("timed out")])
        try:
            self._service().send_chat_message(chat, "hi")
            assert False, "Expected AIServiceError"
        except AIServiceError as error:
            assert "Could not reach the AI" in error.message
            assert error.code is None
