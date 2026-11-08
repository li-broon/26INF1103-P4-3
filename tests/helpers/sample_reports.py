# ------- #
# Imports
# ------- #

import json
import os


# Loads the Hardcoded AI Replies in tests/samples (Same Format Gemini Returns), so Tests Run Without a Live API
class SampleReports:
    FOLDER = os.path.join(os.path.dirname(__file__), "..", "samples")

    # The "report" Part of a Sample AI Reply (the Part 'ai_manager' Hands to 'logic_manager')
    def load(self, file_name: str) -> dict:
        with open(os.path.join(self.FOLDER, file_name), encoding="utf-8") as file:
            return json.load(file)["report"]
