# Imports
import pandas as pd

from src.data_manager.filters.exact_text_filter import ExactTextFilter
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.storage.record_store import RecordStore

# The one place the rest of the app goes to save, read and filter reports (the RecordStore and ReportFilters it uses are passed in)
class DataManager:

    # store keeps the reports (a CSV file in the app) and filters maps each column to its filter; both are passed in so any store or filters work
    def __init__(self, store: RecordStore, filters: dict[str, ReportFilter]) -> None:
        self._store = store
        self._filters = dict(filters)  # A copy, so changing the dictionary later changes nothing here

    # Saves one report. Returns (success, message)
    def save_record(self, record: dict) -> tuple[bool, str]:
        return self._store.save_record(record)

    # Reads all saved reports, sorted by urgency (highest first by default)
    def load_records(self, ascending: bool = False) -> pd.DataFrame:
        return self._store.load_records(ascending=ascending)

    # Returns all column headers of the saved reports
    def get_column_names(self) -> list[str]:
        return self._store.get_column_names()

    # Called by io_manager once the user has chosen a column and a value; results are sorted by urgency
    def load_matching_records(self, column: str, value: str, ascending: bool = False) -> pd.DataFrame:
        table = self.load_records(ascending=ascending)

        # The filter returns an empty table if the column is not there (or nothing is saved yet)
        return self._filter_for(column).apply(table=table, value=value)

    # Builds the filter options the user sees in the I/O menu; the column's filter decides them (fixed ranges for score and date, saved values otherwise)
    def get_unique_values(self, column: str) -> list[str]:
        # The filter returns an empty list if the column is not there (or nothing is saved yet)
        return self._filter_for(column).options(table=self.load_records())

    # Looks up the column's filter, falling back to an exact text match if the column has none
    def _filter_for(self, column: str) -> ReportFilter:
        if column in self._filters:
            return self._filters[column]
        return ExactTextFilter(column)