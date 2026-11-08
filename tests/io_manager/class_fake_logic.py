# ------- #
# Imports
# ------- #

from types import SimpleNamespace

# ---- #
# Class
# ---- #

# A fake Logic Manager: always returns the outcome it was given (by default a saved report that is not MOM-reportable)
class FakeLogic:
    def __init__(self, result=None):
        self._result = result or SimpleNamespace(saved=True, message="Record saved.", importance_score=7.4, mom_reportable="No", deadline="N/A")

    def process(self, report):
        return self._result
