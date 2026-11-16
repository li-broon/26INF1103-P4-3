# Imports

from src.io_manager import ReportFormatter
from src.io_manager.constants import FULL_REPORT_FIELDS, TABLE_COLUMNS, YES_NO_COLUMNS
from src.data_manager.constants import MOM_REPORTED_FIELD
from src.gui_manager.constants import MOM_TABLE_COLUMNS, MUTED, SCORE_COLOURS, SURFACE_ALT, TICKED, UNTICKED

# Class

# Turns report data into text and colours for the window
class WindowReportFormatter(ReportFormatter):
    # Text for one cell; empty values show as "-"
    def display_value(self, value) -> str:
        if value is None or (isinstance(value, float) and value != value):  # True for NaN
            return "-"
        text = str(value).strip()
        return text if text else "-"

    # Values for one table row, starting with the row number
    def table_row_values(self, number: int, report: dict) -> list:
        values = [number]
        for _, column, _ in TABLE_COLUMNS:
            value = report.get(column)
            values.append(self.yes_no(value) if column in YES_NO_COLUMNS else self.display_value(value))
        return values

    # Highlight the row if someone went to hospital or it must be reported to MOM
    def needs_attention(self, report: dict) -> bool:
        return self.yes_no(report.get("hospitalised")) == "YES" or self.yes_no(report.get("mom_reportable")) == "YES"

    # Every (label, value) pair shown when a report is opened
    def full_report_lines(self, report: dict) -> list:
        lines = []
        for label, column in FULL_REPORT_FIELDS:
            value = report.get(column)
            if column in YES_NO_COLUMNS:
                value = self.yes_no(value)
            lines.append((label, self.display_value(value)))
        return lines

    # MOM warning text, or None if it does not need reporting
    def mom_warning(self, report: dict) -> str | None:
        if self.yes_no(report.get("mom_reportable")) != "YES":
            return None
        deadline = self.display_value(report.get("deadline"))
        if self.is_overdue(deadline):
            return f"OVERDUE: this incident had to be reported to MOM by {deadline}. Tell your supervisor now."
        return f"This incident must be reported to MOM by {deadline}."

    # Colours for a score: red for most urgent, green for least
    def score_colours(self, score) -> tuple:
        try:
            value = float(score)
        except (TypeError, ValueError):
            return MUTED, SURFACE_ALT
        for lowest, colour, background in SCORE_COLOURS:
            if value >= lowest:
                return colour, background
        return SCORE_COLOURS[-1][1], SCORE_COLOURS[-1][2]  # Treat bad scores as least urgent

    # Numbers for the summary cards on the Reports tab
    def report_stats(self, table) -> dict:
        stats = {"total": len(table), "mom": 0, "overdue": 0, "hospitalised": 0}
        for report in table.to_dict("records"):
            if self.yes_no(report.get("hospitalised")) == "YES":
                stats["hospitalised"] += 1
            if self.yes_no(report.get("mom_reportable")) == "YES":
                stats["mom"] += 1
                if self.is_overdue(self.display_value(report.get("deadline"))):
                    stats["overdue"] += 1
        return stats

    # True if the safety officer has ticked this report
    def is_reported(self, report: dict) -> bool:
        return self.yes_no(report.get(MOM_REPORTED_FIELD)) == "YES"

    # "reported", "overdue" or "pending", used for the row colour
    def mom_row_state(self, report: dict) -> str:
        if self.is_reported(report):
            return "reported"
        if self.is_overdue(self.display_value(report.get("deadline"))):
            return "overdue"
        return "pending"

    # Values for one MOM table row, starting with the tick box
    def mom_table_row_values(self, report: dict) -> list:
        values = []
        for _, column, _ in MOM_TABLE_COLUMNS:
            if column == MOM_REPORTED_FIELD:
                values.append(TICKED if self.is_reported(report) else UNTICKED)
            else:
                values.append(self.display_value(report.get(column)))
        return values

    # Numbers for the summary cards on the MOM tab
    def mom_stats(self, table) -> dict:
        stats = {"total": len(table), "pending": 0, "overdue": 0, "reported": 0}
        for report in table.to_dict("records"):
            state = self.mom_row_state(report)
            if state == "reported":
                stats["reported"] += 1
            else:
                stats["pending"] += 1
                if state == "overdue":
                    stats["overdue"] += 1
        return stats
