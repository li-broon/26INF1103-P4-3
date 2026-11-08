# ------- #
# Imports
# ------- #

from src.ai_manager import AIServiceError


# A Fake AI Manager with No API Key: Refuses to Start, Like the Real One
class FakeNoKeyAIManager:
    def start_conversation(self):
        raise AIServiceError("GEMINI_API_KEY is missing.")
