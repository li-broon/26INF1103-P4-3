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

# Where each report's conversation is kept (one text file per report), and the column in data.csv that names the file
TRANSCRIPT_FOLDER = os.path.join(DATA_FOLDER, "transcripts")
TRANSCRIPT_ID_FIELD = "transcript_id"

# Shared Chart settings used by the Chart Classes

TOP_LOCATIONS = 10         # How many locations the location chart shows
MAX_STOPPAGE_HOURS = 24    # Same cap as logic_manager, so one odd value (e.g. 999) cannot flatten the chart

SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]
SEVERITY_COLORS = {"Low": "#7fb77e", "Medium": "#f2c14e", "High": "#f08a4b", "Critical": "#d1495b"}

UNKNOWN_PREFIX = "unknown"
BAR_COLOR = "#4c78a8"
COUNT_LABEL = "Number of incidents"

# Severity as a Number, so Mean and Median Can be Worked Out (Low = 1 ... Critical = 4)
SEVERITY_SCORES = {level: number for number, level in enumerate(SEVERITY_ORDER, start=1)}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OTHER_LABEL = "Other"      # Where the locations outside the top ones are grouped
MAX_LABEL_LENGTH = 28      # Longer location names are shortened so the legend stays readable

# How the Charts React when their Window is Resized (Used by ChartResizer and the Chart Drawers)
YEAR_LABEL_PAD = 22        # Points between the month labels and the year label under them (scaled with the window)
DETAIL_GID = "detail"      # Tag put on small numbers (bar totals, cell numbers) so they can be hidden when the window is too small for them
MIN_TEXT_SCALE = 0.6       # Text never shrinks below this fraction of its normal size
MAX_TEXT_SCALE = 1.6       # ...or grows beyond this one
DETAIL_MIN_SCALE = 0.7     # Below this fraction of the normal window size the small numbers are hidden instead of overlapping
MIN_TICK_FONT_SIZE = 6     # Points. Tick labels shrink to fit their room down to this size; below it every 2nd, 3rd... label is shown instead
TICK_LABEL_GAP = 1.5       # Points of clear space neighbouring tick labels must keep between them
