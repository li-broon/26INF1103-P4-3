# ------- #
# Imports
# ------- #

import logging
import os

import pandas as pd

from src.data_manager.constants import REQUIRED_FIELDS, TRANSCRIPT_ID_FIELD, URGENCY_COLUMN
from src.data_manager.storage.record_cleaner import RecordCleaner
from src.data_manager.storage.record_store import RecordStore

# Used for debugging to log warnings and errors instead of printing them to the console
logger = logging.getLogger(__name__)

# ----- #
# Class
# ----- #

# Keeps the reports in one CSV file (the RecordStore the app uses)
class CsvRecordStore(RecordStore):

    # data_file is the CSV file the reports are stored in
    def __init__(self, data_file: str) -> None:
        self._data_file = data_file
        self._data_folder = os.path.dirname(data_file)
        self._cleaner = RecordCleaner()  # Created and owned by this store

    # Adds one report to the CSV file
    def save_record(self, record: dict) -> tuple[bool, str]:
        # Attempts to clean record
        cleaned = self._cleaner.clean(record)
        if cleaned is None:
            return False, "Record rejected: missing or invalid required field."

        # Makes sure data folder exists
        os.makedirs(self._data_folder, exist_ok=True)
        existing_data = self._load_data_from_csv(self._data_file)

        # File exists but couldn't be read: keep a backup instead of overwriting it
        if existing_data.empty and os.path.exists(self._data_file) and os.path.getsize(self._data_file) > 0:
            os.replace(self._data_file, self._data_file.replace(".csv", "_backup.csv"))
            logger.warning("Unreadable data file backed up to '%s'.", self._data_file.replace(".csv", "_backup.csv"))

        # Checks if record is a duplicate
        if self._is_duplicate(existing_data, cleaned):
            return False, "Record rejected: an identical record already exists."

        new_row = pd.DataFrame([cleaned])

        # Creates a new DataFrame with the new row if existing_data is empty, otherwise concatenates the new row to existing_data
        table = new_row if existing_data.empty else pd.concat([existing_data, new_row], ignore_index=True)
        # Sort the table by urgency before saving
        table = self._sort_by_urgency(table)

        # Write a temporary file first to avoid data loss if the write fails, then replace the original if everything is good
        temp_file = self._data_file + ".tmp"
        try:
            table.to_csv(temp_file, index=False)
            os.replace(temp_file, self._data_file)
        except OSError as e:
            logger.error("Could not write '%s': %s", self._data_file, e)
            return False, "Record could not be saved (file write error)."

        return True, "Record saved."

    # Reads all reports for display: cleans each row, drops invalid or duplicate rows and sorts by urgency, without changing the file
    def load_records(self, ascending: bool = False) -> pd.DataFrame:
        table = self._load_data_from_csv(self._data_file)
        if table.empty:
            return table

        valid_records = []
        # Convert dataframe to a list of dictionaries
        for record in table.to_dict("records"):
            # Clean each row and only keep valid ones
            cleaned = self._cleaner.clean(record)
            # Only keep rows that pass validation (rejects None)
            if cleaned is not None:
                valid_records.append(cleaned)

        # If all rows were corrupt, return empty
        if not valid_records:
            return pd.DataFrame()

        # Convert back to DataFrame and sort
        clean_table = pd.DataFrame(valid_records)

        # Drop exact duplicates that might have been pasted in manually
        clean_table = clean_table.drop_duplicates()

        return self._sort_by_urgency(clean_table, ascending=ascending)

    # Simple function to return all column headers in the CSV file
    def get_column_names(self) -> list[str]:
        return list(self._load_data_from_csv(self._data_file).columns)

    # Function checks for duplicate records
    def _is_duplicate(self, existing_data: pd.DataFrame, record: dict) -> bool:
        # If the existing data is empty, there can't be a duplicate
        if existing_data.empty:
            return False

        for row in existing_data.to_dict("records"):
            row_matches = True  # Assume a match until a field proves otherwise

            for field, new_value in record.items():
                # The transcript ID is new for every conversation, so it is left out (otherwise nothing could ever be a duplicate)
                if field == TRANSCRIPT_ID_FIELD:
                    continue
                # Comparing the existing row's value and the new record's value
                if self._cleaner.comparable(row.get(field)) != self._cleaner.comparable(new_value):
                    row_matches = False
                    break

            # If all fields matched, there's a duplicate
            if row_matches: 
                return True
        # Returns false, meaning the new record is a unique record    
        return False

    # Safe reading of the CSV file
    def _load_data_from_csv(self, file_path: str) -> pd.DataFrame:
        # A missing or empty file gives an empty table
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return pd.DataFrame()

        try:
            # Only Blank Cells Count as Missing (pandas' Default Turned the "N/A" Deadline into NaN, Breaking Duplicate Checks and Erasing "N/A" on Re-Save)
            df = pd.read_csv(file_path, keep_default_na=False, na_values=[""])

        # Error handling, logs the error and returns empty table so application never crashes
        except pd.errors.EmptyDataError:
            logger.warning("File '%s' is empty.", file_path)
            return pd.DataFrame()
        except pd.errors.ParserError:
            logger.warning("File '%s' is badly formatted.", file_path)
            return pd.DataFrame()
        except PermissionError:
            logger.error("No permission to read '%s'.", file_path)
            return pd.DataFrame()
        except Exception as e:
            logger.error("Unexpected problem loading '%s': %s", file_path, e)
            return pd.DataFrame()

        # Checks for required columns
        missing = [col for col in REQUIRED_FIELDS if col not in df.columns]
        if missing:
            logger.warning("File '%s' is missing required columns: %s", file_path, missing)
            return pd.DataFrame()

        return df

    def _sort_by_column(self, data: pd.DataFrame, column_name: str, ascending: bool = True) -> pd.DataFrame:

        # Safety check : if column does not exist, return the data unchanged instead of crashing
        if column_name not in data.columns:
            return data

        # Sorts by the chosen column (blank values go to the bottom) and renumbers the rows from 0
        return data.sort_values(by=column_name, ascending=ascending, na_position="last").reset_index(drop=True)

    # Converts the score column to numbers and sorts by it, highest first by default
    def _sort_by_urgency(self, table: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
        if URGENCY_COLUMN in table.columns:
            table = table.copy()
            table[URGENCY_COLUMN] = pd.to_numeric(table[URGENCY_COLUMN], errors="coerce")
        return self._sort_by_column(table, URGENCY_COLUMN, ascending=ascending)