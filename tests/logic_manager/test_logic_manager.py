# Imports

# Used to Capture Output, to Check the Logic Manager Prints Nothing
import contextlib
import io

# Others
import json
import os
import tempfile
from datetime import datetime, timedelta

# Import the Classes Under Test
from src.logic_manager import Evaluation, InvalidReportError, LogicConfig, LogicManager, SaveOutcome
from src.logic_manager.field_parser import FieldParser
from src.logic_manager.rules.mom_reporting_rule import MomReportingRule
from src.logic_manager.rules.priority_classifier import PriorityClassifier
from src.logic_manager.rules.reporting_rule import ReportingRule
from src.logic_manager.scoring.factors.boolean_factor import BooleanFactor
from src.logic_manager.scoring.factors.choice_factor import ChoiceFactor
from src.logic_manager.scoring.factors.hours_factor import HoursFactor
from src.logic_manager.scoring.factors.score_factor import ScoreFactor
from src.logic_manager.scoring.importance_scorer import ImportanceScorer

# Hardcoded AI Replies
SAMPLES_FOLDER = os.path.join(os.path.dirname(__file__), "..", "samples")

# Helper Classes

# A Fake Data Manager: Remembers What it was Asked to Save, so data.csv is Never Touched
class FakeDataManager:
    def __init__(self, result=(True, "Report saved."), error=None):
        self._result = result
        self._error = error
        self.saved_records = []

    def save_record(self, record):
        if self._error:
            raise self._error
        self.saved_records.append(record)
        return self._result

# Helper Functions

# Load a Sample AI Reply and Return its Dict.
def load_sample_report(file_name):
    with open(os.path.join(SAMPLES_FOLDER, file_name), encoding="utf-8") as file:
        return json.load(file)["report"]

# A Logic Manager Wired to a Fake Data Manager. Returns (manager, fake data manager)
def make_manager(config=None, data_manager=None):
    data_manager = data_manager or FakeDataManager()
    return LogicManager(data_manager, config), data_manager

# Scorer / Rule Built from the Default Configuration
def default_scorer():
    return ImportanceScorer.from_config(LogicConfig())

def default_rule():
    return MomReportingRule.from_config(LogicConfig())

# Score a Sample Report
def score(report):
    return default_scorer().score(report)

# Scores are Rounded Floats, so Compare with a Small Tolerance (e.g. 2.725 can Round to 2.72 or 2.73)
def assert_close(actual, expected, tolerance=0.01):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"

# Check that Running 'action' Raises 'error_type' (Same Idea as pytest.raises, Without Needing pytest)
def assert_raises(error_type, action):
    try:
        action()
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__} to be raised")

# Write Text to a Temporary Config File, Run 'action' with its Path, then Delete it
def with_config_file(text, action):
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "logic_config.json")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return action(path)

# Importance Score Tests

# Check the Score of a Critical Electrical Incident
def test_critical_electrical_hospitalised():
    assert_close(score(load_sample_report("critical_electrical.json")), 7.4)

# Check the Score of a Near Miss Slip Incident
def test_near_miss_slip():
    assert_close(score(load_sample_report("near_miss_slip.json")), 3.3)

# Check the Score of a Medium Machinery Incident
def test_medium_machinery_decimal_hours():
    assert_close(score(load_sample_report("medium_machinery.json")), 4.93)

# Check that the Scores are Ranked by Seriousness
def test_scores_rank_by_seriousness():
    critical = score(load_sample_report("critical_electrical.json"))
    medium = score(load_sample_report("medium_machinery.json"))
    low = score(load_sample_report("near_miss_slip.json"))
    assert critical > medium > low

# Hospitalised (5) Scores Lower than Not Hospitalised (10), by Design (Justify This in the Report!)
def test_hospitalisation_lowers_score():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, hospitalised=True)) < score(dict(report, hospitalised=False))

# The Score Can Never Go Above 10, even for the Worst Possible Report
def test_score_never_exceeds_cap():
    worst = {
        "ai_severity": "Critical", "root_cause_category": "Chemical",
        "hospitalised": True, "is_near_miss": True,
        "lost_time_injury": True, "work_stoppage_hours": 999,
    }
    assert score(worst) <= 10

