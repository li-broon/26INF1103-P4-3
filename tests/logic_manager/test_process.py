# ------- #
# Imports
# ------- #

import contextlib
import io
from datetime import datetime, timedelta

from src.logic_manager import LogicManager
from tests.fakes.fake_data_manager import FakeDataManager
from tests.helpers.sample_reports import SampleReports


# Tests for LogicManager.process(): Score, MOM Check and Save, with a Fake Data Manager so data.csv is Never Touched
class TestLogicManager:

    def setup_method(self):
        self._samples = SampleReports()

    # Scores are Rounded Floats, so Compare with a Small Tolerance
    def _assert_close(self, actual: float, expected: float, tolerance: float = 0.01):
        assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"

    # process() Saves Exactly One Record, with the Score and MOM Details Added
    def test_saves_scored_record(self):
        report = self._samples.load("critical_electrical.json")
        data = FakeDataManager()
        LogicManager(data_manager=data).process(report)
        assert len(data.saved_records) == 1
        saved = data.saved_records[0]
        self._assert_close(saved["importance_score"], 7.4)
        assert saved["reporter_name"] == "Ahmad bin Ismail"
        assert saved["mom_reportable"] == "Yes"
        expected_deadline = datetime.strptime(report["incident_date"], "%Y-%m-%d") + timedelta(days=10)
        assert saved["deadline"] == expected_deadline.strftime("%Y-%m-%d")

    # A Minor Incident is Saved as Not Reportable
    def test_saves_non_reportable_incident(self):
        data = FakeDataManager()
        LogicManager(data_manager=data).process(self._samples.load("near_miss_slip.json"))
        saved = data.saved_records[0]
        assert saved["mom_reportable"] == "No"
        assert saved["deadline"] == "N/A"

    # process() Must Not Change the Report it was Given
    def test_does_not_change_original_report(self):
        report = self._samples.load("near_miss_slip.json")
        original = dict(report)
        LogicManager(data_manager=FakeDataManager()).process(report)
        assert report == original
        assert "importance_score" not in report
        assert "mom_reportable" not in report
        assert "deadline" not in report

    # process() Returns the Real Save Result and the Score and MOM Details, for 'io_manager' to Show
    def test_returns_outcome(self):
        outcome = LogicManager(data_manager=FakeDataManager()).process(self._samples.load("critical_electrical.json"))
        assert outcome.saved is True
        assert outcome.message == "Record saved."
        self._assert_close(outcome.importance_score, 7.4)
        assert outcome.mom_reportable == "Yes"

    # A Failed Save is Passed On, Not Hidden
    def test_returns_failed_save(self):
        rejected = (False, "Record rejected: an identical record already exists.")
        outcome = LogicManager(data_manager=FakeDataManager(save_result=rejected)).process(self._samples.load("near_miss_slip.json"))
        assert outcome.saved is False
        assert outcome.message == rejected[1]
        assert outcome.mom_reportable == "No"
        assert outcome.deadline == "N/A"

    # process() Prints Nothing (Printing is 'io_manager's Job, Workers Should Never See Raw JSON)
    def test_prints_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            LogicManager(data_manager=FakeDataManager()).process(self._samples.load("critical_electrical.json"))
        assert output.getvalue() == ""
