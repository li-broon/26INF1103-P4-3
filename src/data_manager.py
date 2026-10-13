# Imports
import logging
import os

import pandas as pd
from datetime import timedelta

# Gets correct data directory no matter where application is launched from
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")

# Sorting by score means sorting by urgency 
URGENCY_COLUMN = "importance_score"

# Important fields that csv must contain, or the csv is rejected
REQUIRED_FIELDS = ["reporter_name", "incident_date", URGENCY_COLUMN]

# The date column and its format (e.g. 2026-12-5)
DATE_FIELD = "incident_date"
DATE_FORMAT = "%Y-%m-%d"

# Columns that are searched for keywords (location)
KEYWORD_COLUMNS = ["location"]

# Predefined date ranges for filtering, counting back from today
DATE_RANGES = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
    "Last 180 Days": 180,
    "Last 365 Days": 365,
}

DEADLINE_FIELD = "deadline"

# Filter options for the MOM deadline column: (earliest, latest) in days from
# today. None means no limit on that side. 0 is today, -1 is yesterday.
DEADLINE_FILTERS = {
    "Overdue": (None, -1),
    "Due within 3 days": (0, 3),
    "Due within 7 days": (0, 7),
    "All upcoming": (0, None),
}

# Indicates the boundary for each threshold filter in the urgency column.
# Ranges [0-2, 2-4, 4-6, 6-8, 8 and above]
SCORE_THRESHOLDS = ["0", "2", "4", "6", "8"]
# Used for debugging to log warnings and errors instead of printing them to the console
logger = logging.getLogger(__name__)

# CSV Cleaning
def clean_record(record):
    # If input is not a dictionary, rejects it
    if not isinstance(record, dict):
        return None

    # Makes a copy so that the original is not affected
    cleaned = record.copy()

    # Strip whitespace from every text value
    for k, v in cleaned.items():
        if isinstance(v, str):
            cleaned[k] = v.strip()
        else:
            cleaned[k] = v

    # Required fields must exist and be non-empty
    for field in REQUIRED_FIELDS:
        value = cleaned.get(field)
        if value is None or (isinstance(value, str) and value == "") or pd.isna(value):
            return None

    try:
        # Converts date to exact YYYY-MM-DD format
        cleaned[DATE_FIELD] = pd.to_datetime(
            cleaned[DATE_FIELD], format=DATE_FORMAT
        ).strftime(DATE_FORMAT)
        # Converts score to decimal number
        cleaned[URGENCY_COLUMN] = float(cleaned[URGENCY_COLUMN])
    # If conversion fails, reject the input
    except (ValueError, TypeError):
        return None

    # Returns cleaned copy
    return cleaned

# Function purpose : converts value into a standardised format for fair comparison
# Example : "5" and 5.0 count as equal, or lowercase and trims such that "Fire" and "fire" are equal
def comparable(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value).strip().lower()

# Function checks for duplicate records
def is_duplicate(existing_data, record):
    # If the existing data is empty, there can't be a duplicate
    if existing_data.empty:
        return False

    for row in existing_data.to_dict("records"):
        row_matches = True  # Assume a match until a field proves otherwise

        for field, new_value in record.items():
            # Comparing the existing row's value and the new record's value
            if comparable(row.get(field)) != comparable(new_value):
                row_matches = False
                break

        # If all fields matched, there's a duplicate
        if row_matches: 
            return True
    # Returns false, meaning the new record is a unique record    
    return False

# Safe reading of the CSV file
def load_data_from_csv(file_path):
    # Checks if file exists and isn't empty
    # Returns empty table if does not exist or is empty
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    try:
        # Only Blank Cells Count as Missing. By Default pandas Also Turns Text like "N/A" (the
        # Deadline for Non-MOM Reports) into NaN, which Broke Duplicate Checks and Erased "N/A" on Re-Save.
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

def sort_by_column(data, column_name, ascending=True):

    # Safety check : if column does not exist, return the data unchanged instead of crashing
    if column_name not in data.columns:
        return data

    # Sort by the chosen column, rows with a blank value always go to the bottom
    # Renumbers the rows in the new order starting with 0
    return data.sort_values(by=column_name, ascending=ascending, na_position="last").reset_index(drop=True)

