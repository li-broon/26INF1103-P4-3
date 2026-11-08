from src.logic_manager.helpers import to_bool
from src.logic_manager.scoring.factors.score_factor import ScoreFactor


# One weight if the value is true, another if false
class BooleanFactor(ScoreFactor):
    def __init__(self, field, importance, if_true, if_false):
        super().__init__(field, importance)
        self._if_true = if_true
        self._if_false = if_false

    def _weight(self, value):
        return self._if_true if to_bool(value) else self._if_false
