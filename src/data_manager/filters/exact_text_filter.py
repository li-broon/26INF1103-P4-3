# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.filters.report_filter import ReportFilter

# ----- #
# Class
# ----- #

# Keeps the reports whose text in this column equals the chosen value (e.g. severity "High")
class ExactTextFilter(ReportFilter):

    # Keeps records whose string matches the value exactly, it is not case-sensitive, ignores extra spaces
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        column_text = table[self._column].astype(str).str.strip().str.lower()

        return table[column_text == str(value).strip().lower()].reset_index(drop=True)