# Keeps the records whose score is within the chosen score band
# Example : "2 to under 4" will then keep records with score of 2 up to (not including) 4
# "8+" will keep every record from 8 upward
def filter_by_minimum(data, column_name, value):
    try:
        # Extract the selected threshold from value which is the range (0-24 etc.)
        raw_value = str(value).split()[0].replace("+", "")
        minimum = float(raw_value)
        min_index = SCORE_THRESHOLDS.index(raw_value)

        # next_threshold is the threshold in the SCORE_THRESHOLDS list after the selected threshold
        next_threshold = float(SCORE_THRESHOLDS[min_index + 1]) if min_index + 1 < len(SCORE_THRESHOLDS) else None

        if next_threshold is not None:
            # Keep the values within the threshold range
            data = data[(data[column_name] >= minimum) & (data[column_name] < next_threshold)]
        else:
            # No next threshold, so just filter by the minimum
            data = data[data[column_name] >= minimum]

    # Returns empty table if non-numeric value or value not found in table is found
    except ValueError:
        return pd.DataFrame()

    return data.reset_index(drop=True)

# Keeps records from the last N days
def filter_by_date_range(data, column_name, value):
    days = DATE_RANGES.get(value)
    # Returns empty table if unknown label
    if days is None:
        return pd.DataFrame()

    # Count from midnight today, so "Last 7 Days" includes a report dated exactly 7 days ago
    cutoff = pd.Timestamp.today().normalize() - timedelta(days=days)
    dates = pd.to_datetime(data[column_name], format=DATE_FORMAT, errors="coerce")

    return data[dates >= cutoff].reset_index(drop=True)

# Keeps records whose MOM deadline fall within a window
def filter_by_deadline(data, column_name, value):
    # Deadline windows are gotten from DEADLINE_FILTERS
    limits = DEADLINE_FILTERS.get(value)
    if limits is None:
        return pd.DataFrame()

    earliest, latest = limits
    today = pd.Timestamp.today().normalize()
    deadlines = pd.to_datetime(data[column_name], format=DATE_FORMAT, errors="coerce")
    days_left = (deadlines - today).dt.days # "N/A" or invalid deadlines become blanks

    keep = days_left.notna()  # No valid deadline means no match
    if earliest is not None:
        keep &= days_left >= earliest
    if latest is not None:
        keep &= days_left <= latest

    return data[keep].reset_index(drop=True)

# Keeps records containing the typed keyword, it is not case-sensitive, ignores extra spaces
def filter_by_keyword(data, column_name, value):
    keyword = str(value).strip()
    # Blank keyword returns empty table
    if keyword == "":
        return pd.DataFrame()

    # Regex false means symbols like () + , are treated as plain characters, safe to type
    found = data[column_name].astype(str).str.contains(keyword, case=False, regex=False, na=False)

    return data[found].reset_index(drop=True)

# Keeps records whose string matches the value exactly, it is not case-sensitive, ignores extra spaces
def filter_by_text(data, column_name, value):
    column_text = data[column_name].astype(str).str.strip().str.lower()

    return data[column_text == str(value).strip().lower()].reset_index(drop=True)

# Acts as a manager for all other filter functions
# Chooses the correct filter function for the column that the user chose
# Returns the rows that match
def filter_by_value(data, column_name, value):
    if column_name not in data.columns:
        return pd.DataFrame()

    if column_name == DEADLINE_FIELD:
        return filter_by_deadline(data, column_name, value)

    if pd.api.types.is_numeric_dtype(data[column_name]):
        return filter_by_minimum(data, column_name, value)

    if column_name == DATE_FIELD:
        return filter_by_date_range(data, column_name, value)

    if column_name in KEYWORD_COLUMNS:
        return filter_by_keyword(data, column_name, value)

    return filter_by_text(data, column_name, value)

