# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

import pandas as pd

# ----- #
# Class
# ----- #

# Base Class for the Filters the User can Apply to Saved Reports (One per Column): Does the Shared Checks, Each Subclass Only Says How a Report Matches
class ReportFilter(ABC):

    # column is the column of the reports this filter works on
    def __init__(self, column: str) -> None:
        self._column = column

    # The column this filter works on (read only)
    @property
    def column(self) -> str:
        return self._column

    # Keeps the Reports that Match the Chosen Value. Gives an Empty Table if the Column is Not in the Table
    def apply(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        if self._column not in table.columns:
            return pd.DataFrame()
        return self._match(table, value)

    # The Choices to Show the User for this Column. Gives an Empty List if the Column is Not in the Table
    def options(self, table: pd.DataFrame) -> list[str]:
        if self._column not in table.columns:
            return []
        return self._options(table)

    # How a Report Matches the Chosen Value (Every Subclass Must Say)
    @abstractmethod
    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        pass

    # Default Choices: Each Distinct Saved Value Once, in Alphabetical Order (Filters with Fixed Choices, e.g. "Last 7 Days", Override This)
    def _options(self, table: pd.DataFrame) -> list[str]:
        return sorted(table[self._column].dropna().astype(str).unique())