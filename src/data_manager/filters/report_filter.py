# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

import pandas as pd

# Base Class for the Filters the User can Apply to Saved Reports (One per Column)
# Sub classes determine how the filter works (e.g. by a fixed range, or by matching a keyword, or by exact text)
class ReportFilter(ABC):

    # column is the column of the reports this filter works on
    def __init__(self, column: str) -> None:
        self._column = column

    # Column getter
    @property
    def column(self) -> str:
        return self._column

    # Applies the filter to the reports table, returning only the matching reports (or an empty table if the column is not there)
    def apply(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        if self._column not in table.columns:
            return pd.DataFrame()
        return self._match(table, value)

    # Provide options for multiple choice filters (e.g. "Last 7 Days", "Overdue", "High Severity")
    def options(self, table: pd.DataFrame) -> list[str]:
        if self._column not in table.columns:
            return []
        return self._options(table)

    # determine how value in the column is matched each sub class (filter) implements this
    @abstractmethod
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        pass

    # Default Choices: Each Distinct Saved Value Once, in Alphabetical Order (Filters with Fixed Choices, e.g. "Last 7 Days", Override This)
    def _options(self, table: pd.DataFrame) -> list[str]:
        return sorted(table[self._column].dropna().astype(str).unique())