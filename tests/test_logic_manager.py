# ------- #
# Imports
# ------- #

# Used to Capture logic()'s Debug Print, so Test Output is Clean
import contextlib
import io

# Used to Mock logic_manager.save_record(), so data.csv is Never Touched
from unittest import mock

# Others
import json
import os
import sys
import traceback
from datetime import datetime, timedelta

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")) # Let 'src' be Imported
from src import logic_manager

# ------------ #
# Test Config.
# ------------ #

# Hardcoded AI Replies
SAMPLES_FOLDER = "tests/samples"

# ---------------- #
# Helper Functions
# ---------------- #

# Load a Sample AI Reply and Return its Dict.
def load_sample_report(file_name):
    with open(os.path.join(SAMPLES_FOLDER, file_name), encoding="utf-8") as file:
        return json.load(file)["report"]

# Score a Sample Report
def score(report):
    return logic_manager._calculate_importance_score(report)

# Run logic() with save_record Replaced by a Fake, so data.csv is Never Touched. Returns the Fake.
def run_logic_without_saving(report):
    return run_logic_with_save_result(report)[0]

# Same, but the Fake save_record Returns 'save_result'. Returns (Fake, What logic() Returned).
def run_logic_with_save_result(report, save_result=(True, "Record saved.")):
    with mock.patch.object(logic_manager, "save_record", return_value=save_result) as fake_save:
        with contextlib.redirect_stdout(io.StringIO()):  # Hide logic()'s Debug Print
            outcome = logic_manager.logic(report)
    return fake_save, outcome

# Scores are Rounded Floats, so Compare with a Small Tolerance (e.g. 2.725 can Round to 2.72 or 2.73)
def assert_close(actual, expected, tolerance=0.01):
    assert abs(actual - expected) <= tolerance, f"expected {expected}, got {actual}"

# ---------------------- #
# Importance Score Tests
# ---------------------- #
# Check the Score of a Critical Electrical Incident
# Critical 10x0.30 + Electrical 8x0.20 + Hospitalised 5x0.20 + Lost Time 8x0.20 + 4 Hours x0.05
def test_critical_electrical_hospitalised():
    assert_close(score(load_sample_report("critical_electrical.json")), 7.4)

# Check the Score of a Near Miss Slip Incident
# Low 1x0.30 + Slip or Trip 3x0.20 + Not Hospitalised 10x0.20 + Near Miss 2x0.10 + No Lost Time 1x0.20
def test_near_miss_slip():
    assert_close(score(load_sample_report("near_miss_slip.json")), 3.3)

# Check the Score of a Medium Machinery Incident
# Medium 4x0.30 + Machinery 7x0.20 + Not Hospitalised 10x0.20 + No Lost Time 1x0.20 + 2.5 Hours x0.05
def test_medium_machinery_decimal_hours():
    assert_close(score(load_sample_report("medium_machinery.json")), 4.93)

# Check that the Scores are Ranked by Seriousness
def test_scores_rank_by_seriousness():
    critical = score(load_sample_report("critical_electrical.json"))
    medium = score(load_sample_report("medium_machinery.json"))
    low = score(load_sample_report("near_miss_slip.json"))
    assert critical > medium > low

# Hospitalised (5) Now Scores Lower than Not Hospitalised (10), by Design
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
# ------------------- #
# Bad AI Output Tests
# ------------------- #

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

# ----------------- #
# MOM Reporting Tests
# ----------------- #

# Hospitalised Incidents Must be Reported, 10 Days after the Incident
def test_hospitalised_is_mom_reportable():
    flag, deadline = logic_manager._check_mom_reporting(
        {"hospitalised": True, "incident_date": "2026-10-01"}
    )
    assert flag == "Yes"
    assert deadline == "2026-10-11"

# Lost Time Injuries Must be Reported
def test_lost_time_injury_is_mom_reportable():
    flag, _ = logic_manager._check_mom_reporting(
        {"lost_time_injury": True, "incident_date": "2026-10-01"}
    )
    assert flag == "Yes"

# Critical Severity Must be Reported, even with No Injury
def test_critical_severity_is_mom_reportable():
    flag, _ = logic_manager._check_mom_reporting(
        {"ai_severity": "Critical", "incident_date": "2026-10-01"}
    )
    assert flag == "Yes"

