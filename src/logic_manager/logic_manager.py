from collections.abc import Mapping
from dataclasses import asdict

from .exceptions import InvalidReportError
from .models.evaluation import Evaluation
from .models.logic_config import LogicConfig
from .models.save_outcome import SaveOutcome
from .rules.mom_reporting_rule import MomReportingRule
from .rules.priority_classifier import PriorityClassifier
from .scoring.importance_scorer import ImportanceScorer


class LogicManager:
    """Applies the business rules to an AI-enriched report and hands it on to be saved.

    - Composition: it builds and owns its scorer, reporting rule and classifier.
    - Aggregation: the DataManager is injected and lives on independently of it.
    """

    def __init__(self, data_manager, config=None):
        config = config or LogicConfig()
        self._data_manager = data_manager                       # aggregation (your DataManager, or any object with save_record)
        self._scorer = ImportanceScorer.from_config(config)     # composition
        self._reporting_rule = MomReportingRule.from_config(config)
        self._classifier = PriorityClassifier.from_config(config)

    # Apply every business rule to the report. Pure: nothing is saved or changed.
    def evaluate(self, report):
        if not isinstance(report, Mapping) or not report:
            raise InvalidReportError("Report must be a non-empty dictionary.")

        score = self._scorer.score(report)
        mom_reportable, deadline = self._reporting_rule.check(report)
        return Evaluation(
            importance_score=score,
            mom_reportable=mom_reportable,
            deadline=deadline,
            priority=self._classifier.classify(score),
            score_breakdown=self._scorer.breakdown(report),
        )

    # Evaluate the report, save it, and return the outcome so 'io_manager' can show it
    def process(self, report):
        try:
            evaluation = self.evaluate(report)
        except InvalidReportError as error:
            return SaveOutcome(False, str(error), 0, "No", MomReportingRule.NO_DEADLINE, "")

        record = dict(report)
        record.update(evaluation.record_fields())

        try:
            saved, message = self._data_manager.save_record(record)
        except OSError as error:
            saved, message = False, f"Could not save record: {error}"

        return SaveOutcome(
            saved=saved,
            message=message,
            importance_score=evaluation.importance_score,
            mom_reportable=evaluation.mom_reportable,
            deadline=evaluation.deadline,
            priority=evaluation.priority,
        )


# TEMPORARY: old function style entry point still used by main.py and the GUI. Builds a LogicManager that saves
# through the shared functions in src.data_manager, and returns the outcome as a dictionary.
def logic(report):
    from src import data_manager  # Imported here so LogicManager itself never depends on the data manager package

    return asdict(LogicManager(data_manager).process(report))