# ------- #
# Imports
# ------- #

from src.data_manager.filters.date_range_filter import DateRangeFilter
from src.data_manager.filters.deadline_filter import DeadlineFilter
from src.data_manager.filters.keyword_filter import KeywordFilter
from src.data_manager.filters.report_filter import ReportFilter
from src.data_manager.filters.score_band_filter import ScoreBandFilter


# Columns that are searched for keywords (location)
KEYWORD_COLUMNS = ["location"]

# ---------- #
# Function
# ---------- #

# Builds the filters the app uses, one per column, as a dictionary of column name -> filter
# The DataManager is given this dictionary. Any column that is not in it is matched on its exact text
def create_default_filters() -> dict[str, ReportFilter]:
    column_filters = [ScoreBandFilter(), DateRangeFilter(), DeadlineFilter()]
    for column in KEYWORD_COLUMNS:
        column_filters.append(KeywordFilter(column))

    filters = {}
    for column_filter in column_filters:
        filters[column_filter.column] = column_filter
    return filters
