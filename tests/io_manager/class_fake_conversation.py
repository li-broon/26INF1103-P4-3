# ------- #
# Imports
# ------- #

from src.ai_manager.conversation.transcript import Transcript

# ----- #
# Class
# ----- #

# A fake chat: hands back the prepared replies one at a time, and keeps a real Transcript like the real conversation does
class FakeConversation:
    def __init__(self, replies):
        self._replies = iter(replies)
        self.transcript = Transcript()

    def send(self, text):
        reply = next(self._replies)
        if not reply.error:
            self.transcript.add_worker(text)
            self.transcript.add_ai(reply.reply)
        return reply
