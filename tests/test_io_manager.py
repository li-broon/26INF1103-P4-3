# Imports
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

# _fit Tests

# Test that text shorter than the width is padded with spaces
def test_fit_pads_short_text():
    result = io.ReportFormatter().fit_text("Hello", 10)
    assert len(result) == 10
    assert result == "Hello     "
    
# Test that text longer than the width is cut off and appended with an ellipsis.
def test_fit_truncates_long_text():
    result = io.ReportFormatter().fit_text("This is a very long location name", 15)
    assert len(result) == 15
    assert result.endswith("… ")
    assert result == "This is a ver… "

# Test that numeric or boolean inputs are safely converted to strings before fitting.
def test_fit_handles_non_strings():
    result = io.ReportFormatter().fit_text(42.5, 6)
    assert result == "42.5  "

# Menu Tests

# Test that every menu shares the same show() but has its own number of options:
# the same code accepts 3 on the main menu, 5 on the view menu and 4 on the page menu
def test_menus_accept_their_own_last_option():
    menus = [
        (io.MainMenu, 3),
        (io.ViewMenu, 5),
        (io.PageMenu, 4),
        (io.FilterMenu, 8),
    ]
    for menu_class, last_option in menus:
        menu = menu_class(io.Prompter(read=fake_input(str(last_option + 1), str(last_option))))
        with contextlib.redirect_stdout(StringIO()) as out:
            choice = menu.show()
        assert choice == last_option                                     # the last real option is accepted
        assert f"{last_option + 1} is not an option" in out.getvalue()   # one past the end is rejected
 

# Pager Tests

# Test page count when the rows divide exactly: 10 rows at 5 per page = 2 pages
def test_page_count_exact_multiple():
    assert io.Pager(10, page_size=5).page_count() == 2

# Test page count when rows spill onto an extra page: 12 rows at 5 per page = 3 pages
def test_page_count_with_remainder():
    assert io.Pager(12, page_size=5).page_count() == 3

# Test that an empty table still has 1 page, so the screen never shows 'page 1 of 0'
def test_page_count_empty_table():
    assert io.Pager(0).page_count() == 1

# Test that next() moves forward and says it moved
def test_go_next_success():
    pager = io.Pager(9, page_size=3)
    assert pager.next() is True
    assert pager.current_page() == 2

# Test that next() refuses to go past the last page and stays put
def test_go_next_blocked_at_end():
    pager = io.Pager(9, page_size=3)
    pager.next()
    pager.next()                        # now on page 3, the last page
    assert pager.next() is False
    assert pager.current_page() == 3

# Test that previous() moves back and says it moved
def test_go_previous_success():
    pager = io.Pager(9, page_size=3)
    pager.next()                        # page 2
    assert pager.previous() is True
    assert pager.current_page() == 1

# Test that previous() refuses to go before page 1 and stays put
def test_go_previous_blocked_at_start():
    pager = io.Pager(9, page_size=3)
    assert pager.previous() is False
    assert pager.current_page() == 1

# Test that the last page only shows the leftover rows: 7 rows, page 3 = row 7 only
def test_row_range_last_page():
    pager = io.Pager(7, page_size=3)
    pager.next()
    pager.next()
    assert pager.row_range() == (6, 7)



# Report Card Tests
REPORT = {
    "reporter_name": "Ahmad bin Ismail",
    "incident_date": "2026-10-08",
    "hospitalised": True,
    "is_near_miss": False,
    "injury_status": "",
}
SAVED = {"saved": True, "message": "Record saved.", "importance_score": 7.4,
         "mom_reportable": "Yes", "deadline": "2099-12-31"}

# Run fn and return what it printed, with colour codes removed.
def printed(fn, *args):
    with contextlib.redirect_stdout(StringIO()) as out:
        fn(*args)
    return re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())


# Test that a saved report is shown back with the worker's details plus the score and MOM deadline.
def test_confirmation_card_shows_report_and_logic_results():
    text = printed(io._print_save_outcome, REPORT, SAVED)
    assert "Your report has been saved" in text
    assert "Your Saved Report" in text
    assert "Ahmad bin Ismail" in text
    assert re.search(r"Score:\s+7.4", text)
    assert re.search(r"Hospitalised:\s+YES", text)
    assert re.search(r"MOM deadline:\s+2099-12-31", text)
    assert "must be reported to MOM by 2099-12-31" in text
    assert "Injury:" not in text  # Empty fields are skipped

# Test that a failed save shows the reason and no card, so the worker isn't told it was saved
def test_confirmation_card_not_shown_when_save_fails():
    failed = dict(SAVED, saved=False, message="Record rejected: an identical record already exists.")
    text = printed(io._print_save_outcome, REPORT, failed)
    assert "NOT saved" in text
    assert "identical record" in text
    assert "Your Saved Report" not in text
    assert "has been saved" not in text

# Test that a MOM deadline in the past is shown as OVERDUE.
def test_confirmation_card_says_overdue_when_deadline_passed():
    
    text = printed(io._print_save_outcome, REPORT, dict(SAVED, deadline="2022-12-22"))
    assert "OVERDUE" in text
    assert "2022-12-22" in text

# Test that only deadlines before today count as overdue, and bad dates never do.
def test_is_overdue():
    
    today = date(2026, 10, 13)
    assert io._is_overdue("2026-10-12", today) is True
    assert io._is_overdue("2026-10-13", today) is False  # Due today is not overdue yet
    assert io._is_overdue("2026-10-14", today) is False
    assert io._is_overdue("Check incident date", today) is False
    assert io._is_overdue("N/A", today) is False

# Test that a non-MOM report shows N/A as its deadline and no MOM warning.
def test_confirmation_card_no_mom_warning_when_not_reportable():
    
    not_reportable = dict(SAVED, mom_reportable="No", deadline="N/A")
    text = printed(io._print_save_outcome, REPORT, not_reportable)
    assert re.search(r"MOM reportable:\s+No", text)
    assert "must be reported" not in text

# Test that opening a report from the table shows its number and its fields.
def test_full_report_from_table_uses_report_number():
    
    table = pd.DataFrame([REPORT, dict(REPORT, reporter_name="Siti")])
    text = printed(io._print_full_report, table, 2)
    assert "Report #2" in text
    assert "Siti" in text

# Prompter Tests
# Build a fake 'input' that hands back the given answers one at a time
def fake_input(*answers):
    answers = iter(answers)
    return lambda prompt: next(answers)

# Test that blank, text and out-of-range answers are rejected before a valid one is accepted
def test_prompter_ask_number_rejects_bad_input_then_accepts():
    prompter = io.Prompter(read=fake_input("", "abc", "9", "2"))
    with contextlib.redirect_stdout(StringIO()) as out:
        result = prompter.ask_number("Choose (1-3): ", 1, 3)
    assert result == 2
    assert "can't be left blank" in out.getvalue()
    assert "'abc' is not a number" in out.getvalue()
    assert "9 is not an option" in out.getvalue()

    # The user types y, so ask_yes_no should give back True
def test_prompter_yes():
    prompter = io.Prompter(read=fake_input("y"))
    result = prompter.ask_yes_no("Leave?")
    assert result is True

# The user types n, so ask_yes_no should give back False
def test_prompter_no():
    prompter = io.Prompter(read=fake_input("n"))
    result = prompter.ask_yes_no("Leave?")
    assert result is False


# Mini runner
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