# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

import pandas as pd



# Interface: Utility interface for classes that want to extend file saving and loading reports functionality
class RecordStore(ABC):

    # Clean and Save One Report
    @abstractmethod
    def save_record(self, record: dict) -> tuple[bool, str]:
        pass

    # Loads all saved reports
    @abstractmethod
    def load_records(self, ascending: bool = False) -> pd.DataFrame:
        pass

    # Return the Column Names of the Saved Reports
    @abstractmethod
    def get_column_names(self) -> list[str]:
        pass