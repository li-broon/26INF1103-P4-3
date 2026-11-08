# ------- #
# Imports
# ------- #

from src.ai_manager.conversation.ai_reply import AIReply
from tests.fakes.fake_conversation import FakeConversation


# A Fake AI Manager: Starts a Fake Chat with the Prepared Replies
class FakeAIManager:
    def __init__(self, replies: list[AIReply]):
        self._replies = replies

    def start_conversation(self) -> FakeConversation:
        return FakeConversation(self._replies)