# Very Long Work Stoppages Stop Adding to the Score after the Hours Cap
def test_stoppage_hours_are_capped():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, work_stoppage_hours=24)) == score(dict(report, work_stoppage_hours=500))

# Negative Hours Must Not Lower the Score
def test_negative_hours_do_not_lower_score():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, work_stoppage_hours=-5)) == score(report)

# Same Input Gives the Same Score Every Run
def test_score_is_deterministic():
    report = load_sample_report("medium_machinery.json")
    assert len({score(report) for _ in range(5)}) == 1

# The Breakdown Explains the Score: One Entry per Field, Adding Up to the Total
def test_breakdown_adds_up_to_score():
    report = load_sample_report("critical_electrical.json")
    breakdown = default_scorer().breakdown(report)
    assert set(breakdown) == set(LogicConfig().field_importance)
    assert_close(sum(breakdown.values()), score(report), tolerance=0.05)

# An Empty Report Has Nothing to Explain
def test_empty_breakdown_for_empty_report():
    assert default_scorer().breakdown({}) == {}

# Bad AI Output Tests

# Wrong Casing, Text Instead of True/False, Unknown Category, "unknown" Hours: Must Not Crash
def test_messy_values_do_not_crash():
    result = score(load_sample_report("messy_values.json"))
    assert isinstance(result, float) and 0 <= result <= 10

# Hours the AI Could Not Turn into a Number Count as 0
def test_non_numeric_hours_count_as_zero():
    report = load_sample_report("near_miss_slip.json")
    for hours in ("unknown (worker could not say)", None, ""):
        assert_close(score(dict(report, work_stoppage_hours=hours)), 3.3)

# Hours Sent as Text ("2.5") Still Count
def test_numeric_text_hours_are_used():
    report = load_sample_report("near_miss_slip.json")
    assert_close(score(dict(report, work_stoppage_hours="2.5")), 3.43)

# An Empty Report Scores 0 Instead of Crashing
def test_empty_report_scores_zero():
    assert score({}) == 0

# True/False Sent as Text Must Score the Same as Real Booleans
def test_text_booleans_are_converted():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, hospitalised="true")) == score(dict(report, hospitalised=True))
    assert score(dict(report, hospitalised="false")) == score(dict(report, hospitalised=False))

# The AI Sending a List or Dict Where a Word was Expected Must Not Crash the Scorer or the MOM Rule
def test_unhashable_values_do_not_crash():
    report = dict(load_sample_report("near_miss_slip.json"), ai_severity=["High"], root_cause_category={"a": 1})
    assert isinstance(score(report), (int, float))
    assert default_rule().check(report)[0] in ("Yes", "No")

# FieldParser Turns Messy AI Values into Clean Ones
def test_field_parser():
    assert FieldParser.to_bool(" TRUE ") is True
    assert FieldParser.to_bool("no") is False
    assert FieldParser.to_bool(None) is False
    assert FieldParser.to_float("3.5") == 3.5
    assert FieldParser.to_float("abc") == 0.0
    assert FieldParser.to_float(None) == 0.0

# "yes" Counts as True, and Numbers that are Not Usable (inf, nan, Huge, Lists) Become 0.0
def test_field_parser_extra_cases():
    assert FieldParser.to_bool("Yes") is True
    assert FieldParser.to_bool(0) is False
    for junk in ("inf", "nan", float("inf"), 10 ** 400, [], {}):
        assert FieldParser.to_float(junk) == 0.0, f"value={junk!r}"
    assert FieldParser.to_float(" 2.5 ") == 2.5

# Score Factor Tests (One Class at a Time)

# ChoiceFactor Looks Values Up, and Unknown Values Score 0
def test_choice_factor():
    factor = ChoiceFactor("ai_severity", 0.5, {"Low": 1, "High": 7})
    assert factor.contribution({"ai_severity": "High"}) == 3.5
    assert factor.contribution({"ai_severity": "Banana"}) == 0
    assert factor.contribution({}) == 0

# ChoiceFactor Ignores Case and Spaces in Text ("low", " HIGH ") but Still Scores Unknown Words 0
def test_choice_factor_ignores_case():
    factor = ChoiceFactor("ai_severity", 0.5, {"Low": 1, "High": 7})
    assert factor.contribution({"ai_severity": "low"}) == 0.5
    assert factor.contribution({"ai_severity": " HIGH "}) == 3.5
    assert factor.contribution({"ai_severity": "Banana"}) == 0

