# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.filters.report_filter import ReportFilter

# Filters columns by matching the text exactly (case-insensitive, ignores extra spaces).
# Used for columns that have no special filter.
class ExactTextFilter(ReportFilter):

    # Keeps records whose string matches the value exactly, it is not case-sensitive, ignores extra spaces
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        column_text = table[self._column].astype(str).str.strip().str.lower()

        return table[column_text == str(value).strip().lower()].reset_index(drop=True)
