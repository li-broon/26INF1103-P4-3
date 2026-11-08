# ------- #
# Imports
# ------- #

from datetime import timedelta

import pandas as pd

from src.data_manager.constants import DATE_FIELD, DATE_FORMAT
from src.data_manager.filters.report_filter import ReportFilter

# ------------------ #
# Filter Choices
# ------------------ #

# Predefined date ranges for filtering, counting back from today
DATE_RANGES = {"Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90, "Last 180 Days": 180, "Last 365 Days": 365}

# ----- #
# Class
# ----- #

# Keeps the reports from the last N days (the user picks a range such as "Last 7 Days")
class DateRangeFilter(ReportFilter):

    # ranges maps each choice shown to the user to a number of days
    def __init__(self, column: str = DATE_FIELD, ranges: dict = DATE_RANGES) -> None:
        super().__init__(column)
        self._ranges = dict(ranges)

    # Keeps records from the last N days
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        days = self._ranges.get(value)
        # Returns empty table if unknown label
        if days is None:
            return pd.DataFrame()

        # Count from midnight today, so "Last 7 Days" includes a report dated exactly 7 days ago
        cutoff = pd.Timestamp.today().normalize() - timedelta(days=days)
        dates = pd.to_datetime(table[self._column], format=DATE_FORMAT, errors="coerce")

        return table[dates >= cutoff].reset_index(drop=True)

    # The choices are the fixed ranges, not every date in the reports
    def _options(self, table: pd.DataFrame) -> list[str]:
        return list(self._ranges)