# BooleanFactor Picks the True/False Weight, Including for Text Booleans
def test_boolean_factor():
    factor = BooleanFactor("hospitalised", 0.5, if_true=4, if_false=10)
    assert factor.contribution({"hospitalised": True}) == 2
    assert factor.contribution({"hospitalised": "TRUE"}) == 2
    assert factor.contribution({"hospitalised": False}) == 5
    assert factor.contribution({"hospitalised": "false"}) == 5

# HoursFactor Clamps Between 0 and its Max, and Treats Junk as 0
def test_hours_factor():
    factor = HoursFactor("work_stoppage_hours", 0.5, max_hours=10)
    for hours, expected in ((4, 2), (99, 5), (-3, 0), ("abc", 0), (None, 0)):
        assert factor.contribution({"work_stoppage_hours": hours}) == expected, f"hours={hours!r}"

# An Abstract Class Cannot be Used Directly
def test_score_factor_is_abstract():
    assert_raises(TypeError, lambda: ScoreFactor("field", 1))

# SOLID Evidence Tests

# Every Concrete Factor, Used by the Liskov Test Below
def all_factors():
    return [ChoiceFactor("f", 0.5, {"a": 1}), BooleanFactor("f", 0.5, 5, 10), HoursFactor("f", 0.5, 24)]

# Liskov: Every ScoreFactor Subclass Honours the Same Contract (Any Value In, a Non-Negative Number Out)
def test_every_factor_honours_contract():
    junk_values = [None, "", "abc", [], {}, -1, 0, 10 ** 9, 2.5, True]
    for factor in all_factors():
        for junk in junk_values:
            result = factor.contribution({"f": junk})
            assert isinstance(result, (int, float)), f"{type(factor).__name__} with {junk!r}"
            assert result >= 0, f"{type(factor).__name__} with {junk!r}"

# Fails if a New Factor Class is Added to src/ without Being Added to all_factors() Above
def test_contract_test_covers_every_factor_subclass():
    real = {cls for cls in ScoreFactor.__subclasses__() if cls.__module__.startswith("src.logic_manager")}
    assert real == {type(factor) for factor in all_factors()}

# Liskov: Any ReportingRule Can Stand in for Another (Same Method, Same Return Shape)
def test_every_reporting_rule_honours_contract():
    class AlwaysReport(ReportingRule):
        def check(self, report):
            return "Yes", "2099-01-01"

    for rule in (default_rule(), AlwaysReport()):
        flag, deadline = rule.check({"hospitalised": True, "incident_date": "2026-10-01"})
        assert flag in ("Yes", "No"), type(rule).__name__
        assert isinstance(deadline, str), type(rule).__name__

# Open/Closed: A Brand New Kind of Factor Plugs into the Scorer Without Editing ImportanceScorer
def test_new_factor_type_needs_no_scorer_changes():
    class LengthFactor(ScoreFactor):  # scores the length of the description
        def _weight(self, value):
            return len(value) if isinstance(value, str) else 0

    scorer = ImportanceScorer([LengthFactor("description", 0.5)], max_score=10)
    assert scorer.score({"description": "abcd"}) == 2

# Open/Closed: The Cap Comes from the Scorer's Settings, not Hard-Coded
def test_scorer_cap_is_configurable():
    scorer = ImportanceScorer([ChoiceFactor("ai_severity", 1.0, {"High": 20})], max_score=10)
    assert scorer.score({"ai_severity": "High"}) == 10

# The Interface Cannot be Instantiated, the Concrete Rule Implements it
def test_reporting_rule_is_an_interface():
    assert_raises(TypeError, lambda: ReportingRule())
    assert isinstance(default_rule(), ReportingRule)

# MOM Reporting Tests

# Hospitalised Incidents Must be Reported, 10 Days after the Incident
def test_hospitalised_is_mom_reportable():
    assert default_rule().check({"hospitalised": True, "incident_date": "2026-10-01"}) == ("Yes", "2026-10-11")

# Lost Time Injuries Must be Reported
def test_lost_time_injury_is_mom_reportable():
    assert default_rule().check({"lost_time_injury": True, "incident_date": "2026-10-01"})[0] == "Yes"

