# A fake chat: hands back the prepared replies one at a time
class FakeConversation:
    def __init__(self, replies):
        self._replies = iter(replies)

    def send(self, text):
        return next(self._replies)
