# ------- #
# Imports
# ------- #

import pandas as pd
from src.data_manager.filters.report_filter import ReportFilter

# ---- #
# Class
# ---- #

# A Test-Only Filter that Remembers the Values it was Asked for, Always Keeps Eli's Reports and Offers One Fixed Choice (Proves Any Filter Given is Used)
class ShoutFilter(ReportFilter):
    def __init__(self, column: str):
        super().__init__(column)
        self.calls = []

    def _match(self, table: pd.DataFrame, value: str) -> pd.DataFrame:
        self.calls.append(value)
        return table[table["reporter_name"] == "Eli"].reset_index(drop=True)

    def _options(self, table: pd.DataFrame) -> list[str]:
        return ["only choice"]
