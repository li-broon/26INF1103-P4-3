# ------- #
# Imports
# ------- #

from tests.io_manager.class_fake_conversation import FakeConversation

# ---- #
# Class
# ---- #

# A fake AI Manager: starts a fake chat with the prepared replies
class FakeAI:
    def __init__(self, replies):
        self._replies = replies

    def start_conversation(self):
        return FakeConversation(self._replies)
