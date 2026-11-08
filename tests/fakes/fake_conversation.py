# ------- #
# Imports
# ------- #

from src.ai_manager.conversation.ai_reply import AIReply


# A Fake Chat: Hands Back the Prepared Replies One at a Time
class FakeConversation:
    def __init__(self, replies: list[AIReply]):
        self._replies = list(replies)

    def send(self, text: str) -> AIReply:
        return self._replies.pop(0)