# High and Critical Severity Must be Reported, even with No Injury
def test_high_and_critical_severity_are_mom_reportable():
    for severity in ("High", "Critical"):
        assert default_rule().check({"ai_severity": severity, "incident_date": "2026-10-01"})[0] == "Yes", severity

# Minor Incidents are Not Reported and Have No Deadline
def test_minor_incident_is_not_reportable():
    report = {"hospitalised": False, "lost_time_injury": False, "ai_severity": "Low", "incident_date": "2026-10-01"}
    assert default_rule().check(report) == ("No", "N/A")

# "Medium" Severity Alone is Below the Threshold
def test_medium_severity_alone_is_not_reportable():
    assert default_rule().check({"ai_severity": "Medium", "incident_date": "2026-10-01"})[0] == "No"

# "true" as Text Must Still Trigger the Report
def test_text_boolean_triggers_mom_report():
    assert default_rule().check({"hospitalised": "true", "incident_date": "2026-10-01"})[0] == "Yes"

# A Reportable Incident with a Bad Date is Still Flagged
def test_bad_date_is_still_flagged():
    for date in (None, "", "yesterday", "01/10/2026"):
        result = default_rule().check({"hospitalised": True, "incident_date": date})
        assert result == ("Yes", "Check incident date"), f"date={date!r}"

# The AI Writing "critical" or " High " in the Wrong Case Must Not Hide a Reportable Incident
def test_severity_case_does_not_hide_mom_report():
    for severity in ("critical", " HIGH ", "High"):
        assert default_rule().check({"ai_severity": severity, "incident_date": "2026-10-01"})[0] == "Yes", severity

# The Deadline Counts Across a Month End (e.g. 25 Oct + 10 Days = 4 Nov)
def test_deadline_crosses_month_end():
    assert default_rule().check({"hospitalised": True, "incident_date": "2026-10-25"})[1] == "2026-11-04"

# Severities and Deadline Length Come from the Settings, not Hard-Coded
def test_mom_rule_accepts_custom_settings():
    rule = MomReportingRule(severities={"Medium"}, deadline_days=3)
    assert rule.check({"ai_severity": "Medium", "incident_date": "2026-10-01"}) == ("Yes", "2026-10-04")
    assert rule.check({"ai_severity": "Critical", "incident_date": "2026-10-01"})[0] == "No"

# Priority Routing Tests (New Feature)

# Scores Exactly on a Boundary Belong to the Higher Band
def test_priority_band_boundaries():
    classifier = PriorityClassifier.from_config(LogicConfig())
    cases = ((10, "Urgent"), (7.0, "Urgent"), (6.99, "Elevated"), (4.0, "Elevated"), (3.99, "Routine"), (0, "Routine"))
    for value, expected in cases:
        assert classifier.classify(value) == expected, f"score={value}"

# A Score Below Every Band Falls into the Lowest One
def test_negative_score_uses_lowest_band():
    assert PriorityClassifier.from_config(LogicConfig()).classify(-1) == "Routine"

# Bands are Configurable, and No Bands Does Not Crash
def test_custom_and_empty_priority_bands():
    assert PriorityClassifier({"Hot": 5, "Cold": 0}).classify(5) == "Hot"
    assert PriorityClassifier({}).classify(5) == "Unclassified"

# The Sample Incidents are Routed Sensibly
def test_samples_are_routed():
    manager, _ = make_manager()
    assert manager.evaluate(load_sample_report("critical_electrical.json")).priority == "Urgent"
    assert manager.evaluate(load_sample_report("medium_machinery.json")).priority == "Elevated"
    assert manager.evaluate(load_sample_report("near_miss_slip.json")).priority == "Routine"

# Configuration Tests (New Feature)

# The Defaults Reproduce the Original Phase 1 Rules
def test_config_defaults_match_original_rules():
    config = LogicConfig()
    assert config.mom_deadline_days == 10
    assert config.mom_severities == frozenset({"Critical", "High"})
    assert config.max_score == 10

# A JSON File Can Override Settings, and the Rest Keep their Defaults
def test_config_json_overrides_settings():
    text = json.dumps({"mom_deadline_days": 3, "mom_severities": ["Medium"], "priority_bands": {"Red": 5, "Green": 0}})
    config = with_config_file(text, LogicConfig.from_json)
    assert config.mom_deadline_days == 3
    assert config.mom_severities == frozenset({"Medium"})
    assert config.max_score == 10
    evaluation = make_manager(config)[0].evaluate({"ai_severity": "Medium", "incident_date": "2026-10-01"})
    assert (evaluation.mom_reportable, evaluation.deadline) == ("Yes", "2026-10-04")

