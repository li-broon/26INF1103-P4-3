from abc import ABC, abstractmethod


class ScoreFactor(ABC):
    """Scores one field of a report. Subclasses decide how a value becomes a weight."""

    def __init__(self, field, importance):
        self._field = field
        self._importance = importance

    # Weighted contribution of this field to the final importance score
    def contribution(self, report):
        return self._weight(report.get(self._field)) * self._importance

    @abstractmethod
    def _weight(self, value):
        """Turn the raw field value into a weight."""
