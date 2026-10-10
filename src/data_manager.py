# ------- #
# Imports
# ------- #
import logging
import os

import pandas as pd
from datetime import timedelta

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

# Indicates the boundary for each threshold filter in the urgency column.
SCORE_THRESHOLDS = ["0", "25", "50", "75", "100"]

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


def filter_by_minimum(data, column_name, value):
    """
    Keep the rows whose number in 'column_name' is at least 'value' (used for the score filter).

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): A numeric column.
    value (str): The minimum, e.g. "20". Not a number gives an empty DataFrame.

    Returns:
    pd.DataFrame: The matching rows.
    """
    try:
        minimum = float(value)
    except ValueError:
        return pd.DataFrame()

    return data[data[column_name] >= minimum].reset_index(drop=True)


def filter_by_date_range(data, column_name, value):
    """
    Keep the rows dated within the chosen window, counting back from today.

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): The date column (YYYY-MM-DD text).
    value (str): One of the labels in DATE_RANGES, e.g. "Last 7 Days". Anything else gives an empty DataFrame.

    Returns:
    pd.DataFrame: The matching rows. Rows with an invalid date are left out.
    """
    days = DATE_RANGES.get(value)
    if days is None:
        return pd.DataFrame()

    # Count from midnight today, so "Last 7 Days" includes a report dated exactly 7 days ago
    cutoff = pd.Timestamp.today().normalize() - timedelta(days=days)
    dates = pd.to_datetime(data[column_name], format=DATE_FORMAT, errors="coerce")

    return data[dates >= cutoff].reset_index(drop=True)


def filter_by_keyword(data, column_name, value):
    """
    Keep the rows whose text CONTAINS the keyword, ignoring case and extra spaces.
    The keyword is matched as string, so symbols such as ( ) [ ] + . are safe to type.

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): The column to search.
    value (str): The keyword, e.g. "warehouse". A blank keyword gives an empty DataFrame.

    Returns:
    pd.DataFrame: The matching rows.
    """
    keyword = str(value).strip()
    if keyword == "":
        return pd.DataFrame()

    found = data[column_name].astype(str).str.contains(keyword, case=False, regex=False, na=False)

    return data[found].reset_index(drop=True)


def filter_by_text(data, column_name, value):
    """
    Keep the rows whose string matches 'value' exactly, ignoring case and extra spaces.

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): The column to check.
    value (str): The text to match.

    Returns:
    pd.DataFrame: The matching rows.
    """
    column_text = data[column_name].astype(str).str.strip().str.lower()

    return data[column_text == str(value).strip().lower()].reset_index(drop=True)


def filter_by_value(data, column_name, value):
    """
    Return the rows of data that match the chosen filter value. How the value is
    matched depends on the column:
      - number columns (e.g. score): the row's number is AT LEAST the value
      - the date column: the row is dated within the chosen "Last N no. of days" window
      - keyword columns (e.g. location): the text contains the keyword (ignoring case and extra spaces)
      - every other column: the text matches exactly (ignoring case and extra spaces)

    Parameters:
    data (pd.DataFrame): The data to filter.
    column_name (str): The column to check.
    value (str): The value picked by the user.

    Returns:
    pd.DataFrame: The matching rows, or an empty DataFrame if the column doesn't
    exist or the value is not valid for that column.
    """
    if column_name not in data.columns:
        return pd.DataFrame()

    if pd.api.types.is_numeric_dtype(data[column_name]):
        return filter_by_minimum(data, column_name, value)

    if column_name == DATE_FIELD:
        return filter_by_date_range(data, column_name, value)

    if column_name in KEYWORD_COLUMNS:
        return filter_by_keyword(data, column_name, value)

    return filter_by_text(data, column_name, value)


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


def get_unique_values(column_name: str) -> list[str]:
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

    # Score and date offer fixed choices instead of every unique value saved in the column
    if column_name == URGENCY_COLUMN:
        return list(SCORE_THRESHOLDS)

    if column_name == DATE_FIELD:
        return list(DATE_RANGES)

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