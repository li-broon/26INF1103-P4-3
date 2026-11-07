# Public Parts of the Data Manager
from src.data_manager.constants import DATA_FILE
from src.data_manager.filters.default_filters import create_default_filters
from src.data_manager.manager import DataManager
from src.data_manager.storage.csv_record_store import CsvRecordStore
from src.data_manager.storage.record_store import RecordStore

# One shared DataManager, so the functions below keep working for io_manager and logic_manager
# Remove them once main.py creates the DataManager and passes it to the other managers
_manager = DataManager(CsvRecordStore(DATA_FILE), create_default_filters())

def save_record(record):
    return _manager.save_record(record)

def load_records(ascending=False):
    return _manager.load_records(ascending=ascending)

def get_unique_values(column_name):
    return _manager.get_unique_values(column_name)

def load_matching_records(column_name, value, ascending=False):
    return _manager.load_matching_records(column_name, value, ascending=ascending)

# The Package's Public Names
__all__ = [
    "DataManager", "RecordStore", "CsvRecordStore", "create_default_filters",
    "save_record", "load_records", "get_unique_values", "load_matching_records",
]