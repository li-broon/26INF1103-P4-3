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
    with mock.patch.object(logic_manager, "save_record") as fake_save:
        with contextlib.redirect_stdout(io.StringIO()):  # Hide logic()'s Debug Print
            logic_manager.logic(report)
    return fake_save

# ---------------------- #
# Importance Score Tests
# ---------------------- #

# Check the Score of a Critical Electrical Incident
def test_critical_electrical_hospitalised():
    assert score(load_sample_report("critical_electrical.json")) == 59.8

# Check the Score of a Near Miss Slip Incident
def test_near_miss_slip():
    assert score(load_sample_report("near_miss_slip.json")) == 8.5

# Check the Score of a Medium Machinery Incident
def test_medium_machinery_decimal_hours():
    assert score(load_sample_report("medium_machinery.json")) == 19.0

# Check that the Scores are Ranked by Seriousness
def test_scores_rank_by_seriousness():
    critical = score(load_sample_report("critical_electrical.json"))
    medium = score(load_sample_report("medium_machinery.json"))
    low = score(load_sample_report("near_miss_slip.json"))
    assert critical > medium > low

# Hospitalisation Alone Must Raise the Score
def test_hospitalisation_raises_score():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, hospitalised=True)) > score(report)

# ------------------- #
# Bad AI Output Tests
# ------------------- #

# Wrong Casing, Text Instead of True/False, Unknown Category, "unknown" Hours: Must Not Crash
def test_messy_values_do_not_crash():
    result = score(load_sample_report("messy_values.json"))
    assert isinstance(result, float) and result >= 0

# Hours the AI Could Not Turn into a Number Count as 0
def test_non_numeric_hours_count_as_zero():
    report = load_sample_report("near_miss_slip.json")
    for hours in ("unknown (worker could not say)", None, ""):
        assert score(dict(report, work_stoppage_hours=hours)) == 8.5, f"hours={hours!r}"

# Hours Sent as Text ("2.5") Still Count
def test_numeric_text_hours_are_used():
    report = load_sample_report("near_miss_slip.json")
    assert score(dict(report, work_stoppage_hours="2.5")) == 9.0

# An Empty Report Scores 0 Instead of Crashing
def test_empty_report_scores_zero():
    assert score({}) == 0

# ---------------------- #
# logic() Pipeline Tests
# ---------------------- #

# logic() Saves Exactly One Record, with the Score Added
def test_logic_saves_scored_record():
    fake_save = run_logic_without_saving(load_sample_report("critical_electrical.json"))
    fake_save.assert_called_once()
    saved = fake_save.call_args.args[0]
    assert saved["importance_score"] == 59.8
    assert saved["reporter_name"] == "Ahmad bin Ismail"

# logic() Must Not Change the Report it was Given
def test_logic_does_not_change_original_report():
    report = load_sample_report("near_miss_slip.json")
    original = dict(report)
    run_logic_without_saving(report)
    assert report == original
    assert "importance_score" not in report

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
    