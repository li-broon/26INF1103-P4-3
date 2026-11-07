# Imports

import os
import sys
import traceback

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.exact_text_filter import ExactTextFilter

# ------- #
# Helpers
# ------- #

def make_table():
    return pd.DataFrame({
        "reporter_name": ["Ann", "Bob", "Cai", "Dee", "Eli"],
        "location": ["Office", "Head Office", "  office ", "Warehouse (Level 2)", None],
        "importance_score": [5, 7, 3, 9, 1],
    })

# ----- #
# Tests
# ----- #

def test_exact_text_filter_is_a_report_filter_for_its_column():
    chosen = ExactTextFilter("location")
    assert isinstance(chosen, ReportFilter)
    assert chosen.column == "location"
    assert not ExactTextFilter.__abstractmethods__


# Matches the Whole Text, Ignoring Upper/Lower Case and Spaces Around it
def test_matches_ignoring_case_and_surrounding_spaces():
    result = ExactTextFilter("location").apply(make_table(), "OFFICE")
    assert list(result["reporter_name"]) == ["Ann", "Cai"]
    result = ExactTextFilter("location").apply(make_table(), "  office  ")
    assert list(result["reporter_name"]) == ["Ann", "Cai"]


# Part of the Text is Not Enough ("Office" Must Not Find "Head Office")
def test_does_not_match_part_of_the_text():
    assert list(ExactTextFilter("location").apply(make_table(), "Office")["reporter_name"]) == ["Ann", "Cai"]
    assert ExactTextFilter("location").apply(make_table(), "Offic").empty


# Brackets and Other Symbols Are Plain Text
def test_symbols_in_the_value_are_plain_text():
    result = ExactTextFilter("location").apply(make_table(), "Warehouse (Level 2)")
    assert list(result["reporter_name"]) == ["Dee"]


def test_numbers_are_compared_as_text():
    assert list(ExactTextFilter("importance_score").apply(make_table(), "7")["reporter_name"]) == ["Bob"]


def test_no_match_gives_an_empty_table():
    assert ExactTextFilter("location").apply(make_table(), "Canteen").empty
    assert ExactTextFilter("location").apply(make_table(), "").empty


# Matching Rows Keep Every Column and are Renumbered from 0
def test_result_keeps_all_columns_and_resets_the_row_numbers():
    result = ExactTextFilter("location").apply(make_table(), "office")
    assert list(result.columns) == list(make_table().columns)
    assert list(result.index) == [0, 1]


def test_the_table_given_is_not_changed():
    table = make_table()
    before = table.copy()
    ExactTextFilter("location").apply(table, "office")
    assert table.equals(before)


def test_a_column_that_is_not_in_the_table_gives_an_empty_table():
    assert ExactTextFilter("no_such_column").apply(make_table(), "x").empty


# The Menu Offers Each Distinct Saved Value (the Default From ReportFilter)
def test_options_are_the_distinct_saved_values():
    assert ExactTextFilter("reporter_name").options(make_table()) == ["Ann", "Bob", "Cai", "Dee", "Eli"]
    assert ExactTextFilter("location").options(make_table()) == ["  office ", "Head Office", "Office", "Warehouse (Level 2)"]

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
