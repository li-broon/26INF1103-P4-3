# Imports

import os
import sys
import traceback

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.score_band_filter import SCORE_THRESHOLDS, ScoreBandFilter

# ------- #
# Helpers
# ------- #

def make_table(scores):
    return pd.DataFrame({"reporter_name": [f"R{i}" for i in range(len(scores))], "importance_score": scores})


# The Scores Kept by One Band
def kept(band, scores, **options):
    return list(ScoreBandFilter(**options).apply(make_table(scores), band)["importance_score"])

# ----- #
# Tests
# ----- #

def test_score_band_filter_is_a_report_filter_for_the_score_column():
    chosen = ScoreBandFilter()
    assert isinstance(chosen, ReportFilter)
    assert chosen.column == "importance_score"
    assert not ScoreBandFilter.__abstractmethods__


def test_options_are_the_fixed_bands():
    assert ScoreBandFilter().options(make_table([5])) == ["0 to under 2", "2 to under 4", "4 to under 6", "6 to under 8", "8+"]


# The Menu Does Not Depend on the Scores Saved
def test_options_do_not_change_with_the_scores():
    assert ScoreBandFilter().options(make_table([1])) == ScoreBandFilter().options(make_table([1, 50, 218.8]))


# A Band Starts at its Own Number and Stops Just Before the Next One
def test_a_band_includes_its_start_and_excludes_its_end():
    scores = [0, 1.99, 2, 3.999, 4, 7.99, 8, 12]
    assert kept("0 to under 2", scores) == [0, 1.99]
    assert kept("2 to under 4", scores) == [2, 3.999]
    assert kept("4 to under 6", scores) == [4]
    assert kept("6 to under 8", scores) == [7.99]
    assert kept("8+", scores) == [8, 12]


# Every Score Lands in Exactly One Band
def test_every_score_is_in_exactly_one_band():
    scores = [0, 0.5, 1.99, 2, 2.5, 3.999, 4, 5, 5.99, 6, 7.99, 8, 9, 60, 218.8]
    table = make_table(scores)
    found = []
    for band in ScoreBandFilter().options(table):
        found += kept(band, scores)
    assert sorted(found) == sorted(scores)


def test_the_top_band_has_no_upper_limit():
    assert kept("8+", [8, 100, 218.8, 1000]) == [8, 100, 218.8, 1000]


def test_reports_without_a_score_are_in_no_band():
    scores = [3, float("nan"), 9]
    for band in ScoreBandFilter().options(make_table(scores)):
        assert not any(pd.isna(score) for score in kept(band, scores))


def test_rows_keep_their_order_and_all_columns():
    table = make_table([5, 4, 5.5, 9])
    result = ScoreBandFilter().apply(table, "4 to under 6")
    assert list(result["importance_score"]) == [5, 4, 5.5]
    assert list(result["reporter_name"]) == ["R0", "R1", "R2"]
    assert list(result.index) == [0, 1, 2]


# Anything That is Not One of the Bands Gives an Empty Table
def test_values_that_are_not_a_band_give_an_empty_table():
    table = make_table([1, 3, 5, 9])
    for value in ("abc", "None", "-1", "9", "3", "7 to under 9", None):
        assert ScoreBandFilter().apply(table, value).empty, value


# A Blank Value Used to Crash With an IndexError, Now it Gives an Empty Table
def test_a_blank_value_gives_an_empty_table_and_does_not_crash():
    table = make_table([1, 3])
    for value in ("", "   "):
        assert ScoreBandFilter().apply(table, value).empty, repr(value)


# The Band Can be Picked From Just its Number, or With Extra Words After it
def test_the_band_start_alone_picks_the_band():
    assert kept("2", [1, 2, 3, 4]) == [2, 3]
    assert kept(" 4 to under 6 ", [3, 4, 5, 6]) == [4, 5]
    assert kept("2 to", [1, 2, 3, 4]) == [2, 3]  # only the number at the start is read


# Different Thresholds Give Different Bands
def test_custom_thresholds_make_custom_bands():
    chosen = ScoreBandFilter(thresholds=["0", "10", "20"])
    assert chosen.options(make_table([5])) == ["0 to under 10", "10 to under 20", "20+"]
    assert kept("10 to under 20", [5, 10, 15, 20, 25], thresholds=["0", "10", "20"]) == [10, 15]
    assert kept("20+", [5, 20, 25], thresholds=["0", "10", "20"]) == [20, 25]


def test_the_thresholds_given_are_copied_so_changing_them_later_changes_nothing():
    thresholds = ["0", "5"]
    chosen = ScoreBandFilter(thresholds=thresholds)
    thresholds.append("99")
    assert chosen.options(make_table([1])) == ["0 to under 5", "5+"]


def test_the_default_thresholds_are_the_shared_constant():
    assert SCORE_THRESHOLDS == ["0", "2", "4", "6", "8"]
    assert ScoreBandFilter().options(make_table([1])) == ["0 to under 2", "2 to under 4", "4 to under 6", "6 to under 8", "8+"]


def test_a_column_that_is_not_in_the_table_gives_an_empty_table_and_no_options():
    table = pd.DataFrame({"reporter_name": ["Ann"]})
    assert ScoreBandFilter().apply(table, "0 to under 2").empty
    assert ScoreBandFilter().options(table) == []

# ------------ #
# Test Runner
# ------------ #

def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
