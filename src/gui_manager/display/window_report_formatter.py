# ------- #
# Imports
# ------- #

from src.io_manager import ReportFormatter
from src.io_manager.constants import FULL_REPORT_FIELDS, TABLE_COLUMNS, YES_NO_COLUMNS
from src.gui_manager.constants import MUTED, SCORE_COLOURS, SURFACE_ALT

# ----- #
# Class
# ----- #

# Turns Report Data into What the Window Shows (Never Draws); Inherits the Terminal's YES/No Wording and Overdue Check
class WindowReportFormatter(ReportFormatter):
    # Cell as Display Text, with Blanks, None and NaN Shown as "-"
    def display_value(self, value) -> str:
        if value is None or (isinstance(value, float) and value != value):  # Only NaN is Not Equal to Itself
            return "-"
        text = str(value).strip()
        return text if text else "-"

    # One Table Row in TABLE_COLUMNS Order, Starting with the Row Number
    def table_row_values(self, number: int, report: dict) -> list:
        values = [number]
        for _, column, _ in TABLE_COLUMNS:
            value = report.get(column)
            values.append(self.yes_no(value) if column in YES_NO_COLUMNS else self.display_value(value))
        return values

    # Rows are Highlighted when Someone went to Hospital or the Incident Must Go to MOM
    def needs_attention(self, report: dict) -> bool:
        return self.yes_no(report.get("hospitalised")) == "YES" or self.yes_no(report.get("mom_reportable")) == "YES"

    # Every (Label, Value) Pair Shown when a Report is Opened in Full
    def full_report_lines(self, report: dict) -> list:
        lines = []
        for label, column in FULL_REPORT_FIELDS:
            value = report.get(column)
            if column in YES_NO_COLUMNS:
                value = self.yes_no(value)
            lines.append((label, self.display_value(value)))
        return lines

    # The MOM Warning for a Report, or None if it Does Not Need Reporting
    def mom_warning(self, report: dict) -> str | None:
        if self.yes_no(report.get("mom_reportable")) != "YES":
            return None
        deadline = self.display_value(report.get("deadline"))
        if self.is_overdue(deadline):
            return f"OVERDUE: this incident had to be reported to MOM by {deadline}. Tell your supervisor now."
        return f"This incident must be reported to MOM by {deadline}."

    # (Text Colour, Background) for a Score: Red for the Most Urgent, Green for the Least, Grey if Not a Number
    def score_colours(self, score) -> tuple:
        try:
            value = float(score)
        except (TypeError, ValueError):
            return MUTED, SURFACE_ALT
        for lowest, colour, background in SCORE_COLOURS:
            if value >= lowest:
                return colour, background
        return SCORE_COLOURS[-1][1], SCORE_COLOURS[-1][2]  # Negative or NaN Scores Count as Least Urgent

    # Counts for the Summary Cards above the Reports Table
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
