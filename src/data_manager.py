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
    
    # Export CSV
    table.to_csv(DATA_FILE, index=False)
