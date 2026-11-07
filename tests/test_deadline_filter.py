# Imports

import os
import sys
import traceback
from datetime import timedelta

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.deadline_filter import DEADLINE_FILTERS, DeadlineFilter

# ------- #
# Helpers
# ------- #

# A Date String (YYYY-MM-DD) that is 'days' Days From Today (Negative = in the Past)
def from_today(days):
    return (pd.Timestamp.today().normalize() + timedelta(days=days)).strftime("%Y-%m-%d")


# A Table with One Report per Deadline Given ("N/A", Text or Days From Today)
def make_table(deadlines):
    values = [from_today(d) if isinstance(d, int) else d for d in deadlines]
    return pd.DataFrame({"reporter_name": [f"R{i}" for i in range(len(values))], "deadline": values})


# The Deadlines (as Given) Kept by One Window
def kept(label, deadlines, **options):
    result = DeadlineFilter(**options).apply(make_table(deadlines), label)
    return [deadlines[int(name[1:])] for name in result.get("reporter_name", [])]

# ----- #
# Tests
# ----- #

def test_deadline_filter_is_a_report_filter_for_the_deadline_column():
    chosen = DeadlineFilter()
    assert isinstance(chosen, ReportFilter)
    assert chosen.column == "deadline"
    assert not DeadlineFilter.__abstractmethods__


def test_options_are_the_fixed_windows_in_order():
    assert DeadlineFilter().options(make_table([1])) == ["Overdue", "Due within 3 days", "Due within 7 days", "All upcoming"]
    assert DeadlineFilter().options(make_table([1])) == list(DEADLINE_FILTERS)


# Overdue is Before Today: Yesterday Counts, Today Does Not
def test_overdue_is_before_today():
    assert kept("Overdue", [-30, -2, -1, 0, 1]) == [-30, -2, -1]


# Due Within 3 Days is Today up to and Including 3 Days Ahead
def test_due_within_3_days_includes_today_and_day_3():
    assert kept("Due within 3 days", [-1, 0, 1, 3, 4]) == [0, 1, 3]


def test_due_within_7_days_includes_today_and_day_7():
    assert kept("Due within 7 days", [-1, 0, 4, 7, 8]) == [0, 4, 7]


def test_all_upcoming_has_no_upper_limit():
    assert kept("All upcoming", [-1, 0, 1, 8, 400]) == [0, 1, 8, 400]


# Reports That Do Not Need a MOM Report, or With a Bad Deadline, Match no Window
def test_na_and_invalid_deadlines_never_match():
    deadlines = ["N/A", "not a date", "", None, 2]
    for label in DEADLINE_FILTERS:
        assert kept(label, deadlines) in ([], [2]), label  # only the real date can ever match
    assert kept("Overdue", deadlines) == []
    assert kept("All upcoming", deadlines) == [2]


def test_unknown_labels_give_an_empty_table():
    table = make_table([0, 3])
    for value in ("Due within 5 days", "overdue", "", "N/A", None):
        assert DeadlineFilter().apply(table, value).empty, value


def test_result_keeps_all_columns_and_resets_the_row_numbers():
    result = DeadlineFilter().apply(make_table(["N/A", 1, -5, 2]), "Due within 3 days")
    assert list(result.columns) == ["reporter_name", "deadline"]
    assert list(result.index) == [0, 1]


def test_custom_windows():
    windows = {"Next 2 days": (0, 2), "Before today": (None, -1)}
    assert DeadlineFilter(windows=windows).options(make_table([1])) == ["Next 2 days", "Before today"]
    assert kept("Next 2 days", [-1, 0, 2, 3], windows=windows) == [0, 2]
    assert kept("Overdue", [0], windows=windows) == []


# Even a Window With no Limits at All Only Keeps Reports That Have a Real Deadline
def test_a_window_without_limits_still_leaves_out_na_and_invalid_deadlines():
    windows = {"Any deadline": (None, None)}
    assert kept("Any deadline", ["N/A", "not a date", "", None, -400, 0, 400], windows=windows) == [-400, 0, 400]


def test_the_windows_given_are_copied_so_changing_them_later_changes_nothing():
    windows = {"Next 2 days": (0, 2)}
    chosen = DeadlineFilter(windows=windows)
    windows["Next 99 days"] = (0, 99)
    assert chosen.options(make_table([1])) == ["Next 2 days"]


# Reports Saved Before the MOM Feature Have no Deadline Column at All
def test_a_table_without_a_deadline_column_gives_an_empty_table_and_no_options():
    table = pd.DataFrame({"reporter_name": ["Ann"]})
    assert DeadlineFilter().apply(table, "Overdue").empty
    assert DeadlineFilter().options(table) == []

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
