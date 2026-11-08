from dataclasses import asdict

from src.logic_manager.adapters.data_manager_adapter import DataManagerAdapter
from src.logic_manager.scoring.default_scorer import build_default_scorer
from src.logic_manager.rules.mom_reporting_rule import MomReportingRule
from src.logic_manager.models.save_outcome import SaveOutcome


# Coordinates scoring, MOM checking and saving. Dependencies are injected.
class LogicManager:

    def __init__(self, data_manager=None, scorer=None, mom_rule=None):
        self._data_manager = data_manager or DataManagerAdapter()
        self._scorer = scorer or build_default_scorer()
        self._mom_rule = mom_rule or MomReportingRule()

    # Score the report, save it, and return the outcome so 'io_manager' can show it
    def process(self, report):
        score = self._scorer.score(report)
        mom_reportable, deadline = self._mom_rule.check(report)

        record = dict(report)
        record["importance_score"] = score
        record["mom_reportable"] = mom_reportable
        record["deadline"] = deadline
        saved, message = self._data_manager.save_record(record)

        return SaveOutcome(
            saved=saved,
            message=message,
            importance_score=score,
            mom_reportable=mom_reportable,
            deadline=deadline,
        )


# Backwards-compatible entry point: same name and dict output as before, so existing callers keep working
def logic(json_result):
    return asdict(LogicManager().process(json_result))
