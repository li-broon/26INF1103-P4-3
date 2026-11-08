# ------- #
# Imports
# ------- #

from src.ai_manager import AIServiceError

# ---- #
# Class
# ---- #

# A fake AI Manager with no API key: refuses to start, like the real one
class NoKeyAI:
    def start_conversation(self):
        raise AIServiceError("GEMINI_API_KEY is missing.")
