# ------- #
# Imports
# ------- #

import pandas as pd


# A Fake Data Manager that Never Touches data.csv: Saving Records the Report and Returns the Prepared Result, Reading Returns the Prepared Table
class FakeDataManager:
    def __init__(self, table: pd.DataFrame | None = None, save_result: tuple[bool, str] = (True, "Record saved.")):
        self._table = table if table is not None else pd.DataFrame()
        self._save_result = save_result
        self.saved_records = []

    def save_record(self, record: dict) -> tuple[bool, str]:
        self.saved_records.append(record)
        return self._save_result

    def load_records(self, ascending: bool = False) -> pd.DataFrame:
        return self._table

    def get_unique_values(self, column: str) -> list[str]:
        return []

    def load_matching_records(self, column: str, value: str, ascending: bool = False) -> pd.DataFrame:
        return self._table
