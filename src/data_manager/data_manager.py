# Imports
import pandas as pd
from datetime import timedelta

from src.data_manager.constants import DATE_FIELD, DATE_FORMAT, DEADLINE_FIELD, URGENCY_COLUMN
# The filter choices now live with their filter classes (these imports go once DataManager uses the filter objects)
from src.data_manager.filters.date_range_filter import *
from src.data_manager.filters.deadline_filter import *
from src.data_manager.filters.score_band_filter import *
from src.data_manager.storage.record_store import RecordStore
from src.data_manager.filters.score_band_filter import *
from src.data_manager.filters.keyword_filter import *
from src.data_manager.filters.exact_text_filter import *

# The one place the rest of the app goes to save, read and filter incident reports
# The reports themselves are kept by a RecordStore that is passed in
class DataManager:

    # store is where the reports are kept (a CSV file in the app). It is passed in, not created here,
    # so the DataManager can work with any RecordStore
    def __init__(self, store: RecordStore, filters: dict[str, ReportFilter]):
        self._store = store
        self._filters = filters if filters is not None else {}

    # Saves one report. Returns (success, message)
    def save_record(self, record):
        return self._store.save_record(record)

    # Reads all saved reports, sorted by urgency (highest first by default)
    def load_records(self, ascending=False):
        return self._store.load_records(ascending=ascending)

    # Returns all column headers of the saved reports
    def get_column_names(self):
        return self._store.get_column_names()

    def load_matching_records(self, column: str, value: str, ascending: bool = False):
        table = self.load_records(ascending=ascending)
        if table.empty or column not in table.columns:
            return pd.DataFrame()

        # Look up the specific filter object in the dictionary
        active_filter = self._filters.get(column)
        
        # Fallback to an exact text match if the column isn't in the injected dictionary
        if not active_filter:
            active_filter = ExactTextFilter(column)
            
        return active_filter.apply(table=table, value=value)

    def get_unique_values(self, column: str) -> list:
        table = self.load_records()
        if table.empty or column not in table.columns:
            return []

        # Look up the specific filter object in the dictionary
        active_filter = self._filters.get(column)
        
        if not active_filter:
            active_filter = ExactTextFilter(column)
            
        return active_filter.options(table=table)