# Missing File, Corrupt JSON or Wrong Top-Level Type: Defaults, No Crash
def test_config_bad_files_fall_back_to_defaults():
    assert LogicConfig.from_json(os.path.join("does", "not", "exist.json")) == LogicConfig()
    for text in ("{not json", "", "[1, 2]"):
        assert with_config_file(text, LogicConfig.from_json) == LogicConfig(), f"file={text!r}"

# A Value of the Wrong Type is Ignored (Others Still Apply), Unknown Keys are Ignored
def test_config_bad_values_are_ignored():
    text = json.dumps({"mom_deadline_days": "ten", "max_score": 8, "severity_weights": {"Low": "lots"}, "colour": "blue"})
    config = with_config_file(text, LogicConfig.from_json)
    assert config.mom_deadline_days == 10
    assert config.severity_weights == LogicConfig().severity_weights
    assert config.max_score == 8

# Changing a Setting in the Config Changes the Score
def test_config_changes_score():
    report = load_sample_report("near_miss_slip.json")
    assert ImportanceScorer.from_config(LogicConfig(max_score=2)).score(report) == 2

# LogicManager Pipeline Tests

# evaluate() Applies the Rules but Saves Nothing (Separation of Evaluating and Saving)
def test_evaluate_does_not_save():
    manager, data_manager = make_manager()
    evaluation = manager.evaluate(load_sample_report("critical_electrical.json"))
    assert isinstance(evaluation, Evaluation)
    assert data_manager.saved_records == []
    assert_close(evaluation.importance_score, 7.4)
    assert evaluation.mom_reportable == "Yes"

# process() Saves Exactly One Record, with the Score, MOM Details and Priority Added
def test_process_saves_scored_record():
    report = load_sample_report("critical_electrical.json")
    manager, data_manager = make_manager()
    manager.process(report)
    assert len(data_manager.saved_records) == 1
    saved = data_manager.saved_records[0]
    assert_close(saved["importance_score"], 7.4)
    assert saved["reporter_name"] == "Ahmad bin Ismail"
    assert saved["mom_reportable"] == "Yes"
    assert saved["priority"] == "Urgent"
    expected_deadline = datetime.strptime(report["incident_date"], "%Y-%m-%d") + timedelta(days=10)
    assert saved["deadline"] == expected_deadline.strftime("%Y-%m-%d")

# A Minor Incident is Saved as Not Reportable
def test_process_saves_non_reportable_incident():
    manager, data_manager = make_manager()
    manager.process(load_sample_report("near_miss_slip.json"))
    saved = data_manager.saved_records[0]
    assert (saved["mom_reportable"], saved["deadline"]) == ("No", "N/A")

# process() Must Not Change the Report it was Given
def test_process_does_not_change_original_report():
    report = load_sample_report("near_miss_slip.json")
    original = dict(report)
    make_manager()[0].process(report)
    assert report == original
    for added in ("importance_score", "mom_reportable", "deadline", "priority"):
        assert added not in report

# process() Returns a SaveOutcome with the Real Save Result and the Score, MOM Details and Priority
def test_process_returns_outcome():
    outcome = make_manager()[0].process(load_sample_report("critical_electrical.json"))
    assert isinstance(outcome, SaveOutcome)
    assert outcome.saved is True
    assert outcome.message == "Report saved."
    assert_close(outcome.importance_score, 7.4)
    assert (outcome.mom_reportable, outcome.priority) == ("Yes", "Urgent")

# A Failed Save is Passed On, Not Hidden
def test_failed_save_is_passed_on():
    rejected = (False, "Report rejected: an identical report already exists.")
    manager, _ = make_manager(data_manager=FakeDataManager(result=rejected))
    outcome = manager.process(load_sample_report("near_miss_slip.json"))
    assert outcome.saved is False
    assert outcome.message == rejected[1]
    assert (outcome.mom_reportable, outcome.deadline) == ("No", "N/A")

