# Imports

import inspect
import os
import sys
import tempfile
import traceback
from abc import ABC

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager import CsvRecordStore, DataManager
from src.data_manager.filters.report_filter import ReportFilter

# ------- #
# Helpers
# ------- #

# A Throwaway Filter for Testing the Base Class. It is Made with type() instead of a class statement,
# because Every Class in the Project has its Own File
#   match   : what _match does (default: keep every row)
#   options : fixed choices (default: None, so the base class's own choices are used)
def make_filter(column="location", match=None, options=None):
    members = {"_match": match or (lambda self, table, value: table)}
    if options is not None:
        members["_options"] = lambda self, table: options
    return type("ThrowawayFilter", (ReportFilter,), members)(column)


def make_table():
    return pd.DataFrame({"location": ["Warehouse", "Office", "Office", None, "Dock"],
                         "importance_score": [5, 7, 7, 1, 3]})

# ------------------ #
# The Abstract Class
# ------------------ #

# ReportFilter is an Abstract Class (ABC) and Cannot be Created Directly
def test_report_filter_is_an_abstract_class():
    assert issubclass(ReportFilter, ABC)
    try:
        ReportFilter("location")
    except TypeError:
        return
    raise AssertionError("ReportFilter('location') should raise TypeError")


# The Only Thing a Subclass Must Provide is How a Report Matches the Value
def test_the_only_abstract_method_is_match():
    assert set(ReportFilter.__abstractmethods__) == {"_match"}


# A Subclass that Fills in _match Can be Created
def test_a_subclass_that_fills_in_match_can_be_created():
    assert isinstance(make_filter(), ReportFilter)
    assert not type(make_filter()).__abstractmethods__


# Every Method Has Typed Parameters and a Return Type
def test_every_method_has_type_hints():
    for name in ("__init__", "apply", "options", "_match", "_options"):
        signature = inspect.signature(getattr(ReportFilter, name))
        for parameter in signature.parameters.values():
            if parameter.name != "self":
                assert parameter.annotation is not inspect.Parameter.empty, f"{name}({parameter.name})"
        if name != "__init__":
            assert signature.return_annotation is not inspect.Signature.empty, f"{name} has no return type"

# ------------ #
# The Column
# ------------ #

def test_column_is_kept_and_read_only():
    chosen = make_filter("ai_severity")
    assert chosen.column == "ai_severity"
    try:
        chosen.column = "location"
    except AttributeError:
        return
    raise AssertionError("column should be read only")

# ------------ #
# apply()
# ------------ #

# A Column that is Not in the Table Gives an Empty Table, and _match is Never Called
def test_apply_with_a_missing_column_returns_an_empty_table_without_matching():
    calls = []
    chosen = make_filter("no_such_column", match=lambda self, table, value: calls.append(value))
    result = chosen.apply(make_table(), "x")
    assert isinstance(result, pd.DataFrame) and result.empty
    assert calls == []


# When the Column Exists, apply() Hands the Table and Value to _match and Returns What it Gives Back
def test_apply_returns_what_match_returns():
    seen = []
    answer = pd.DataFrame({"found": [1]})

    def match(self, table, value):
        seen.append((table, value))
        return answer

    table = make_table()
    result = make_filter("location", match=match).apply(table, "Office")
    assert result is answer
    assert seen[0][0] is table and seen[0][1] == "Office"


# Two Different Filters Give Different Results Through the Same apply() Call (Polymorphism)
def test_different_subclasses_behave_differently_through_apply():
    keep_office = make_filter("location", match=lambda self, t, v: t[t["location"] == v].reset_index(drop=True))
    keep_none = make_filter("location", match=lambda self, t, v: t.iloc[0:0])
    for chosen, expected_rows in ((keep_office, 2), (keep_none, 0)):
        assert len(chosen.apply(make_table(), "Office")) == expected_rows

# ------------ #
# options()
# ------------ #

# Default Choices: Each Distinct Saved Value Once, Alphabetical, Missing Values Left Out
def test_default_options_are_the_distinct_values_in_alphabetical_order():
    assert make_filter("location").options(make_table()) == ["Dock", "Office", "Warehouse"]


# Numbers are Offered as Text, the Way the Menu Shows Them
def test_default_options_turn_numbers_into_text():
    assert make_filter("importance_score").options(make_table()) == ["1", "3", "5", "7"]


def test_options_with_a_missing_column_is_an_empty_list():
    assert make_filter("no_such_column").options(make_table()) == []


# A Subclass can Offer Fixed Choices by Overriding _options, and the Missing-Column Check Still Applies
def test_a_subclass_can_offer_fixed_choices():
    fixed = ["Last 7 Days", "Last 30 Days"]
    assert make_filter("location", options=fixed).options(make_table()) == fixed
    assert make_filter("no_such_column", options=fixed).options(make_table()) == []


# The Base Class Gives the Same Menu Values the DataManager Already Offers for an Ordinary Column
def test_default_options_match_the_data_managers_menu_values():
    with tempfile.TemporaryDirectory() as folder:
        dm = DataManager(CsvRecordStore(os.path.join(folder, "data.csv")))
        for name, place, severity in (("Ann", "Office", "High"), ("Bob", "Warehouse", "Low"), ("Cai", "Office", "Medium")):
            assert dm.save_record({"reporter_name": name, "incident_date": "2026-10-01", "importance_score": 5,
                                   "location": place, "ai_severity": severity})[0]
        table = dm.load_records()
        for column in ("location", "ai_severity", "reporter_name"):
            assert make_filter(column).options(table) == dm.get_unique_values(column), column

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
