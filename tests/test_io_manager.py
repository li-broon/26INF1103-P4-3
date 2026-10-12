"""
Tests for io_manager.py

Focuses strictly on pure utility functions (pagination math, text formatting)
to avoid the complexities of mocking terminal standard input/output.
"""

import sys
import os
import re
import traceback
import contextlib
from datetime import date
from io import StringIO
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import io_manager as io


# ------------------ #
# _fit Tests
# ------------------ #

def test_fit_pads_short_text():
    """Test that text shorter than the width is padded with spaces."""
    result = io._fit("Hello", 10)
    assert len(result) == 10
    assert result == "Hello     "

def test_fit_truncates_long_text():
    """Test that text longer than the width is cut off and appended with an ellipsis."""
    result = io._fit("This is a very long location name", 15)
    assert len(result) == 15
    assert result.endswith("… ")
    assert result == "This is a ver… "

def test_fit_handles_non_strings():
    """Test that numeric or boolean inputs are safely converted to strings before fitting."""
    result = io._fit(42.5, 6)
    assert result == "42.5  "


# ------------------ #
# Pagination Tests
# ------------------ #

def test_page_count_exact_multiple():
    """Test page calculation when the row count perfectly divides by PAGE_SIZE."""
    # Assuming PAGE_SIZE is 5, a 10-row table should be exactly 2 pages
    dummy_table = pd.DataFrame([{"id": i} for i in range(10)])
    assert io._page_count(dummy_table) == -(-10 // io.PAGE_SIZE)

def test_page_count_with_remainder():
    """Test page calculation when the row count spills over into a new page."""
    # A 12-row table should be 3 pages
    dummy_table = pd.DataFrame([{"id": i} for i in range(12)])
    assert io._page_count(dummy_table) == -(-12 // io.PAGE_SIZE)

def test_page_count_empty_table():
    """Test that an empty table still registers as at least 1 page to prevent UI crashes."""
    dummy_table = pd.DataFrame()
    assert io._page_count(dummy_table) == 1

def test_go_next_success():
    """Test that page increments correctly when not on the last page."""
    new_page, changed = io._go_next(page=1, pages=3)
    assert new_page == 2
    assert changed is True

def test_go_next_blocked_at_end():
    """Test that scrolling past the last page is blocked."""
    new_page, changed = io._go_next(page=3, pages=3)
    assert new_page == 3
    assert changed is False

def test_go_previous_success():
    """Test that page decrements correctly."""
    new_page, changed = io._go_previous(page=2)
    assert new_page == 1
    assert changed is True

def test_go_previous_blocked_at_start():
    """Test that scrolling into negative pages is blocked."""
    new_page, changed = io._go_previous(page=1)
    assert new_page == 1
    assert changed is False


# ------------------ #
# Report Card Tests
# ------------------ #

REPORT = {
    "reporter_name": "Ahmad bin Ismail",
    "incident_date": "2026-10-08",
    "hospitalised": True,
    "is_near_miss": False,
    "injury_status": "",
}
SAVED = {"saved": True, "message": "Record saved.", "importance_score": 7.4,
         "mom_reportable": "Yes", "deadline": "2099-12-31"}

def printed(fn, *args):
    """Run fn and return what it printed, with colour codes removed."""
    with contextlib.redirect_stdout(StringIO()) as out:
        fn(*args)
    return re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())

def test_confirmation_card_shows_report_and_logic_results():
    """Test that a saved report is shown back with the worker's details plus the score and MOM deadline."""
    text = printed(io._print_save_outcome, REPORT, SAVED)
    assert "Your report has been saved" in text
    assert "Your Saved Report" in text
    assert "Ahmad bin Ismail" in text
    assert re.search(r"Score:\s+7.4", text)
    assert re.search(r"Hospitalised:\s+YES", text)
    assert re.search(r"MOM deadline:\s+2099-12-31", text)
    assert "must be reported to MOM by 2099-12-31" in text
    assert "Injury:" not in text  # Empty fields are skipped

def test_confirmation_card_not_shown_when_save_fails():
    """Test that a failed save shows the reason and no card, so the worker isn't told it was saved."""
    failed = dict(SAVED, saved=False, message="Record rejected: an identical record already exists.")
    text = printed(io._print_save_outcome, REPORT, failed)
    assert "NOT saved" in text
    assert "identical record" in text
    assert "Your Saved Report" not in text
    assert "has been saved" not in text

def test_confirmation_card_says_overdue_when_deadline_passed():
    """Test that a MOM deadline in the past is shown as OVERDUE."""
    text = printed(io._print_save_outcome, REPORT, dict(SAVED, deadline="2022-12-22"))
    assert "OVERDUE" in text
    assert "2022-12-22" in text

def test_is_overdue():
    """Test that only deadlines before today count as overdue, and bad dates never do."""
    today = date(2026, 10, 13)
    assert io._is_overdue("2026-10-12", today) is True
    assert io._is_overdue("2026-10-13", today) is False  # Due today is not overdue yet
    assert io._is_overdue("2026-10-14", today) is False
    assert io._is_overdue("Check incident date", today) is False
    assert io._is_overdue("N/A", today) is False

def test_confirmation_card_no_mom_warning_when_not_reportable():
    """Test that a non-MOM report shows N/A as its deadline and no MOM warning."""
    not_reportable = dict(SAVED, mom_reportable="No", deadline="N/A")
    text = printed(io._print_save_outcome, REPORT, not_reportable)
    assert re.search(r"MOM reportable:\s+No", text)
    assert "must be reported" not in text

def test_full_report_from_table_uses_report_number():
    """Test that opening a report from the table shows its number and its fields."""
    table = pd.DataFrame([REPORT, dict(REPORT, reporter_name="Siti")])
    text = printed(io._print_full_report, table, 2)
    assert "Report #2" in text
    assert "Siti" in text


# ------------------ #
# Mini runner
# ------------------ #
def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except AssertionError as e:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n      {e}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
            
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures

if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)