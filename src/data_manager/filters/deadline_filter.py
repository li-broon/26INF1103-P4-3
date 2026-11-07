# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.constants import DATE_FORMAT, DEADLINE_FIELD
from src.data_manager.filters.report_filter import ReportFilter

# ------------------ #
# Filter Choices
# ------------------ #

# Filter options for the MOM deadline column: (earliest, latest) in days from
# today. None means no limit on that side. 0 is today, -1 is yesterday.
DEADLINE_FILTERS = {
    "Overdue": (None, -1),
    "Due within 3 days": (0, 3),
    "Due within 7 days": (0, 7),
    "All upcoming": (0, None),
}

# ----- #
# Class
# ----- #

# Keeps the reports whose MOM deadline falls in a window (e.g. "Overdue", or "Due within 7 days")
class DeadlineFilter(ReportFilter):

    # windows maps each choice shown to the user to (earliest, latest) days from today
    def __init__(self, column: str = DEADLINE_FIELD, windows: dict = DEADLINE_FILTERS) -> None:
        super().__init__(column)
        self._windows = dict(windows)

    # Keeps records whose MOM deadline fall within a window
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        # Deadline windows are gotten from the windows this filter was given
        limits = self._windows.get(value)
        if limits is None:
            return pd.DataFrame()

        earliest, latest = limits
        today = pd.Timestamp.today().normalize()
        deadlines = pd.to_datetime(table[self._column], format=DATE_FORMAT, errors="coerce")
        days_left = (deadlines - today).dt.days # "N/A" or invalid deadlines become blanks

        keep = days_left.notna()  # No valid deadline means no match
        if earliest is not None:
            keep &= days_left >= earliest
        if latest is not None:
            keep &= days_left <= latest

        return table[keep].reset_index(drop=True)

    # The choices are the fixed windows, not every deadline in the reports
    def _options(self, table: pd.DataFrame) -> list[str]:
        return list(self._windows)