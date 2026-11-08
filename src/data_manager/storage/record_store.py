# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod

import pandas as pd

# ----- #
# Class
# ----- #

# Contract Every Report Store Must Follow (a CSV File in the App, a Fake in the Tests)
class RecordStore(ABC):

    # Clean and Save One Report. Returns (success, message). A Bad Report Gives (False, reason), it Never Crashes.
    @abstractmethod
    def save_record(self, record: dict) -> tuple[bool, str]:
        pass

    # Return Every Saved Report as a Table Sorted by Urgency (Most Urgent First Unless ascending). Empty if Nothing is Saved.
    @abstractmethod
    def load_records(self, ascending: bool = False) -> pd.DataFrame:
        pass

    # Return the Column Names of the Saved Reports (an Empty List if Nothing is Saved)
    @abstractmethod
    def get_column_names(self) -> list[str]:
        pass