from src import data_manager


class DataManagerAdapter:
    """Thin wrapper over the existing src/data_manager.py so LogicManager depends on an object.

    Any object with a save_record(record) -> (success, message) method can be used instead
    (e.g. a fake for testing). If data_manager.py gets its own DataManager class, replace
    this adapter with it.
    """

    def save_record(self, record):
        return data_manager.save_record(record)
