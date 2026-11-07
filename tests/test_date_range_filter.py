# Imports

import os
import sys
import traceback
from datetime import timedelta

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.date_range_filter import DATE_RANGES, DateRangeFilter

# ------- #
# Helpers
# ------- #

# A Date String (YYYY-MM-DD) that is 'days' Days Before Today
def days_ago(days):
    return (pd.Timestamp.today().normalize() - timedelta(days=days)).strftime("%Y-%m-%d")


# A Table with One Report per Entry, Each Dated that Many Days Ago
def make_table(day_counts):
    return pd.DataFrame({"reporter_name": [f"d{days}" for days in day_counts],
                         "incident_date": [days_ago(days) for days in day_counts]})


def kept(label, day_counts, **options):
    return list(DateRangeFilter(**options).apply(make_table(day_counts), label).get("reporter_name", []))

# ----- #
# Tests
# ----- #

def test_date_range_filter_is_a_report_filter_for_the_date_column():
    chosen = DateRangeFilter()
    assert isinstance(chosen, ReportFilter)
    assert chosen.column == "incident_date"
    assert not DateRangeFilter.__abstractmethods__


def test_options_are_the_fixed_ranges_in_order():
    assert DateRangeFilter().options(make_table([1])) == ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last 365 Days"]
    assert DateRangeFilter().options(make_table([1])) == list(DATE_RANGES)


# Counting Back From Midnight Today, the Seventh Day Back is Still Inside "Last 7 Days"
def test_last_7_days_includes_day_7_and_excludes_day_8():
    assert kept("Last 7 Days", [0, 3, 6, 7, 8, 40, 400]) == ["d0", "d3", "d6", "d7"]


def test_the_other_windows():
    days = [0, 8, 40, 100, 200, 400]
    assert kept("Last 30 Days", days) == ["d0", "d8"]
    assert kept("Last 90 Days", days) == ["d0", "d8", "d40"]
    assert kept("Last 180 Days", days) == ["d0", "d8", "d40", "d100"]
    assert kept("Last 365 Days", days) == ["d0", "d8", "d40", "d100", "d200"]


def test_each_window_edge():
    for label, size in DATE_RANGES.items():
        assert kept(label, [size, size + 1]) == [f"d{size}"], label


# Anything That is Not One of the Labels Gives an Empty Table
def test_unknown_labels_give_an_empty_table():
    table = make_table([0, 3])
    for value in ("Last 12 Years", "last 7 days", "Last 7 Days ", "", "2026-10-09", None):
        assert DateRangeFilter().apply(table, value).empty, value


def test_reports_with_an_invalid_date_are_left_out():
    table = make_table([1])
    table.loc[len(table)] = {"reporter_name": "bad", "incident_date": "not a date"}
    table.loc[len(table)] = {"reporter_name": "none", "incident_date": None}
    assert list(DateRangeFilter().apply(table, "Last 7 Days")["reporter_name"]) == ["d1"]


def test_result_keeps_all_columns_and_resets_the_row_numbers():
    table = make_table([20, 3, 5])
    result = DateRangeFilter().apply(table, "Last 7 Days")
    assert list(result.columns) == ["reporter_name", "incident_date"]
    assert list(result.index) == [0, 1]


def test_custom_ranges():
    ranges = {"Last 2 Days": 2, "Last 10 Days": 10}
    assert DateRangeFilter(ranges=ranges).options(make_table([1])) == ["Last 2 Days", "Last 10 Days"]
    assert kept("Last 2 Days", [0, 2, 3], ranges=ranges) == ["d0", "d2"]
    assert kept("Last 7 Days", [0], ranges=ranges) == []  # a label that is not in this filter's ranges


def test_the_ranges_given_are_copied_so_changing_them_later_changes_nothing():
    ranges = {"Last 2 Days": 2}
    chosen = DateRangeFilter(ranges=ranges)
    ranges["Last 99 Days"] = 99
    assert chosen.options(make_table([1])) == ["Last 2 Days"]


def test_a_column_that_is_not_in_the_table_gives_an_empty_table_and_no_options():
    table = pd.DataFrame({"reporter_name": ["Ann"]})
    assert DateRangeFilter().apply(table, "Last 7 Days").empty
    assert DateRangeFilter().options(table) == []

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
