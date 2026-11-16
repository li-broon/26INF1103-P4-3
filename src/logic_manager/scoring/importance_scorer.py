from .factors.boolean_factor import BooleanFactor
from .factors.choice_factor import ChoiceFactor
from .factors.hours_factor import HoursFactor


# Adds up the contribution of every factor it owns and caps the result.
class ImportanceScorer:
    def __init__(self, factors, max_score):
        self._factors = list(factors)
        self._max_score = max_score

    # Builds the scorer, and the factor objects it owns, from the configured weights
    @classmethod
    def from_config(cls, config):
        importance = config.field_importance
        return cls(
            factors=[
                ChoiceFactor("ai_severity", importance["ai_severity"], config.severity_weights),
                ChoiceFactor("root_cause_category", importance["root_cause_category"], config.root_cause_weights),
                BooleanFactor("hospitalised", importance["hospitalised"], *config.hospitalised_weights),
                BooleanFactor("is_near_miss", importance["is_near_miss"], *config.near_miss_weights),
                BooleanFactor("lost_time_injury", importance["lost_time_injury"], *config.lost_time_injury_weights),
                HoursFactor("work_stoppage_hours", importance["work_stoppage_hours"], config.max_stoppage_hours),
            ],
            max_score=config.max_score,
        )

    def score(self, report):
        # An empty report has no data to score (missing fields would otherwise count as False)
        if not report:
            return 0
        total = sum(factor.contribution(report) for factor in self._factors)
        return round(min(total, self._max_score), 2)

    # How many points each field added (before the cap), so a score can be explained
    def breakdown(self, report):
        if not report:
            return {}
        return {factor.field: round(factor.contribution(report), 2) for factor in self._factors}