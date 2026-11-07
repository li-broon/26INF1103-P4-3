# Imports

import os
import sys
import traceback

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.keyword_filter import KeywordFilter

# ------- #
# Helpers
# ------- #

def make_table(places):
    return pd.DataFrame({"reporter_name": [f"R{i}" for i in range(len(places))], "location": places})

# ----- #
# Tests
# ----- #

def test_keyword_filter_is_a_report_filter_for_its_column():
    chosen = KeywordFilter("location")
    assert isinstance(chosen, ReportFilter)
    assert chosen.column == "location"
    assert not KeywordFilter.__abstractmethods__


# Finds Every Report Whose Text Contains the Keyword, in Any Upper/Lower Case
def test_finds_text_containing_the_keyword_ignoring_case():
    table = make_table(["Office", "Head Office", "Warehouse", "OFFICE PARK"])
    result = KeywordFilter("location").apply(table, "office")
    assert list(result["location"]) == ["Office", "Head Office", "OFFICE PARK"]


def test_spaces_around_the_keyword_are_ignored():
    table = make_table(["Office", "Warehouse"])
    assert list(KeywordFilter("location").apply(table, "   warehouse ")["location"]) == ["Warehouse"]


# Symbols Typed by the User Are Plain Text, Not a Pattern
def test_symbols_are_matched_as_plain_text():
    table = make_table(["Warehouse (Level 2)", "Dock [North]", "Gate A+B", "Plant 1.5", "Plant 105"])
    assert list(KeywordFilter("location").apply(table, "(level 2)")["location"]) == ["Warehouse (Level 2)"]
    assert list(KeywordFilter("location").apply(table, "[north]")["location"]) == ["Dock [North]"]
    assert list(KeywordFilter("location").apply(table, "a+b")["location"]) == ["Gate A+B"]
    assert list(KeywordFilter("location").apply(table, "1.5")["location"]) == ["Plant 1.5"]  # "." is not "any character"


# A Half-Typed Bracket Must Not Crash
def test_unbalanced_symbols_do_not_crash():
    table = make_table(["Dock [North]"])
    assert list(KeywordFilter("location").apply(table, "Dock [North")["location"]) == ["Dock [North]"]
    assert KeywordFilter("location").apply(table, "(").empty


def test_blank_keyword_gives_an_empty_table():
    table = make_table(["Office"])
    assert KeywordFilter("location").apply(table, "").empty
    assert KeywordFilter("location").apply(table, "    ").empty


def test_no_match_gives_an_empty_table():
    assert KeywordFilter("location").apply(make_table(["Office"]), "canteen").empty


# Reports With no Location are Never Found
def test_missing_values_are_ignored():
    table = make_table(["Office", None, "Warehouse"])
    assert list(KeywordFilter("location").apply(table, "o")["location"]) == ["Office", "Warehouse"]


def test_result_keeps_all_columns_and_resets_the_row_numbers():
    table = make_table(["Warehouse", "Office", "Head Office"])
    result = KeywordFilter("location").apply(table, "office")
    assert list(result.columns) == ["reporter_name", "location"]
    assert list(result.index) == [0, 1]


def test_a_column_that_is_not_in_the_table_gives_an_empty_table():
    assert KeywordFilter("no_such_column").apply(make_table(["Office"]), "office").empty


# The Menu Still Offers the Distinct Saved Locations (the I/O Side is Unchanged)
def test_options_are_the_distinct_saved_values():
    assert KeywordFilter("location").options(make_table(["Warehouse", "Office", "Office", None])) == ["Office", "Warehouse"]

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
