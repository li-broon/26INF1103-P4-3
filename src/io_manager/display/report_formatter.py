import textwrap  # Wraps Long Sentences onto Several Lines so Nothing is Cut Off
from datetime import date, datetime  # Checks Whether a MOM Deadline has Passed

from src.io_manager.constants import (
    ALERT_COLUMNS,
    BOLD,
    CYAN,
    DETAIL_FIELDS,
    DETAIL_INDENT,
    DETAIL_LABEL_WIDTH,
    DETAIL_TEXT_WIDTH,
    EMPTY_VALUES,
    RED,
    RESET,
    TABLE_COLUMNS,
)


#Turns Report Data into Display Text (Never Prints)
class ReportFormatter:
    # The layout of the table does not change, so it is stored once
    def __init__(self, columns=TABLE_COLUMNS, details=DETAIL_FIELDS):
        self._columns = columns
        self._details = details

    # Cut or pad text to an exact column width
    def fit_text(self, text, width) -> str:
        text = str(text)
        if len(text) >= width:
            text = text[:width - 2] + "…"
        return text.ljust(width)

    # Turn one long field into wrapped, indented lines (returns [] if the field is empty)
    def wrap_detail(self, label, text) -> list:
        text = str(text).strip()
        if text.lower() in EMPTY_VALUES:
            return []
        indent = " " * DETAIL_INDENT
        label_cell = f"{label}:".ljust(DETAIL_LABEL_WIDTH)
        lines = textwrap.wrap(text, width=DETAIL_TEXT_WIDTH) or [text]

        # First line carries the label, the rest line up underneath the text
        wrapped = [f"{indent}{CYAN}{label_cell}{RESET}{lines[0]}"]
        wrapped += [f"{indent}{' ' * DETAIL_LABEL_WIDTH}{line}" for line in lines[1:]]
        return wrapped

    # Turn a True/False value from data.csv into "YES", "No" or "-"
    def yes_no(self, value) -> str:
        text = str(value).strip().lower()
        if text in ("true", "yes", "1", "1.0"):
            return "YES"
        if text in ("false", "no", "0", "0.0"):
            return "No"
        return "-"

    # Check whether a MOM deadline has already passed (a deadline of today is not overdue yet)
    def is_overdue(self, deadline, today=None) -> bool:
        try:
            due = datetime.strptime(str(deadline), "%Y-%m-%d").date()
        except ValueError:
            return False  # e.g. "Check incident date": no real date to compare
        return due < (today or date.today())

    # Build one summary row, highlighting hospital and MOM cases in red
    def build_row(self, number, report) -> str:
        row = self.fit_text(number, 5)
        for heading, data_column, width in self._columns:
            value = report.get(data_column, "-")

            # Yes/No columns: YES is worth shouting about
            if data_column in ALERT_COLUMNS:
                value = self.yes_no(value)
                cell = self.fit_text(value, width)
                row += f"{RED}{BOLD}{cell}{RESET}" if value == "YES" else cell
                continue

            # The deadline is only urgent when MOM must be told
            if data_column == "deadline":
                cell = self.fit_text(value, width)
                must_report = self.yes_no(report.get("mom_reportable")) == "YES"
                row += f"{RED}{BOLD}{cell}{RESET}" if must_report else cell
                continue

            row += self.fit_text(value, width)
        return row

    # The heading line of the table: "No." then every column name at its width
    def build_header(self) -> str:
        header = self.fit_text("No.", 5)
        for heading, column, width in self._columns:
            header += self.fit_text(heading, width)
        return header

    # Every wrapped detail line shown under one table row (empty fields are skipped)
    def build_details(self, report) -> list:
        lines = []
        for label, column in self._details:
            lines += self.wrap_detail(label, report.get(column, "-"))
        return lines