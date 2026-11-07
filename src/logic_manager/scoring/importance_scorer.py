from .config import MAX_SCORE


class ImportanceScorer:
    """Adds up the contribution of every factor and caps the result."""

    def __init__(self, factors, max_score=MAX_SCORE):
        self._factors = list(factors)
        self._max_score = max_score

    def score(self, report):
        # An empty report has no data to score (missing fields would otherwise count as False)
        if not report:
            return 0

        total = sum(factor.contribution(report) for factor in self._factors)
        return round(min(total, self._max_score), 2)
