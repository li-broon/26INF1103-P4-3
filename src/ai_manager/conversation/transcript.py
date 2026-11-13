# ------- #
# Imports
# ------- #

from datetime import datetime
from uuid import uuid4
from src.ai_manager.constants import AI_LABEL, WORKER_LABEL

# ----- #
# Class
# ----- #

# The Back-and-Forth Between the Worker and the AI, Exactly as Written (Untranslated), with the ID that Links it to the Saved Report
class Transcript:
    def __init__(self):
        # Date and Time the Chat Started, plus 4 Random Characters so Two Reports in the Same Second Cannot Clash
        self._transcript_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:4]
        self._turns = []  # (Speaker, Text) in the Order Spoken

    @property
    def transcript_id(self) -> str:
        return self._transcript_id

    def add_worker(self, text: str) -> None:
        self._turns.append((WORKER_LABEL, text))

    def add_ai(self, text: str) -> None:
        self._turns.append((AI_LABEL, text))

    # Everything the Worker Said, in Order (Context for the AI's Separate Analysis Request)
    def worker_messages(self) -> list[str]:
        return [text for speaker, text in self._turns if speaker == WORKER_LABEL]

    # One Line per Turn: "Worker: ..." then "AI: ..."
    def as_text(self) -> str:
        return "\n".join([f"{speaker}: {text}" for speaker, text in self._turns])
