from src.logic_manager.scoring.factors.score_factor import ScoreFactor


# Uses the number of hours directly, clamped between 0 and max_hours
class HoursFactor(ScoreFactor):
    def __init__(self, field, importance, max_hours):
        super().__init__(field, importance)
        self._max_hours = max_hours

    def _weight(self, value):
        try:
            hours = float(value or 0)
        except (TypeError, ValueError):
            hours = 0
        return max(0, min(hours, self._max_hours))  # No negatives, and capped
