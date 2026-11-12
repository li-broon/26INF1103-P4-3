# Imports
import contextlib
import re
from datetime import date
from io import StringIO
from types import SimpleNamespace

import pandas as pd

from src import io_manager as io
from src.io_manager.manager import IOManager
from tests.io_manager.class_fake_ai import FakeAI
from tests.io_manager.class_fake_charts import FakeCharts
from tests.io_manager.class_fake_data import FakeData
from tests.io_manager.class_fake_logic import FakeLogic
from tests.io_manager.class_no_key_ai import NoKeyAI
from tests.io_manager.class_scripted_input import ScriptedInput

#_fit Tests

#Test that text shorter than the width is padded with spaces
def test_fit_pads_short_text():
    result = io.ReportFormatter().fit_text("Hello", 10)
    assert len(result) == 10
    assert result == "Hello     "
    
#Test that text longer than the width is cut off and appended with an ellipsis.
def test_fit_truncates_long_text():
    result = io.ReportFormatter().fit_text("This is a very long location name", 15)
    assert len(result) == 15
    assert result.endswith("… ")
    assert result == "This is a ver… "

#Test that numeric or boolean inputs are safely converted to strings before fitting.
def test_fit_handles_non_strings():
    result = io.ReportFormatter().fit_text(42.5, 6)
    assert result == "42.5  "

#Test that Menu is abstract: Python must refuse to create a plain Menu
def test_menu_is_abstract():
    try:
        io.Menu(io.Prompter())
        assert False, "Menu should be abstract"
    except TypeError:
        pass

#Menu Tests
#Every menu shares show() but has its own options: the same code accepts 3 on the main menu, 5 on the view menu and 4 on the page menu
def test_menus_accept_their_own_last_option():
    menus = [(io.MainMenu, 4), (io.ViewMenu, 5), (io.PageMenu, 4), (io.FilterMenu, 8)]
    for menu_class, last_option in menus:
        menu = menu_class(io.Prompter(read=ScriptedInput(str(last_option + 1), str(last_option)).read))
        with contextlib.redirect_stdout(StringIO()) as out:
            choice = menu.show()
        assert choice == last_option                                     # the last real option is accepted
        assert f"{last_option + 1} is not an option" in out.getvalue()   # one past the end is rejected
 

#Pager Tests

#Test page count when the rows divide exactly: 10 rows at 5 per page = 2 pages
def test_page_count_exact_multiple():
    assert io.Pager(10, page_size=5).page_count() == 2

#Test page count when rows spill onto an extra page: 12 rows at 5 per page = 3 pages
def test_page_count_with_remainder():
    assert io.Pager(12, page_size=5).page_count() == 3

#Test that an empty table still has 1 page, so the screen never shows 'page 1 of 0'
def test_page_count_empty_table():
    assert io.Pager(0).page_count() == 1

#Test that next() moves forward and says it moved
def test_go_next_success():
    pager = io.Pager(9, page_size=3)
    assert pager.next() is True
    assert pager.current_page() == 2

#Test that next() refuses to go past the last page and stays put
def test_go_next_blocked_at_end():
    pager = io.Pager(9, page_size=3)
    pager.next()
    pager.next()                        # now on page 3, the last page
    assert pager.next() is False
    assert pager.current_page() == 3

#Test that previous() moves back and says it moved
def test_go_previous_success():
    pager = io.Pager(9, page_size=3)
    pager.next()                        # page 2
    assert pager.previous() is True
    assert pager.current_page() == 1

#Test that previous() refuses to go before page 1 and stays put
def test_go_previous_blocked_at_start():
    pager = io.Pager(9, page_size=3)
    assert pager.previous() is False
    assert pager.current_page() == 1

#Test that the last page only shows the leftover rows: 7 rows, page 3 = row 7 only
def test_row_range_last_page():
    pager = io.Pager(7, page_size=3)
    pager.next()
    pager.next()
    assert pager.row_range() == (6, 7)


#Report Card Tests
REPORT = {
    "reporter_name": "Ahmad bin Ismail",
    "incident_date": "2026-10-08",
    "hospitalised": True,
    "is_near_miss": False,
    "injury_status": "",
}

#A fake SaveOutcome: the same fields as the Logic Manager's real one
SAVED = SimpleNamespace(saved=True, message="Record saved.", importance_score=7.4,
                        mom_reportable="Yes", deadline="2099-12-31")

#A copy of SAVED with some fields changed, e.g. outcome(deadline="2022-12-22")
def outcome(**changes):
    return SimpleNamespace(**{**vars(SAVED), **changes})

card_view = io.ReportCardView(io.ReportFormatter())

