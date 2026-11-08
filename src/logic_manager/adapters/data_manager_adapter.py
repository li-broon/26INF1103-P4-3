from src import data_manager


# Thin wrapper so LogicManager saves through an object (any object with save_record(record) -> (success, message) works); replace it with the real DataManager once main.py passes one in
class DataManagerAdapter:

    def save_record(self, record):
        return data_manager.save_record(record)