# Converts score column into numbers, then sorts by it
# Highest number is first by default
def sort_by_urgency(table, ascending=False):
    if URGENCY_COLUMN in table.columns:
        table = table.copy()
        table[URGENCY_COLUMN] = pd.to_numeric(table[URGENCY_COLUMN], errors="coerce")
    return sort_by_column(table, URGENCY_COLUMN, ascending=ascending)

# Adds one report to the CSV file
def save_record(record):
    # Attempts to clean record
    cleaned = clean_record(record)
    if cleaned is None:
        return False, "Record rejected: missing or invalid required field."

    # Makes sure data folder exists
    os.makedirs(DATA_FOLDER, exist_ok=True)
    existing_data = load_data_from_csv(DATA_FILE)

    # File exists but couldn't be read: keep a backup instead of overwriting it
    if existing_data.empty and os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        os.replace(DATA_FILE, DATA_FILE.replace(".csv", "_backup.csv"))
        logger.warning("Unreadable data file backed up to '%s'.", DATA_FILE.replace(".csv", "_backup.csv"))

    # Checks if record is a duplicate
    if is_duplicate(existing_data, cleaned):
        return False, "Record rejected: an identical record already exists."

    new_row = pd.DataFrame([cleaned])

    # Creates a new DataFrame with the new row if existing_data is empty, otherwise concatenates the new row to existing_data
    table = new_row if existing_data.empty else pd.concat([existing_data, new_row], ignore_index=True)
    # Sort the table by urgency before saving
    table = sort_by_urgency(table)

    # Write a temporary file first to avoid data loss if the write fails, then replace the original if everything is good
    temp_file = DATA_FILE + ".tmp"
    try:
        table.to_csv(temp_file, index=False)
        os.replace(temp_file, DATA_FILE)
    except OSError as e:
        logger.error("Could not write '%s': %s", DATA_FILE, e)
        return False, "Record could not be saved (file write error)."

    return True, "Record saved."

# Reads all reports for display
# Loads the CSV file, cleans each row, drops invalid or duplicate rows
# Returns result sorted by urgency, does not change original file 
def load_records(ascending=False):
    table = load_data_from_csv(DATA_FILE)
    if table.empty:
        return table

    valid_records = []
    # Convert dataframe to a list of dictionaries
    for record in table.to_dict("records"):
        # Clean each row and only keep valid ones
        cleaned = clean_record(record)
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

    return sort_by_urgency(clean_table, ascending=ascending)

# Simple function to return all column headers in the CSV file
def get_column_names():
    return list(load_data_from_csv(DATA_FILE).columns)

# This function builds the list of filter options the user sees in the I/O menu
# For most columns, read the value from the file
# For score, date and deadline specifically, fixed menu options are given
def get_unique_values(column_name):
    # Loads the saved CSV, returns empty list if file is empty/unreadable or doesn't exist
    table = load_data_from_csv(DATA_FILE)
    if column_name not in table.columns:
        return []

    # Score column shows predefined ranges instead of showing every score in the file
    if column_name == URGENCY_COLUMN:
        ranges = []
        for i, threshold in enumerate(SCORE_THRESHOLDS):
            if i + 1 < len(SCORE_THRESHOLDS):
                ranges.append(f"{threshold} to under {SCORE_THRESHOLDS[i + 1]}")
            else:
                ranges.append(f"{threshold}+")
        return ranges           

    # Fixed windows are offered instead of showing every date
    if column_name == DATE_FIELD:
        return list(DATE_RANGES)

    # Fixed windows are offered instead of showing every date
    if column_name == DEADLINE_FIELD:
        return list(DEADLINE_FILTERS)

    # For any other column, list each distinct saved value once in alphabetical order
    return sorted(table[column_name].dropna().astype(str).unique())

# Function that io_manager calls once user has chosen a column and a value
# Every filtered result shown to user is sorted by urgency
def load_matching_records(column_name, value, ascending=False):
    # Loads all valid reports, already cleaned and sorted by urgency
    table = load_records(ascending=ascending)
    if table.empty: # Checks if empty, meaning if nothing is saved yet, so nothing to filter by
        return table

    # Keeps only the rows that match the chosen filter, sort by urgency is preserved
    return filter_by_value(table, column_name, value)