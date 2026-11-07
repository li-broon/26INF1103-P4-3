# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.constants import URGENCY_COLUMN
from src.data_manager.filters.report_filter import ReportFilter

# ------------------ #
# Filter Choices
# ------------------ #

# Indicates the boundary for each threshold filter in the urgency column.
# Ranges [0-2, 2-4, 4-6, 6-8, 8 and above]
SCORE_THRESHOLDS = ["0", "2", "4", "6", "8"]

# ----- #
# Class
# ----- #

# Keeps the reports whose score is within a band (e.g. "2 to under 4", or "8+" for 8 and above)
class ScoreBandFilter(ReportFilter):

    # thresholds are the start of each band, lowest first (each band ends where the next one starts)
    def __init__(self, column: str = URGENCY_COLUMN, thresholds: list[str] = SCORE_THRESHOLDS):
        super().__init__(column)
        self._thresholds = list(thresholds)

    # Keeps the records whose score is within the chosen score band
    # Example : "2 to under 4" will then keep records with score of 2 up to (not including) 4
    # "8+" will keep every record from 8 upward
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        try:
            # Extract the selected threshold from value which is the range (0-24 etc.)
            raw_value = str(value).split()[0].replace("+", "")
            minimum = float(raw_value)
            min_index = self._thresholds.index(raw_value)

            # next_threshold is the threshold in the thresholds list after the selected threshold
            next_threshold = float(self._thresholds[min_index + 1]) if min_index + 1 < len(self._thresholds) else None

            if next_threshold is not None:
                # Keep the values within the threshold range
                table = table[(table[self._column] >= minimum) & (table[self._column] < next_threshold)]
            else:
                # No next threshold, so just filter by the minimum
                table = table[table[self._column] >= minimum]

        # Returns empty table if a blank or non-numeric value, or a value that is not one of the bands, is found
        except (ValueError, IndexError):
            return pd.DataFrame()

        return table.reset_index(drop=True)

    # The choices are the fixed bands, not every score in the reports
    def _options(self, table: pd.DataFrame) -> list[str]:
        bands = []
        for i, threshold in enumerate(self._thresholds):
            if i + 1 < len(self._thresholds):
                bands.append(f"{threshold} to under {self._thresholds[i + 1]}")
            else:
                bands.append(f"{threshold}+")
        return bands
