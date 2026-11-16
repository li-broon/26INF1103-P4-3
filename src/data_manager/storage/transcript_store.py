# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

# ----- #
# Class
# ----- #

# Contract Every Transcript Store Must Follow (Text Files in the App, a Fake in the Tests)
class TranscriptStore(ABC):

    # Save One Conversation under its ID. Returns (success, message), it Never Crashes.
    @abstractmethod
    def save(self, transcript_id: str, text: str) -> tuple[bool, str]:
        pass

    # Return the Saved Transcript for an ID, or None if There is None
    @abstractmethod
    def load(self, transcript_id) -> str | None:
        pass
