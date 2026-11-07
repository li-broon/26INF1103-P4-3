# --Shared Report Settings Used by the Data Manager Classes-- #
# This file has no class, so every class file can import these without importing each other

import os

# Sorting by score means sorting by urgency 
URGENCY_COLUMN = "importance_score"

# Important fields that csv must contain, or the csv is rejected
REQUIRED_FIELDS = ["reporter_name", "incident_date", URGENCY_COLUMN]

# The date column and its format (e.g. 2026-12-5)
DATE_FIELD = "incident_date"
DATE_FORMAT = "%Y-%m-%d"

# Gets correct data directory no matter where application is launched from
# (this file is in src/data_manager/, so go up two levels to reach the project's data folder)
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")