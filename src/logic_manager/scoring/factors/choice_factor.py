from .score_factor import ScoreFactor


# Looks the value up in a dictionary of weights (unknown values score 0, text is matched ignoring case)
class ChoiceFactor(ScoreFactor):
    def __init__(self, field, importance, weights):
        super().__init__(field, importance)
        self._weights = weights
        self._folded = {key.strip().casefold(): weight for key, weight in weights.items() if isinstance(key, str)}

    def _weight(self, value):
        if isinstance(value, str):
            return self._folded.get(value.strip().casefold(), 0)
        try:
            return self._weights.get(value, 0)
        except TypeError:  # unhashable AI output, e.g. a list or dict
            return 0