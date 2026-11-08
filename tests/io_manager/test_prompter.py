# ------- #
# Imports
# ------- #

import contextlib
from io import StringIO

from src.io_manager.prompts.prompter import Prompter
from tests.fakes.scripted_input import ScriptedInput


# Tests for the Prompter: All Keyboard Input Goes Through it, and Bad Answers are Asked Again
class TestPrompter:

    # A Prompter whose "User" Types the Given Answers in Order
    def _prompter(self, *answers: str) -> Prompter:
        return Prompter(read=ScriptedInput(*answers).read)

    # Test that blank, text and out-of-range answers are rejected before a valid one is accepted
    def test_ask_number_rejects_bad_input_then_accepts(self):
        prompter = self._prompter("", "abc", "9", "2")
        with contextlib.redirect_stdout(StringIO()) as out:
            result = prompter.ask_number("Choose (1-3): ", 1, 3)
        assert result == 2
        assert "can't be left blank" in out.getvalue()
        assert "'abc' is not a number" in out.getvalue()
        assert "9 is not an option" in out.getvalue()

    # The user types y, so ask_yes_no should give back True
    def test_yes(self):
        assert self._prompter("y").ask_yes_no("Leave?") is True

    # The user types n, so ask_yes_no should give back False
    def test_no(self):
        assert self._prompter("n").ask_yes_no("Leave?") is False

    # Test that choose_from returns the picked value, and None when the user picks Back
    def test_choose_from(self):
        values = ["Fall", "Fire", "Machinery"]
        with contextlib.redirect_stdout(StringIO()):
            picked = self._prompter("2").choose_from("Root Cause", values)
            back = self._prompter("4").choose_from("Root Cause", values)
        assert picked == "Fire"     # option 2 is the second value
        assert back is None         # option 4 is Back (3 values + 1)

    # Test that ask_text returns what was typed, without the spaces around it
    def test_ask_text_strips_spaces(self):
        assert self._prompter("  Warehouse B  ").ask_text("Keyword: ") == "Warehouse B"

    # Test that the cancel words work in any capitals, and normal text is not a cancel
    def test_is_cancel(self):
        prompter = Prompter()
        assert prompter.is_cancel("QUIT") is True
        assert prompter.is_cancel(" exit ") is True
        assert prompter.is_cancel("hello") is False
