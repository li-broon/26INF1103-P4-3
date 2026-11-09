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

# Shared Chart settings used by the Chart Classes

TOP_LOCATIONS = 10         # How many locations the location chart shows
MAX_STOPPAGE_HOURS = 24    # Same cap as logic_manager, so one odd value (e.g. 999) cannot flatten the chart

SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]
SEVERITY_COLORS = {"Low": "#7fb77e", "Medium": "#f2c14e", "High": "#f08a4b", "Critical": "#d1495b"}

UNKNOWN_PREFIX = "unknown"
BAR_COLOR = "#4c78a8"
COUNT_LABEL = "Number of Incidents"