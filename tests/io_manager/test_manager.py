# ------- #
# Imports
# ------- #

import pandas as pd

from src.ai_manager.conversation.ai_reply import AIReply
from src.io_manager.manager import IOManager
from src.logic_manager import SaveOutcome
from tests.fakes.fake_ai_manager import FakeAIManager
from tests.fakes.fake_data_manager import FakeDataManager
from tests.fakes.fake_logic_manager import FakeLogicManager
from tests.fakes.fake_no_key_ai_manager import FakeNoKeyAIManager
from tests.fakes.scripted_input import ScriptedInput
from tests.helpers.io_samples import REPORT, SAVED_FIELDS
from tests.helpers.print_capture import PrintCapture


# Tests for the IOManager Running the Whole App, with Fake Managers (No API Key, No CSV File)
class TestIOManager:

    def setup_method(self):
        self._capture = PrintCapture()

    # Build an IOManager whose "User" Types the Given Answers in Order
    def _io_manager(self, ai=None, logic=None, data=None, answers: tuple = ()) -> IOManager:
        return IOManager(ai or FakeAIManager([]), logic or FakeLogicManager(), data or FakeDataManager(pd.DataFrame()),
                         read=ScriptedInput(*answers).read)

    # Run the App and Return Everything it Printed
    def _run(self, manager: IOManager) -> str:
        return self._capture.text_of(manager.run)

    # Menu 1 (chat) -> one message -> report complete -> "n" to viewing reports -> 3 (exit)
    def test_chatbot_saves_a_complete_report(self):
        manager = self._io_manager(ai=FakeAIManager([AIReply("Thanks!", True, REPORT)]),
                                   answers=("1", "I cut my hand", "n", "3"))
        text = self._run(manager)
        assert "Your report has been saved" in text
        assert "Ahmad bin Ismail" in text
        assert "Goodbye" in text

    # Typing quit asks to confirm, and nothing is saved
    def test_chatbot_quit_asks_to_confirm(self):
        text = self._run(self._io_manager(answers=("1", "quit", "y", "3")))
        assert "Report cancelled. Nothing was saved." in text

    # An error with no code must not tell the worker to resend
    def test_chatbot_error_without_code_does_not_say_resend(self):
        manager = self._io_manager(ai=FakeAIManager([AIReply(error="Report not finished")]),
                                   answers=("1", "hi", "quit", "y", "3"))
        text = self._run(manager)
        assert "couldn't be finished" in text
        assert "resend" not in text

    # A real API error (it has a code) does tell the worker to resend
    def test_chatbot_api_error_says_resend(self):
        error = AIReply(error="Too many requests", error_code=429, error_status="RESOURCE_EXHAUSTED")
        manager = self._io_manager(ai=FakeAIManager([error]), answers=("1", "hi", "quit", "y", "3"))
        text = self._run(manager)
        assert "429" in text
        assert "resend" in text

    # A failed save is reported, and the worker is not told it was saved
    def test_chatbot_save_failure_is_reported(self):
        failed = SaveOutcome(**dict(SAVED_FIELDS, saved=False, message="Disk full"))
        manager = self._io_manager(ai=FakeAIManager([AIReply("Thanks!", True, REPORT)]),
                                   logic=FakeLogicManager(failed),
                                   answers=("1", "I fell", "n", "3"))
        text = self._run(manager)
        assert "NOT saved" in text
        assert "has been saved" not in text

    # Without an API key, the chatbot explains why and returns to the menu instead of crashing
    def test_chatbot_without_api_key(self):
        text = self._run(self._io_manager(ai=FakeNoKeyAIManager(), answers=("1", "3")))
        assert "GEMINI_API_KEY is missing" in text
        assert "Goodbye" in text

    # Viewing reports with none saved says so instead of showing an empty table
    def test_view_reports_when_none_saved(self):
        text = self._run(self._io_manager(answers=("2", "3")))
        assert "No incident reports have been saved yet" in text
