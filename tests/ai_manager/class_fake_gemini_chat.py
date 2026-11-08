# ------- #
# Imports
# ------- #

from tests.ai_manager.class_fake_gemini_response import FakeGeminiResponse

# ---- #
# Class
# ---- #

# Fake Gemini Chat Session: Raises the Given Errors in Order, then Replies "ok"
class FakeGeminiChat:
    def __init__(self, errors_to_raise: list[Exception]):
        self._errors = list(errors_to_raise)
        self.attempts = 0

    def send_message(self, message: str) -> FakeGeminiResponse:
        self.attempts += 1
        if self._errors:
            raise self._errors.pop(0)
        return FakeGeminiResponse("ok")
