# Public Parts of the Data Manager
from src.data_manager.data_manager import DataManager
from src.data_manager.storage.record_store import RecordStore

# One shared DataManager, so the functions below keep working for io_manager and logic_manager
# Remove them once main.py creates the DataManager and passes it to the other managers
_manager = DataManager()

def save_record(record):
    return _manager.save_record(record)

def load_records(ascending=False):
    return _manager.load_records(ascending=ascending)

def get_unique_values(column_name):
    return _manager.get_unique_values(column_name)

def load_matching_records(column_name, value, ascending=False):
    return _manager.load_matching_records(column_name, value, ascending=ascending)

def get_chart_options():
    return _manager.get_chart_options()
 
def show_chart(chart_name, filter_column=None, filter_value=None, save_path=None):
    return _manager.show_chart(chart_name, filter_column, filter_value, save_path)

# The Package's Public Names
__all__ = [
    "DataManager", "RecordStore",
    "save_record", "load_records", "get_unique_values", "load_matching_records",
    "get_chart_options", "show_chart",
]