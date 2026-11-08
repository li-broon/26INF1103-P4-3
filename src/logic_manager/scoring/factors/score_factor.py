from abc import ABC, abstractmethod


# Scores one field of a report. Subclasses decide how a value becomes a weight.
class ScoreFactor(ABC):

    def __init__(self, field, importance):
        self._field = field
        self._importance = importance

    # Weighted contribution of this field to the final importance score
    def contribution(self, report):
        return self._weight(report.get(self._field)) * self._importance

    # Turn the raw field value into a weight.
    @abstractmethod
    def _weight(self, value):
        pass
