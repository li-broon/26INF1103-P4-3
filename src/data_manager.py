# ------- #
# Imports
# ------- #
import logging
import os

import pandas as pd
from datetime import datetime, timedelta

# ------------------ #
# Data Configuration
# ------------------ #

# Get Correct Data Directory no Matter Where the App is Run From
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")

# Sort by score means sorting by urgency 
URGENCY_COLUMN = "importance_score"

# Important fields that csv must contain
REQUIRED_FIELDS = ["reporter_name", "incident_date", URGENCY_COLUMN]
DATE_FIELD = "incident_date"
DATE_FORMAT = "%Y-%m-%d"

# Used for debugging to log warnings and errors instead of printing them to the console
logger = logging.getLogger(__name__)


# -------------------------- #
# Cleaning (Runtime)
# -------------------------- #
def clean_record(record):
    """
    cleans each column of a dataset, ensuring that required fields are present and valid, 
    and that text values are stripped of whitespace.

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
    """
    Convert a value into a standardized format for safe comparison.
    Numeric strings are converted to floats; text is lowercased and stripped.

    Parameters:
    value (any): The data value to convert.

    Returns:
    float | str: The processed value.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value).strip().lower()


def is_duplicate(existing_data, record):
    """
    Return True if every field of 'record' matches an existing row exactly

    Parameters:
    existing_data (pd.DataFrame): The DataFrame to check against.
    record (dict): The record to check for duplicates.

    Returns:
    bool: True if a duplicate is found, False otherwise.
    """
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
        
    return False


# -------------------------- #
# General Data Functions
# -------------------------- #
def load_data_from_csv(file_path):
    """
    Load data from a CSV file into a pandas DataFrame,
    handling errors and missing required columns.

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
            mask = data[column_name] >= float(value)
        except ValueError:
            return pd.DataFrame()
        
    elif column_name == "incident_date":
        now = datetime.now()
        
        # calculate the difference in days based on the value provided
        if value == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        elif value == "Last 30 Days":
            cutoff = now - timedelta(days=30)
        elif value == "Last 90 Days":
            cutoff = now - timedelta(days=90)
        elif value == "Last 180 Days":
            cutoff = now - timedelta(days=180)
        else:
            cutoff = now - timedelta(days=365)

        # Convert string dates to datetime objects for comparison, ignoring invalid dates
        dates = pd.to_datetime(data[column_name], format="%Y-%m-%d", errors="coerce")
        mask = dates >= cutoff

    elif column_name in ["location"]:
        # Adds matching locations to the filtered results, ignoring case and whitespace
        mask = data[column_name].astype(str).str.contains(str(value).strip(), case=False, na=False)

    else:
        # For columns that are strings, compare ignoring case and whitespace
        mask = data[column_name].astype(str).str.strip().str.lower() == str(value).strip().lower()

    return data[mask].reset_index(drop=True)


# -------------------------- #
# Specific Manager Functions
# -------------------------- #
def sort_by_urgency(table, ascending=False):
    """
    Sort a DataFrame by Urgency.
    
    Parameters:
    table (pd.DataFrame): The DataFrame to sort.
    ascending (bool): Whether to sort in ascending order (default is False, i.e., most urgent first).

    Returns:
    pd.DataFrame: The sorted DataFrame.
    """
    if URGENCY_COLUMN in table.columns:
        table = table.copy()
        table[URGENCY_COLUMN] = pd.to_numeric(table[URGENCY_COLUMN], errors="coerce")
    return sort_by_column(table, URGENCY_COLUMN, ascending=ascending)


def save_record(record):
    """
    Clean a dataset, reject duplicates, then add it to 'data.csv' sorted by urgency.

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
    # Creates a new DataFrame with the new row if existing_data is empty, otherwise concatenates the new row to existing_data
    table = new_row if existing_data.empty else pd.concat([existing_data, new_row], ignore_index=True)
    # Sort the table by urgency before saving
    table = sort_by_urgency(table)

    # Write a temporary file first to avoid data loss if the write fails, then replace the original
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
    Read all saved records from 'data.csv', clean them, reject invalid rows, 
    and return the valid dataset sorted by urgency.

    Parameters:
    ascending (bool): Sort direction based on the urgency column.

    Returns:
    pd.DataFrame: A cleaned and sorted DataFrame containing all valid incident reports.
    """
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


def get_column_names():
    """
    Retrieve all column headers currently present in the saved CSV database.

    Returns:
    list: A list of strings representing the column names.
    """
    return list(load_data_from_csv(DATA_FILE).columns)


def get_unique_values(column_name):
    """
    Extract distinct values from a specified column to populate user filter menus,
    providing custom threshold options for date and numeric score columns.

    Parameters:
    column_name (str): The name of the column to extract data from.

    Returns:
    list: A sorted list of unique strings or predefined threshold options.
    """
    table = load_data_from_csv(DATA_FILE)
    if column_name not in table.columns:
        return []

    # State threshold values for the range of urgency scores, instead of returning the actual unique values in the column
    if column_name == URGENCY_COLUMN:
        return ["0", "25", "50", "75", "100"]

    elif column_name == "incident_date":
        return ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last 365 Days"]
        
    return sorted(table[column_name].astype(str).unique())


def load_matching_records(column_name, value, ascending=False):
    """
    Retrieve a filtered subset of incident reports based on a specific column value or threshold.

    Parameters:
    column_name (str): The column to apply the filter against.
    value (str): The exact value, numeric threshold, or date boundary to search for.
    ascending (bool): Sort direction based on the urgency column.

    Returns:
    pd.DataFrame: A filtered and sorted DataFrame containing only the matching records.
    """
    table = load_records(ascending=ascending)
    if table.empty:
        return table

    return filter_by_value(table, column_name, value)