#Run fn and return what it printed, with colour codes removed.
def printed(fn, *args):
    with contextlib.redirect_stdout(StringIO()) as out:
        fn(*args)
    return re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())


#Test that a saved report is shown back with the worker's details plus the score and MOM deadline.
def test_confirmation_card_shows_report_and_logic_results():
    text = printed(card_view.show_save_outcome, REPORT, SAVED)
    assert "Your report has been saved" in text
    assert "Your Saved Report" in text
    assert "Ahmad bin Ismail" in text
    assert re.search(r"Score:\s+7.4", text)
    assert re.search(r"Hospitalised:\s+YES", text)
    assert re.search(r"MOM deadline:\s+2099-12-31", text)
    assert "must be reported to MOM by 2099-12-31" in text
    assert "Injury:" not in text  # Empty fields are skipped

#Test that a failed save shows the reason and no card, so the worker isn't told it was saved
def test_confirmation_card_not_shown_when_save_fails():
    failed = outcome(saved=False, message="Record rejected: an identical record already exists.")
    text = printed(card_view.show_save_outcome, REPORT, failed)
    assert "NOT saved" in text
    assert "identical record" in text
    assert "Your Saved Report" not in text
    assert "has been saved" not in text

#Test that a MOM deadline in the past is shown as OVERDUE.
def test_confirmation_card_says_overdue_when_deadline_passed():
    text = printed(card_view.show_save_outcome, REPORT, outcome(deadline="2022-12-22"))
    assert "OVERDUE" in text
    assert "2022-12-22" in text

#Test that only deadlines before today count as overdue, and bad dates never do.
def test_is_overdue():
    today = date(2026, 10, 13)
    assert card_view._is_overdue("2026-10-12", today) is True
    assert card_view._is_overdue("2026-10-13", today) is False  # Due today is not overdue yet
    assert card_view._is_overdue("2026-10-14", today) is False
    assert card_view._is_overdue("Check incident date", today) is False
    assert card_view._is_overdue("N/A", today) is False

#Test that a non-MOM report shows N/A as its deadline and no MOM warning.
def test_confirmation_card_no_mom_warning_when_not_reportable():
    text = printed(card_view.show_save_outcome, REPORT, outcome(mom_reportable="No", deadline="N/A"))
    assert re.search(r"MOM reportable:\s+No", text)
    assert "must be reported" not in text

#Test that opening a report from the table shows its number and its fields.
def test_full_report_from_table_uses_report_number():
    table = pd.DataFrame([REPORT, dict(REPORT, reporter_name="Siti")])
    text = printed(card_view.show_from_table, table, 2)
    assert "Report #2" in text
    assert "Siti" in text

#Test that one page shows the header, 3 reports, and the footer exactly once
def test_table_view_shows_one_page():
    table = pd.DataFrame([REPORT] * 4)
    view = io.ReportTableView(io.ReportFormatter())
    text = printed(view.show, table, "Saved Reports", io.Pager(len(table), page_size=3))
    assert "Score" in text and "Severity" in text
    assert text.count("Ahmad bin Ismail") == 3
    assert text.count("Page 1 of 2") == 1

#IOManager Tests (fake managers: no API key, no CSV file)


#One AI reply; by default a normal, unfinished one with no error
def reply(**fields):
    base = dict(reply="Thanks, tell me more.", is_complete=False, report={},
                error=None, error_code=None, error_status=None)
    return SimpleNamespace(**{**base, **fields})

#Build an IOManager whose "user" types the given answers in order
def io_manager(ai=None, logic=None, data=None, charts=None, answers=()):
    return IOManager(ai or FakeAI([]), logic or FakeLogic(), data or FakeData(pd.DataFrame()), charts or FakeCharts(),
                     read=ScriptedInput(*answers).read)


#Menu 1 (chat) -> one message -> report complete -> "n" to viewing reports -> 3 (exit)
def test_chatbot_saves_a_complete_report():
    manager = io_manager(ai=FakeAI([reply(is_complete=True, report=REPORT)]), answers=["1", "I cut my hand", "n", "4"])
    text = printed(manager.run)
    assert "Your report has been saved" in text
    assert "Ahmad bin Ismail" in text
    assert "Goodbye" in text

#Typing quit asks to confirm, and nothing is saved
def test_chatbot_quit_asks_to_confirm():
    text = printed(io_manager(answers=["1", "quit", "y", "4"]).run)
    assert "Report cancelled. Nothing was saved." in text

#An error with no code must not tell the worker to resend
def test_chatbot_error_without_code_does_not_say_resend():
    manager = io_manager(ai=FakeAI([reply(error="Report not finished")]), answers=["1", "hi", "quit", "y", "4"])
    text = printed(manager.run)
    assert "couldn't be finished" in text
    assert "resend" not in text

