# ------- #
# Imports
# ------- #
import logging
import os

import pandas as pd

# ------------------ #
# Data Configuration
# ------------------ #

# Get Correct Data Directory no Matter Where the App is Run From
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")

# Column used to keep data.csv sorted by urgency
URGENCY_COLUMN = "importance_score"  # Must Match the Name 'logic_manager' Saves the Score Under

# Fields every record must have before it is allowed into data.csv
REQUIRED_FIELDS = ["reporter_name", "incident_date", URGENCY_COLUMN]
DATE_FIELD = "incident_date"
DATE_FORMAT = "%Y-%m-%d"

# 'logging' is used for diagnostics because all console output lives in 'io_manager'
logger = logging.getLogger(__name__)


# -------------------------- #
# Cleaning (Runtime)
# -------------------------- #
def clean_record(record):
    """
    Normalize ONE record before it is saved. This is the last safety net;
    user input is validated in 'io_manager' and AI output in 'ai_manager'.

    Parameters:
    record (dict): The record to clean.

    Returns:
    dict | None: The cleaned record, or None if a required field is missing/invalid.
    """
    if not isinstance(record, dict):
        return None

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
        cleaned[DATE_FIELD] = pd.to_datetime(
            cleaned[DATE_FIELD], format=DATE_FORMAT
        ).strftime(DATE_FORMAT)
        cleaned[URGENCY_COLUMN] = float(cleaned[URGENCY_COLUMN])
    except (ValueError, TypeError):
        return None

    return cleaned


def comparable(value):
    """Turns float type values into floats, and everything else into lowercase stripped strings"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value).strip().lower()


def is_duplicate(existing_data, record):
    """Return True if every field of 'record' matches an existing row exactly"""
    # If the existing data is empty, there can't be a duplicate
    if existing_data.empty:
        return False

    for row in existing_data.to_dict("records"):
        row_matches = True  # Assume a match until a field proves otherwise

        for field, new_value in record.items():
            if comparable(row.get(field)) != comparable(new_value):
                row_matches = False
                break

        if row_matches:
            return True
        
    return False


# -------------------------- #
# General Data Functions
# -------------------------- #
def load_data_from_csv(file_path):
    """
    Load a CSV file WITHOUT cleaning or deleting anything.
    Missing, empty, unreadable or wrongly-structured files give an empty DataFrame.

    Parameters:
    file_path (str): The path of the CSV file to load.

    Returns:
    pd.DataFrame: The loaded data, or an empty DataFrame if loading failed/empty.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path)
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

    missing = [col for col in REQUIRED_FIELDS if col not in df.columns]
    if missing:
        logger.warning("File '%s' is missing required columns: %s", file_path, missing)
        return pd.DataFrame()

    return df


def sort_by_column(data, column_name, ascending=True):
    """
    Sort the given data by the specified column.

    Parameters:
    data (pd.DataFrame): The data to be sorted.
    column_name (str): The name of the column to sort by.
    ascending (bool): Sort direction.

    Returns:
    pd.DataFrame: The sorted data.
    """
    if column_name not in data.columns:
        return data

    return data.sort_values(by=column_name, ascending=ascending, na_position="last").reset_index(drop=True)


def filter_by_value(data, column_name, value):
    """
    Return all rows where the given column matches the given value.

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): The column to check.
    value: The value to match. Text is compared ignoring case and extra spaces.

    Returns:
    pd.DataFrame: The matching rows, or an empty DataFrame if the column
    doesn't exist or the value is invalid for that column.
    """
    if column_name not in data.columns:
        return pd.DataFrame()

    if pd.api.types.is_numeric_dtype(data[column_name]):
        try:
            mask = data[column_name] == float(value)
        except ValueError:
            return pd.DataFrame()
    else:
        mask = data[column_name].astype(str).str.strip().str.lower() == str(value).strip().lower()

    return data[mask].reset_index(drop=True)


# -------------------------- #
# Specific Manager Functions
# -------------------------- #
def sort_by_urgency(table, ascending=False):
    """Sort a DataFrame by Urgency, Most Urgent First (non-numeric scores go last)"""
    if URGENCY_COLUMN in table.columns:
        table = table.copy()
        table[URGENCY_COLUMN] = pd.to_numeric(table[URGENCY_COLUMN], errors="coerce")
    return sort_by_column(table, URGENCY_COLUMN, ascending=ascending)


def save_record(record):
    """
    Clean a record, reject duplicates, then add it to 'data.csv' sorted by urgency.

    Parameters:
    record (dict): The processed record to save.

    Returns:
    tuple[bool, str]: (success, message). 'io_manager' decides whether to print the message.
    """
    cleaned = clean_record(record)
    if cleaned is None:
        return False, "Record rejected: missing or invalid required field."

    os.makedirs(DATA_FOLDER, exist_ok=True)
    existing_data = load_data_from_csv(DATA_FILE)

    # File exists but couldn't be read: keep a backup instead of overwriting it
    if existing_data.empty and os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        os.replace(DATA_FILE, DATA_FILE + ".bak")
        logger.warning("Unreadable data file backed up to '%s.bak'.", DATA_FILE)

    if is_duplicate(existing_data, cleaned):
        return False, "Record rejected: an identical record already exists."

    new_row = pd.DataFrame([cleaned])
    table = new_row if existing_data.empty else pd.concat([existing_data, new_row], ignore_index=True)
    table = sort_by_urgency(table)

    # Write to a temp file first so an interrupted write can't corrupt data.csv
    temp_file = DATA_FILE + ".tmp"
    try:
        table.to_csv(temp_file, index=False)
        os.replace(temp_file, DATA_FILE)
    except OSError as e:
        logger.error("Could not write '%s': %s", DATA_FILE, e)
        return False, "Record could not be saved (file write error)."

    return True, "Record saved."


def load_records(ascending=False):
    """
    Read All Saved Records from 'data.csv', clean out any manual corruption 
    in memory, and Return them Sorted by Urgency.
    """
    table = load_data_from_csv(DATA_FILE)
    if table.empty:
        return table

    # 1. Run every loaded row through your existing clean_record function
    valid_records = []
    for record in table.to_dict("records"):
        cleaned = clean_record(record)
        # 2. Only keep rows that pass validation (rejects None)
        if cleaned is not None:
            valid_records.append(cleaned)
            
    # If all rows were corrupt, return empty
    if not valid_records:
        return pd.DataFrame()

    # 3. Convert back to DataFrame and sort
    clean_table = pd.DataFrame(valid_records)
    
    # 4. (Optional but recommended) Drop exact duplicates that might have been pasted in manually
    clean_table = clean_table.drop_duplicates()

    return sort_by_urgency(clean_table, ascending=ascending)


def get_column_names():
    """Return the column names in 'data.csv' so the user can choose from them"""
    return list(load_data_from_csv(DATA_FILE).columns)


def get_unique_values(column_name):
    """Return the distinct values in a column so the user can see what they can filter by"""
    table = load_data_from_csv(DATA_FILE)
    if column_name not in table.columns:
        return []
    return sorted(table[column_name].astype(str).unique())


def load_matching_records(column_name, value, ascending=False):
    """Read 'data.csv' sorted by urgency and keep only rows where column_name equals value.
    Returns an empty DataFrame when nothing matches; 'io_manager' prints the 'no results' message."""
    table = load_records(ascending=ascending)
    if table.empty:
        return table

    return filter_by_value(table, column_name, value)