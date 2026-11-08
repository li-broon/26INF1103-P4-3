# ------- #
# Imports
# ------- #

from src.ai_manager import AIServiceError
from src.ai_manager.services.ai_service import AIService

# ---- #
# Class
# ---- #

# Fake AI Provider (Same AIService Contract, No Live API): Gives Out the Reply Texts (or AIServiceErrors to Raise) in Order, Repeating the Last One
class FakeAIService(AIService):
    def __init__(self, chat_replies: list[str | AIServiceError], json_replies: list[str | AIServiceError] | None = None):
        self._chat_replies = list(chat_replies)
        self._json_replies = list(json_replies or [])
        self.system_prompt = None
        self.sent_messages = []
        self.json_prompts = []

    def start_chat(self, system_prompt: str) -> str:
        self.system_prompt = system_prompt
        return "fake-chat"

    def send_chat_message(self, chat, message: str) -> str:
        self.sent_messages.append(message)
        return self._next(self._chat_replies)

    def generate_json(self, prompt: str, schema: dict) -> str:
        self.json_prompts.append(prompt)
        return self._next(self._json_replies)

    def _next(self, replies: list[str | AIServiceError]) -> str:
        item = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(item, AIServiceError):
            raise item
        return item
