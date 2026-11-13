# ------- #
# Imports
# ------- #

import logging
import os

from src.data_manager.storage.transcript_store import TranscriptStore

# Used for debugging to log warnings and errors instead of printing them to the console
logger = logging.getLogger(__name__)

# ----- #
# Class
# ----- #

# Keeps Each Conversation in its Own Text File, <folder>/<transcript_id>.txt (the TranscriptStore the App Uses)
class TextTranscriptStore(TranscriptStore):

    # folder is where the transcript files go (created on the first save)
    def __init__(self, folder: str) -> None:
        self._folder = folder

    # Writes the conversation to its file. Returns (success, message)
    def save(self, transcript_id: str, text: str) -> tuple[bool, str]:
        path = self._path(transcript_id)
        if path is None:
            return False, "Transcript rejected: invalid transcript ID."
        try:
            os.makedirs(self._folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as file:
                file.write(text + "\n")
        except OSError as error:
            logger.error("Could not write '%s': %s", path, error)
            return False, "Transcript could not be saved (file write error)."
        return True, "Transcript saved."

    # Reads the conversation back, or None if the ID has no file (e.g. a report saved before transcripts existed)
    def load(self, transcript_id) -> str | None:
        path = self._path(transcript_id)
        if path is None or not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as file:
                return file.read().rstrip("\n")
        except OSError as error:
            logger.warning("Could not read '%s': %s", path, error)
            return None

    # The file for an ID, or None if the ID is blank, not text, or not a plain file name (an ID edited in data.csv cannot point outside the folder)
    def _path(self, transcript_id) -> str | None:
        if not isinstance(transcript_id, str) or not transcript_id or os.path.basename(transcript_id) != transcript_id:
            return None
        return os.path.join(self._folder, transcript_id + ".txt")
