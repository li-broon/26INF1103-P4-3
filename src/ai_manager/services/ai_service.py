# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

# ----- #
# Class
# ----- #

# Contract Every AI Provider Must Follow (Gemini in the App, a Fake in the Tests)
class AIService(ABC):

    # Start a Conversation that Follows the System Prompt and Replies in JSON. Returns the Chat Session.
    @abstractmethod
    def start_chat(self, system_prompt: str):
        pass

    # Send One Message in a Chat and Return the Reply Text. Raises AIServiceError on Failure.
    @abstractmethod
    def send_chat_message(self, chat, message: str) -> str:
        pass

    # One-Off Request that Must Return JSON Matching the Schema. Returns the Reply Text. Raises AIServiceError on Failure.
    @abstractmethod
    def generate_json(self, prompt: str, schema: dict) -> str:
        pass