# If the Data Manager Raises (e.g. Disk Full / File Locked) the Outcome Says So Instead of Crashing
def test_data_manager_error_becomes_failed_outcome():
    manager, _ = make_manager(data_manager=FakeDataManager(error=PermissionError("data.csv is locked")))
    outcome = manager.process(load_sample_report("near_miss_slip.json"))
    assert outcome.saved is False
    assert "data.csv is locked" in outcome.message

# Unusable Reports are Rejected Without Touching the Data Manager
def test_invalid_reports_are_rejected():
    for bad in (None, {}, [], "text", 42):
        manager, data_manager = make_manager()
        outcome = manager.process(bad)
        assert outcome.saved is False, f"report={bad!r}"
        assert data_manager.saved_records == [], f"report={bad!r}"
        assert_raises(InvalidReportError, lambda: manager.evaluate(bad))

# The Data Manager is Shared, not Owned (Aggregation): it Outlives Each Logic Manager
def test_data_manager_is_shared_not_owned():
    data_manager = FakeDataManager()
    LogicManager(data_manager).process(load_sample_report("near_miss_slip.json"))
    LogicManager(data_manager).process(load_sample_report("medium_machinery.json"))
    assert len(data_manager.saved_records) == 2

# The Names main.py and the GUI Import from the Package Must Keep Working
def test_package_exports_public_names():
    import src.logic_manager as package
    for name in ("Evaluation", "InvalidReportError", "LogicConfig", "LogicManager", "SaveOutcome"):
        assert hasattr(package, name), name
        assert name in package.__all__, name

# The Manager Prints Nothing (Printing is 'io_manager's Job, Workers Should Never See Raw JSON)
def test_manager_prints_nothing():
    with contextlib.redirect_stdout(io.StringIO()) as output:
        make_manager()[0].process(load_sample_report("critical_electrical.json"))
    assert output.getvalue() == ""


# MOM Register Tests

# A Fake MOM Store: Remembers What it was Asked to Save, so no File is Touched
class FakeMomStore:
    def __init__(self, result=(True, "MOM report saved."), error=None):
        self._result = result
        self._error = error
        self.saved_records = []

    def save_record(self, record):
        if self._error:
            raise self._error
        self.saved_records.append(record)
        return self._result

# A MOM Reportable Report is Copied to the MOM Store After the Main Save, with the Score and Deadline Already Added
def test_mom_reportable_report_is_copied_to_mom_store():
    mom_store = FakeMomStore()
    manager = LogicManager(FakeDataManager(), None, mom_store)
    outcome = manager.process(load_sample_report("critical_electrical.json"))
    assert len(mom_store.saved_records) == 1
    assert mom_store.saved_records[0]["mom_reportable"] == "Yes"
    assert mom_store.saved_records[0]["deadline"] != "N/A"
    assert outcome.message == "Report saved."

# A Report that is Not MOM Reportable Never Reaches the MOM Store
def test_non_reportable_report_is_not_copied_to_mom_store():
    mom_store = FakeMomStore()
    LogicManager(FakeDataManager(), None, mom_store).process(load_sample_report("near_miss_slip.json"))
    assert mom_store.saved_records == []

# If the Main Save Fails the MOM Store is Not Touched (it Must Never Hold a Report data.csv Does Not)
def test_mom_store_is_skipped_when_main_save_fails():
    mom_store = FakeMomStore()
    data_manager = FakeDataManager(result=(False, "Report rejected."))
    outcome = LogicManager(data_manager, None, mom_store).process(load_sample_report("critical_electrical.json"))
    assert outcome.saved is False
    assert mom_store.saved_records == []

# A MOM Store Problem (False Result or OSError) Never Undoes the Main Save; it Only Adds a Note
def test_mom_store_problem_does_not_undo_main_save():
    for mom_store in (FakeMomStore(result=(False, "already there")), FakeMomStore(error=OSError("disk full"))):
        data_manager = FakeDataManager()
        outcome = LogicManager(data_manager, None, mom_store).process(load_sample_report("critical_electrical.json"))
        assert outcome.saved is True
        assert len(data_manager.saved_records) == 1
        assert "MOM register not updated" in outcome.message

# Without a MOM Store, Behaviour is Exactly as Before
def test_no_mom_store_is_fine():
    outcome = make_manager()[0].process(load_sample_report("critical_electrical.json"))
    assert outcome.saved is True and outcome.message == "Report saved."