# Minor Incidents are Not Reported and Have No Deadline
def test_minor_incident_is_not_reportable():
    flag, deadline = logic_manager._check_mom_reporting(
        {"hospitalised": False, "lost_time_injury": False,
         "ai_severity": "Low", "incident_date": "2026-10-01"}
    )
    assert (flag, deadline) == ("No", "N/A")

# "true" as Text Must Still Trigger the Report
def test_text_boolean_triggers_mom_report():
    flag, _ = logic_manager._check_mom_reporting(
        {"hospitalised": "true", "incident_date": "2026-10-01"}
    )
    assert flag == "Yes"

# A Reportable Incident with a Bad Date is Still Flagged
def test_bad_date_is_still_flagged():
    for date in (None, "", "yesterday", "01/10/2026"):
        flag, deadline = logic_manager._check_mom_reporting(
            {"hospitalised": True, "incident_date": date}
        )
        assert flag == "Yes", f"date={date!r}"
        assert deadline == "Check incident date", f"date={date!r}"

# The Deadline Counts Across a Month End (e.g. 25 Oct + 10 Days = 4 Nov)
def test_deadline_crosses_month_end():
    _, deadline = logic_manager._check_mom_reporting(
        {"hospitalised": True, "incident_date": "2026-10-25"}
    )
    assert deadline == "2026-11-04"

# ---------------------- #
# logic() Pipeline Tests
# ---------------------- #

# logic() Saves Exactly One Record, with the Score and MOM Details Added
def test_logic_saves_scored_record():
    report = load_sample_report("critical_electrical.json")
    fake_save = run_logic_without_saving(report)
    fake_save.assert_called_once()
    saved = fake_save.call_args.args[0]
    assert_close(saved["importance_score"], 7.4)
    assert saved["reporter_name"] == "Ahmad bin Ismail"
    assert saved["mom_reportable"] == "Yes"
    expected_deadline = datetime.strptime(report["incident_date"], "%Y-%m-%d") + timedelta(days=10)
    assert saved["deadline"] == expected_deadline.strftime("%Y-%m-%d")

# A Minor Incident is Saved as Not Reportable
def test_logic_saves_non_reportable_incident():
    fake_save = run_logic_without_saving(load_sample_report("near_miss_slip.json"))
    saved = fake_save.call_args.args[0]
    assert saved["mom_reportable"] == "No"
    assert saved["deadline"] == "N/A"

# logic() Must Not Change the Report it was Given
def test_logic_does_not_change_original_report():
    report = load_sample_report("near_miss_slip.json")
    original = dict(report)
    run_logic_without_saving(report)
    assert report == original
    assert "importance_score" not in report
    assert "mom_reportable" not in report
    assert "deadline" not in report

# logic() Returns the Real Save Result and the Score and MOM Details, for 'io_manager' to Show
def test_logic_returns_outcome():
    _, outcome = run_logic_with_save_result(load_sample_report("critical_electrical.json"))
    assert outcome["saved"] is True
    assert outcome["message"] == "Record saved."
    assert_close(outcome["importance_score"], 7.4)
    assert outcome["mom_reportable"] == "Yes"

# A Failed Save is Passed On, Not Hidden
def test_logic_returns_failed_save():
    rejected = (False, "Record rejected: an identical record already exists.")
    _, outcome = run_logic_with_save_result(load_sample_report("near_miss_slip.json"), rejected)
    assert outcome["saved"] is False
    assert outcome["message"] == rejected[1]
    assert outcome["mom_reportable"] == "No"
    assert outcome["deadline"] == "N/A"

# Same Input Gives the Same Score Every Run
def test_score_is_deterministic():
    report = load_sample_report("medium_machinery.json")
    assert len({score(report) for _ in range(5)}) == 1

# ---- #
# Main
# ---- #

# Run Every Function Named test_*, Print PASS/FAIL for Each, and Return how Many Failed
def run_all_tests():
    tests = [func for name, func in globals().items() if name.startswith("test_") and callable(func)] # globals() is a Dict of All Functions in this File
    failed = 0

    for test in tests:
        
        # Run the Test and Print PASS if it Succeeds
        try:
            test()
            print(f"\033[32mPASS\033[0m  {test.__name__}")
            
        # Handle Any Exceptions and Print FAIL & the Traceback
        except Exception:
            failed += 1
            print(f"\033[31mFAIL\033[0m  {test.__name__}")
            print(traceback.format_exc())

    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    return failed

if __name__ == "__main__":
    sys.exit(1 if run_all_tests() else 0)