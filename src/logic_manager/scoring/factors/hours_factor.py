from ...field_parser import FieldParser
from .score_factor import ScoreFactor


# Uses the number of hours directly, clamped between 0 and max_hours
class HoursFactor(ScoreFactor):
    def __init__(self, field, importance, max_hours):
        super().__init__(field, importance)
        self._max_hours = max_hours

    def _weight(self, value):
        return max(0, min(FieldParser.to_float(value), self._max_hours))  # No negatives, and capped