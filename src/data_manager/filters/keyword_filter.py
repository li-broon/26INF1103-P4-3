# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.filters.report_filter import ReportFilter

# ----- #
# Class
# ----- #

# Keeps the reports whose text in this column contains a keyword (e.g. "office" finds "Head Office")
class KeywordFilter(ReportFilter):

    # Keeps records containing the typed keyword, it is not case-sensitive, ignores extra spaces
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        keyword = str(value).strip()
        # Blank keyword returns empty table
        if keyword == "":
            return pd.DataFrame()

        # Regex false means symbols like () + , are treated as plain characters, safe to type
        found = table[self._column].astype(str).str.contains(keyword, case=False, regex=False, na=False)

        return table[found].reset_index(drop=True)

    # No pick list: a keyword is typed, so the menus are given nothing to choose from (and know to ask for a word instead)
    def _options(self, table: pd.DataFrame) -> list[str]:
        return []
