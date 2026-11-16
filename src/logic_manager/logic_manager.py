from collections.abc import Mapping

from .exceptions import InvalidReportError
from .models.evaluation import Evaluation
from .models.logic_config import LogicConfig
from .models.save_outcome import SaveOutcome
from .rules.mom_reporting_rule import MomReportingRule
from .rules.priority_classifier import PriorityClassifier
from .scoring.importance_scorer import ImportanceScorer


# Applies the business rules to an AI-enriched report and hands it on to be saved.
# - Composition: it builds and owns its scorer, reporting rule and classifier.
# - Aggregation: the DataManager is injected and lives on independently of it.
# - Aggregation: the optional MOM store (any object with save_record) is injected too; MOM reportable reports are copied into it after the main save.
class LogicManager:
    def __init__(self, data_manager, config=None, mom_store=None):
        config = config or LogicConfig()
        self._data_manager = data_manager                       # aggregation (your DataManager, or any object with save_record)
        self._mom_store = mom_store                             # aggregation (the MOM register, or None to skip it)
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
            saved, message = False, f"Could not save report: {error}"

        # Once the main save worked, copy MOM reportable reports into the MOM register
        if saved and evaluation.mom_reportable == "Yes" and self._mom_store is not None:
            message = self._save_to_mom_store(record, message)

        return SaveOutcome(
            saved=saved,
            message=message,
            importance_score=evaluation.importance_score,
            mom_reportable=evaluation.mom_reportable,
            deadline=evaluation.deadline,
            priority=evaluation.priority,
        )

    # Copy one report into the MOM register. The report is already safely saved, so a problem here only adds a note to the message
    def _save_to_mom_store(self, record, message):
        try:
            mom_saved, mom_message = self._mom_store.save_record(record)
        except OSError as error:
            mom_saved, mom_message = False, str(error)
        return message if mom_saved else f"{message} (MOM register not updated: {mom_message})"