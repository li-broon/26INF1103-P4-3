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

# Column used to keep data.csv sorted by urgency - change this if your
# urgency/priority field is named something else.
URGENCY_COLUMN = "importance_score"  # Must Match the Name 'logic_manager' Saves the Score Under

# -------------------------- #
# data_manager Main Functions
# -------------------------- #

# Add Record as New Row in 'data.csv'
def save_record(record):
    
    # Create Directory if it Doesn't Exist
    os.makedirs(DATA_FOLDER, exist_ok=True)
    
    # Convert JSON into Pandas Dataframe
    new_row = pd.DataFrame([record])

    # If 'data.csv' Exists and is Not Empty, Concat the Old Data with the New Data
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        table = pd.concat([pd.read_csv(DATA_FILE), new_row], ignore_index=True)
    
    # Else, Start new Table
    else:
        table = new_row

    # Keep the Table Sorted by Urgency (Highest First) Before Saving
    table = sort_by_urgency(table)
    
    # Export CSV
    table.to_csv(DATA_FILE, index=False)

# Sort a Dataframe by Urgency, Most Urgent First
def sort_by_urgency(table, ascending=False):

    # If the Urgency Column Isn't Present Yet, Return Unsorted (Nothing to Sort By)
    if URGENCY_COLUMN not in table.columns:
        return table

    return table.sort_values(URGENCY_COLUMN, ascending=ascending, na_position="last").reset_index(drop=True)


# Re-sort the Existing 'data.csv' on Disk (e.g. if the File was Edited Manually)
def resort_data_file(ascending=False):

    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return pd.DataFrame()

    table = sort_by_urgency(pd.read_csv(DATA_FILE), ascending=ascending)
    table.to_csv(DATA_FILE, index=False)
    return table


# Read All Saved Records from 'data.csv' and Return them Sorted by Urgency
# (Read-Only: Does Not Change the File. 'io_manager' Calls this to Display the Data)
def load_records(ascending=False):

    # If 'data.csv' Doesn't Exist or is Empty, Return an Empty Table (Nothing Saved Yet)
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return pd.DataFrame()

    # Read the CSV into a Dataframe and Sort it (Most Urgent First)
    table = pd.read_csv(DATA_FILE)
    return sort_by_urgency(table, ascending=ascending)