#A real API error (it has a code) does tell the worker to resend
def test_chatbot_api_error_says_resend():
    manager = io_manager(ai=FakeAI([reply(error="Too many requests", error_code=429, error_status="RESOURCE_EXHAUSTED")]),
                         answers=["1", "hi", "quit", "y", "4"])
    text = printed(manager.run)
    assert "429" in text
    assert "resend" in text

#A failed save is reported, and the worker is not told it was saved
def test_chatbot_save_failure_is_reported():
    manager = io_manager(ai=FakeAI([reply(is_complete=True, report=REPORT)]),
                         logic=FakeLogic(outcome(saved=False, message="Disk full")),
                         answers=["1", "I fell", "n", "4"])
    text = printed(manager.run)
    assert "NOT saved" in text
    assert "has been saved" not in text

#Without an API key, the chatbot explains why and returns to the menu instead of crashing
def test_chatbot_without_api_key():
    text = printed(io_manager(ai=NoKeyAI(), answers=["1", "4"]).run)
    assert "GEMINI_API_KEY is missing" in text
    assert "Goodbye" in text

#Viewing reports with none saved says so instead of showing an empty table
def test_view_reports_when_none_saved():
    text = printed(io_manager(answers=["2", "4"]).run)
    assert "No incident reports have been saved yet" in text

#Menu 3 (charts) -> chart 2 -> "n" saves it as a picture -> 4 (exit)
def test_charts_saved_as_picture():
    charts = FakeCharts()
    text = printed(io_manager(charts=charts, answers=["3", "2", "n", "4"]).run)
    assert charts.shown == [("language", "data/chart_language.png")]
    assert "Chart saved to data/chart_language.png" in text

#The extra last option draws every chart on one page; "y" opens it in a window
def test_charts_all_in_a_window():
    charts = FakeCharts()
    printed(io_manager(charts=charts, answers=["3", "3", "y", "4"]).run)
    assert charts.shown == [("all", None)]

#Choosing Back draws nothing
def test_charts_back_draws_nothing():
    charts = FakeCharts()
    printed(io_manager(charts=charts, answers=["3", "4", "4"]).run)
    assert charts.shown == []

#When a chart can't be drawn, the Chart Manager's reason is shown to the user
def test_charts_failure_message_is_shown():
    charts = FakeCharts(result=(False, "No reports to chart yet."))
    text = printed(io_manager(charts=charts, answers=["3", "1", "n", "4"]).run)
    assert "No reports to chart yet." in text

#Prompter Tests

#Test that blank, text and out-of-range answers are rejected before a valid one is accepted
def test_prompter_ask_number_rejects_bad_input_then_accepts():
    prompter = io.Prompter(read=ScriptedInput("", "abc", "9", "2").read)
    with contextlib.redirect_stdout(StringIO()) as out:
        result = prompter.ask_number("Choose (1-3): ", 1, 3)
    assert result == 2
    assert "can't be left blank" in out.getvalue()
    assert "'abc' is not a number" in out.getvalue()
    assert "9 is not an option" in out.getvalue()

#The user types y, so ask_yes_no should give back True
def test_prompter_yes():
    prompter = io.Prompter(read=ScriptedInput("y").read)
    result = prompter.ask_yes_no("Leave?")
    assert result is True

#The user types n, so ask_yes_no should give back False
def test_prompter_no():
    prompter = io.Prompter(read=ScriptedInput("n").read)
    result = prompter.ask_yes_no("Leave?")
    assert result is False

#Test that choose_from returns the picked value, and None when the user picks Back
def test_prompter_choose_from():
    values = ["Fall", "Fire", "Machinery"]
    with contextlib.redirect_stdout(StringIO()):
        picked = io.Prompter(read=ScriptedInput("2").read).choose_from("Root Cause", values)
        back = io.Prompter(read=ScriptedInput("4").read).choose_from("Root Cause", values)
    assert picked == "Fire"     # option 2 is the second value
    assert back is None         # option 4 is Back (3 values + 1)

#Test that ask_text returns what was typed, without the spaces around it
def test_prompter_ask_text_strips_spaces():
    assert io.Prompter(read=ScriptedInput("  Warehouse B  ").read).ask_text("Keyword: ") == "Warehouse B"

#Test that the cancel words work in any capitals, and normal text is not a cancel
def test_prompter_is_cancel():
    prompter = io.Prompter()
    assert prompter.is_cancel("QUIT") is True
    assert prompter.is_cancel(" exit ") is True
    assert prompter.is_cancel("hello") is False
