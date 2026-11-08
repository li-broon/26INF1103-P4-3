# ------- #
# Imports
# ------- #

import re
from datetime import date

import pandas as pd

from src.io_manager.display.pager import Pager
from src.io_manager.display.report_card_view import ReportCardView
from src.io_manager.display.report_formatter import ReportFormatter
from src.io_manager.display.report_table_view import ReportTableView
from src.logic_manager import SaveOutcome
from tests.helpers.io_samples import REPORT, SAVED_FIELDS
from tests.helpers.print_capture import PrintCapture


# Tests for the io_manager Display Classes: ReportFormatter, Pager, ReportCardView and ReportTableView
class TestDisplay:

    def setup_method(self):
        self._card_view = ReportCardView(ReportFormatter())
        self._capture = PrintCapture()

    # The Logic Manager's Result for a Saved Report, with Some Fields Changed (e.g. deadline="2022-12-22")
    def _outcome(self, **changes) -> SaveOutcome:
        return SaveOutcome(**dict(SAVED_FIELDS, **changes))

    # ---------------- ReportFormatter.fit_text ---------------- #

    # Test that text shorter than the width is padded with spaces
    def test_fit_pads_short_text(self):
        result = ReportFormatter().fit_text("Hello", 10)
        assert len(result) == 10
        assert result == "Hello     "

    # Test that text longer than the width is cut off and appended with an ellipsis.
    def test_fit_truncates_long_text(self):
        result = ReportFormatter().fit_text("This is a very long location name", 15)
        assert len(result) == 15
        assert result.endswith("… ")
        assert result == "This is a ver… "

    # Test that numeric or boolean inputs are safely converted to strings before fitting.
    def test_fit_handles_non_strings(self):
        result = ReportFormatter().fit_text(42.5, 6)
        assert result == "42.5  "

    # ---------------- Pager ---------------- #

    # Test page count when the rows divide exactly: 10 rows at 5 per page = 2 pages
    def test_page_count_exact_multiple(self):
        assert Pager(10, page_size=5).page_count() == 2

    # Test page count when rows spill onto an extra page: 12 rows at 5 per page = 3 pages
    def test_page_count_with_remainder(self):
        assert Pager(12, page_size=5).page_count() == 3

    # Test that an empty table still has 1 page, so the screen never shows 'page 1 of 0'
    def test_page_count_empty_table(self):
        assert Pager(0).page_count() == 1

    # Test that next() moves forward and says it moved
    def test_go_next_success(self):
        pager = Pager(9, page_size=3)
        assert pager.next() is True
        assert pager.current_page() == 2

    # Test that next() refuses to go past the last page and stays put
    def test_go_next_blocked_at_end(self):
        pager = Pager(9, page_size=3)
        pager.next()
        pager.next()                        # now on page 3, the last page
        assert pager.next() is False
        assert pager.current_page() == 3

    # Test that previous() moves back and says it moved
    def test_go_previous_success(self):
        pager = Pager(9, page_size=3)
        pager.next()                        # page 2
        assert pager.previous() is True
        assert pager.current_page() == 1

    # Test that previous() refuses to go before page 1 and stays put
    def test_go_previous_blocked_at_start(self):
        pager = Pager(9, page_size=3)
        assert pager.previous() is False
        assert pager.current_page() == 1

    # Test that the last page only shows the leftover rows: 7 rows, page 3 = row 7 only
    def test_row_range_last_page(self):
        pager = Pager(7, page_size=3)
        pager.next()
        pager.next()
        assert pager.row_range() == (6, 7)

    # ---------------- ReportCardView ---------------- #

    # Test that a saved report is shown back with the worker's details plus the score and MOM deadline.
    def test_confirmation_card_shows_report_and_logic_results(self):
        text = self._capture.text_of(self._card_view.show_save_outcome, REPORT, self._outcome())
        assert "Your report has been saved" in text
        assert "Your Saved Report" in text
        assert "Ahmad bin Ismail" in text
        assert re.search(r"Score:\s+7.4", text)
        assert re.search(r"Hospitalised:\s+YES", text)
        assert re.search(r"MOM deadline:\s+2099-12-31", text)
        assert "must be reported to MOM by 2099-12-31" in text
        assert "Injury:" not in text  # Empty fields are skipped

    # Test that a failed save shows the reason and no card, so the worker isn't told it was saved
    def test_confirmation_card_not_shown_when_save_fails(self):
        failed = self._outcome(saved=False, message="Record rejected: an identical record already exists.")
        text = self._capture.text_of(self._card_view.show_save_outcome, REPORT, failed)
        assert "NOT saved" in text
        assert "identical record" in text
        assert "Your Saved Report" not in text
        assert "has been saved" not in text

    # Test that a MOM deadline in the past is shown as OVERDUE.
    def test_confirmation_card_says_overdue_when_deadline_passed(self):
        text = self._capture.text_of(self._card_view.show_save_outcome, REPORT, self._outcome(deadline="2022-12-22"))
        assert "OVERDUE" in text
        assert "2022-12-22" in text

    # Test that only deadlines before today count as overdue, and bad dates never do.
    def test_is_overdue(self):
        today = date(2026, 10, 13)
        assert self._card_view._is_overdue("2026-10-12", today) is True
        assert self._card_view._is_overdue("2026-10-13", today) is False  # Due today is not overdue yet
        assert self._card_view._is_overdue("2026-10-14", today) is False
        assert self._card_view._is_overdue("Check incident date", today) is False
        assert self._card_view._is_overdue("N/A", today) is False

    # Test that a non-MOM report shows N/A as its deadline and no MOM warning.
    def test_confirmation_card_no_mom_warning_when_not_reportable(self):
        text = self._capture.text_of(self._card_view.show_save_outcome, REPORT,
                                     self._outcome(mom_reportable="No", deadline="N/A"))
        assert re.search(r"MOM reportable:\s+No", text)
        assert "must be reported" not in text

    # Test that opening a report from the table shows its number and its fields.
    def test_full_report_from_table_uses_report_number(self):
        table = pd.DataFrame([REPORT, dict(REPORT, reporter_name="Siti")])
        text = self._capture.text_of(self._card_view.show_from_table, table, 2)
        assert "Report #2" in text
        assert "Siti" in text

    # ---------------- ReportTableView ---------------- #

    # Test that one page shows the header, 3 reports, and the footer exactly once
    def test_table_view_shows_one_page(self):
        table = pd.DataFrame([REPORT] * 4)
        view = ReportTableView(ReportFormatter())
        text = self._capture.text_of(view.show, table, "Saved Reports", Pager(len(table), page_size=3))
        assert "Score" in text and "Severity" in text
        assert text.count("Ahmad bin Ismail") == 3
        assert text.count("Page 1 of 2") == 1
