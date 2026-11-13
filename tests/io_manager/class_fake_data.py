# A fake Data Manager: always returns the table it was given, and remembers the transcripts it is asked to save
class FakeData:
    def __init__(self, table, transcript=None):
        self._table = table
        self._transcript = transcript  # What load_transcript gives back (None means no saved conversation)
        self.saved_transcripts = []    # (transcript_id, text) for every save_transcript call

    def load_records(self, ascending=False):
        return self._table

    def get_unique_values(self, column):
        return []

    def load_matching_records(self, column, value, ascending=False):
        return self._table

    def save_transcript(self, transcript_id, text):
        self.saved_transcripts.append((transcript_id, text))
        return True, "Transcript saved."

    def load_transcript(self, transcript_id):
        return self._transcript
