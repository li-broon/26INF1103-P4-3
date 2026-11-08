# ------- #
# Imports
# ------- #

from src.logic_manager.scoring.default_scorer import build_default_scorer
from tests.helpers.sample_reports import SampleReports


# Tests for the Importance Score, Using Hardcoded Sample AI Replies (No Live API)
class TestImportanceScorer:

    def setup_method(self):
        self._scorer = build_default_scorer()
        self._samples = SampleReports()

    def _score(self, report: dict) -> float:
        return self._scorer.score(report)

    # Scores are Rounded Floats, so Compare with a Small Tolerance (e.g. 2.725 can Round to 2.72 or 2.73)
    def _assert_close(self, actual: float, expected: float, tolerance: float = 0.01):
        assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"

    # ---------------- Importance Score ---------------- #

    # Check the Score of a Critical Electrical Incident
    def test_critical_electrical_hospitalised(self):
        self._assert_close(self._score(self._samples.load("critical_electrical.json")), 7.4)

    # Check the Score of a Near Miss Slip Incident
    def test_near_miss_slip(self):
        self._assert_close(self._score(self._samples.load("near_miss_slip.json")), 3.3)

    # Check the Score of a Medium Machinery Incident
    def test_medium_machinery_decimal_hours(self):
        self._assert_close(self._score(self._samples.load("medium_machinery.json")), 4.93)

    # Check that the Scores are Ranked by Seriousness
    def test_scores_rank_by_seriousness(self):
        critical = self._score(self._samples.load("critical_electrical.json"))
        medium = self._score(self._samples.load("medium_machinery.json"))
        low = self._score(self._samples.load("near_miss_slip.json"))
        assert critical > medium > low

    # Hospitalised (5) Now Scores Lower than Not Hospitalised (10), by Design
    def test_hospitalisation_lowers_score(self):
        report = self._samples.load("near_miss_slip.json")
        assert self._score(dict(report, hospitalised=True)) < self._score(dict(report, hospitalised=False))

    # The Score Can Never Go Above 10, even for the Worst Possible Report
    def test_score_never_exceeds_cap(self):
        worst = {
            "ai_severity": "Critical", "root_cause_category": "Chemical",
            "hospitalised": True, "is_near_miss": True,
            "lost_time_injury": True, "work_stoppage_hours": 999,
        }
        assert self._score(worst) <= 10

    # Very Long Work Stoppages Stop Adding to the Score after the Hours Cap
    def test_stoppage_hours_are_capped(self):
        report = self._samples.load("near_miss_slip.json")
        assert self._score(dict(report, work_stoppage_hours=24)) == self._score(dict(report, work_stoppage_hours=500))

    # Negative Hours Must Not Lower the Score
    def test_negative_hours_do_not_lower_score(self):
        report = self._samples.load("near_miss_slip.json")
        assert self._score(dict(report, work_stoppage_hours=-5)) == self._score(report)

    # Same Input Gives the Same Score Every Run
    def test_score_is_deterministic(self):
        report = self._samples.load("medium_machinery.json")
        assert len({self._score(report) for _ in range(5)}) == 1

    # ---------------- Bad AI Output ---------------- #

    # Wrong Casing, Text Instead of True/False, Unknown Category, "unknown" Hours: Must Not Crash
    def test_messy_values_do_not_crash(self):
        result = self._score(self._samples.load("messy_values.json"))
        assert isinstance(result, float) and 0 <= result <= 10

    # Hours the AI Could Not Turn into a Number Count as 0
    def test_non_numeric_hours_count_as_zero(self):
        report = self._samples.load("near_miss_slip.json")
        for hours in ("unknown (worker could not say)", None, ""):
            self._assert_close(self._score(dict(report, work_stoppage_hours=hours)), 3.3)

    # Hours Sent as Text ("2.5") Still Count
    def test_numeric_text_hours_are_used(self):
        report = self._samples.load("near_miss_slip.json")
        self._assert_close(self._score(dict(report, work_stoppage_hours="2.5")), 3.43)

    # An Empty Report Scores 0 Instead of Crashing
    def test_empty_report_scores_zero(self):
        assert self._score({}) == 0

    # True/False Sent as Text Must Score the Same as Real Booleans
    def test_text_booleans_are_converted(self):
        report = self._samples.load("near_miss_slip.json")
        assert self._score(dict(report, hospitalised="true")) == self._score(dict(report, hospitalised=True))
        assert self._score(dict(report, hospitalised="false")) == self._score(dict(report, hospitalised=False))
