# --Shared Report Settings Used by the Data Manager Classes (No Class Here, so Any Class File Can Import These Without Importing Each Other)-- #

import os

# Sorting by score means sorting by urgency 
URGENCY_COLUMN = "importance_score"

# Important fields that csv must contain, or the csv is rejected
REQUIRED_FIELDS = ["reporter_name", "incident_date", URGENCY_COLUMN]

# The date column and its format (e.g. 2026-12-5)
DATE_FIELD = "incident_date"
DATE_FORMAT = "%Y-%m-%d"

# The MOM deadline column ("N/A" for reports that do not need a MOM report)
DEADLINE_FIELD = "deadline"

# Finds the project's data folder no matter where the app is launched from (two levels up from src/data_manager/)
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")