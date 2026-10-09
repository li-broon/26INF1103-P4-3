# ------- #
# Imports
# ------- #
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

# -------------------------- #
# General Data Functions
# -------------------------- #

def save_data_to_csv(data, file_path):
    """
    Save the given data to a CSV file using append mode.

    Parameters:
    data (pd.DataFrame): The data to be saved.
    file_path (str): The path where the CSV file will be saved.
    """
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    df = pd.DataFrame(data)

    # Check if file exists and isn't empty to determine if we need to write headers
    file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
    df.to_csv(file_path, mode='a', header=not file_exists, index=False)


def load_data_from_csv(file_path):
    """
    Parameters:
    
    Loads data from CSV file and sends success or error message.
    file_path (str): The path of the CSV file to load.

    Returns:
    pd.DataFrame: The loaded data, or an empty DataFrame if loading failed/empty.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path, on_bad_lines='skip')  # Skip any bad lines instead of raising an error

        # 1. Standardize dates properly using format='mixed'
        # Enforce a strict YYYY-MM-DD format and coerce anything that doesn't comply
        df['incident_date'] = pd.to_datetime(
            df['incident_date'], 
            format='%Y-%m-%d', 
            errors='coerce'
        ).dt.strftime('%Y-%m-%d')

        # 2. Drop "ghost" rows that are missing critical information (like the reporter's name)
        df = df.dropna(subset=['reporter_name'])

        # 3. Drop exact duplicate rows
        df = df.drop_duplicates()

        # 4. Fill any remaining empty fields with "-" for safe printing
        df.fillna("-", inplace=True)

        # 5. Detect trailing spaces in string columns and strip them
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        # Detect rows where data shifted left, leaving importance_score empty (NaN)
        if df['importance_score'].isnull().any():
            corrupted_count = df['importance_score'].isnull().sum()
            print(f"Warning: Detected {corrupted_count} corrupted row(s) in '{file_path}'. Skipping bad data.")
            
            # Safely drop the corrupted rows so the rest of the app doesn't crash
            df = df.dropna(subset=['importance_score'])
        # ----------------------------

        print(f"Success: loaded data from '{file_path}'.")
        return df
        
    except pd.errors.ParserError:
        print(f"Error: the file '{file_path}' has extra columns and is badly formatted.")
    except PermissionError:
        print(f"Error: you don't have permission to read '{file_path}'.")
    except Exception as e:
        print(f"Error: an unexpected problem occurred while loading '{file_path}': {e}")

    return pd.DataFrame()


def sort_by_column(data, column_name, ascending=True):
    """
    Sort the given data by the specified column.

    Parameters:
    data (pd.DataFrame): The data to be sorted.
    column_name (str): The name of the column to sort by.

    Returns:
    pd.DataFrame: The sorted data.
    """
    if column_name not in data.columns:
        return data
        
    return data.sort_values(by=column_name, ascending=ascending, na_position="last").reset_index(drop=True)

# -------------------------- #
# Specific Manager Functions
# -------------------------- #

def sort_by_urgency(table, ascending=False):
    """Sort a Dataframe by Urgency, Most Urgent First"""
    return sort_by_column(table, URGENCY_COLUMN, ascending=ascending)


def save_record(record):
    """Add Record as New Row in 'data.csv' and maintain urgency sort"""
    os.makedirs(DATA_FOLDER, exist_ok=True)
    new_row = pd.DataFrame([record])

    # Load existing data safely using the general function
    existing_data = load_data_from_csv(DATA_FILE)

    if not existing_data.empty:
        table = pd.concat([existing_data, new_row], ignore_index=True)
    else:
        table = new_row

    # Keep the Table Sorted by Urgency (Highest First) Before Saving
    table = sort_by_urgency(table)
    
    # Overwrite the CSV so it remains fully sorted on disk 
    table.to_csv(DATA_FILE, index=False)


def resort_data_file(ascending=False):
    """Re-sort the Existing 'data.csv' on Disk (e.g. if the File was Edited Manually)"""
    table = load_data_from_csv(DATA_FILE)
    if table.empty:
        return table

    table = sort_by_urgency(table, ascending=ascending)
    table.to_csv(DATA_FILE, index=False)
    return table


def load_records(ascending=False):
    """
    Read All Saved Records from 'data.csv' and Return them Sorted by Urgency
    (Read-Only: Does Not Change the File. 'io_manager' Calls this to Display the Data)
    """
    table = load_data_from_csv(DATA_FILE)
    if table.empty:
        return table

    return sort_by_urgency(table, ascending=ascending)