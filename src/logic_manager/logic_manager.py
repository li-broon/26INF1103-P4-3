from collections.abc import Mapping

from .exceptions import InvalidReportError
from .models.evaluation import Evaluation
from .models.logic_config import LogicConfig
from .models.save_outcome import SaveOutcome
from .rules.mom_reporting_rule import MomReportingRule
from .rules.priority_classifier import PriorityClassifier
from .scoring.importance_scorer import ImportanceScorer


# applies the business rules to an AI-enriched report and hands it on to be saved
class LogicManager:
    def __init__(self, data_manager, config=None, mom_store=None):
        config = config or LogicConfig()
        self._data_manager = data_manager                        
        self._mom_store = mom_store                              
        self._scorer = ImportanceScorer.from_config(config)     
        self._reporting_rule = MomReportingRule.from_config(config)
        self._classifier = PriorityClassifier.from_config(config)

    # apply every business rule to the report
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

    # evaluate the report, save it and return the outcome
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

        # once the main save worked copies MOM reportable reports into the MOM register
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

    # copies one report into the MOM register. if the save fails a message will be added to the save message
    def _save_to_mom_store(self, record, message):
        try:
            mom_saved, mom_message = self._mom_store.save_record(record)
        except OSError as error:
            mom_saved, mom_message = False, str(error)
        return message if mom_saved else f"{message} (MOM register not updated: {mom_message})"