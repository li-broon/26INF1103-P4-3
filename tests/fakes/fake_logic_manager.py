# ------- #
# Imports
# ------- #

from src.logic_manager import SaveOutcome


# A Fake Logic Manager: Always Returns the Outcome it was Given (a Saved, Non-MOM Report by Default)
class FakeLogicManager:
    def __init__(self, result: SaveOutcome | None = None):
        self._result = result or SaveOutcome(saved=True, message="Record saved.", importance_score=7.4,
                                             mom_reportable="No", deadline="N/A")

    def process(self, report: dict) -> SaveOutcome:
        return self._result
