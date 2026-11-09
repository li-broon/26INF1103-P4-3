from .score_factor import ScoreFactor


# Looks the value up in a dictionary of weights (unknown values score 0)
class ChoiceFactor(ScoreFactor):
    def __init__(self, field, importance, weights):
        super().__init__(field, importance)
        self._weights = weights

    def _weight(self, value):
        try:
            return self._weights.get(value, 0)
        except TypeError:  # unhashable AI output, e.g. a list or dict
            return 0