# Imports
import pandas as pd
from datetime import timedelta

from src.data_manager.constants import DATE_FIELD, DATE_FORMAT, DEADLINE_FIELD, URGENCY_COLUMN
# The filter choices now live with their filter classes (these imports go once DataManager uses the filter objects)
from src.data_manager.filters.date_range_filter import DATE_RANGES
from src.data_manager.filters.deadline_filter import DEADLINE_FILTERS
from src.data_manager.filters.score_band_filter import SCORE_THRESHOLDS
from src.data_manager.storage.record_store import RecordStore

# Columns that are searched for keywords (location)
KEYWORD_COLUMNS = ["location"]

CHART_OPTIONS = {
    "severity": "Incidents by severity",
    "root_cause": "Incidents by root cause",
    "monthly": "Incidents per month",
    "location": "Top 10 locations",
    "hospitalised": "Hospitalised vs not hospitalised",
    "language": "Languages reports were made in",
    "severity_by_cause": "Severity within each root cause",
    "stoppage": "Average work stoppage hours by root cause",
}

TOP_LOCATIONS = 10         # How many locations the location chart shows
MAX_STOPPAGE_HOURS = 24    # Same cap as logic_manager, so one odd value (e.g. 999) cannot flatten the chart

SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]
SEVERITY_COLORS = {"Low": "#7fb77e", "Medium": "#f2c14e", "High": "#f08a4b", "Critical": "#d1495b"}

UNKNOWN_PREFIX = "unknown"


# The one place the rest of the app goes to save, read and filter incident reports
# The reports themselves are kept by a RecordStore that is passed in
class DataManager:

    # store is where the reports are kept (a CSV file in the app). It is passed in, not created here,
    # so the DataManager can work with any RecordStore
    def __init__(self, store: RecordStore):
        self._store = store

    # Saves one report. Returns (success, message)
    def save_record(self, record):
        return self._store.save_record(record)

    # Reads all saved reports, sorted by urgency (highest first by default)
    def load_records(self, ascending=False):
        return self._store.load_records(ascending=ascending)

    # Returns all column headers of the saved reports
    def get_column_names(self):
        return self._store.get_column_names()

    def filter_by_minimum(self, data, column_name, value):
        try:
            # Extract the selected threshold from value which is the range (0-24 etc.)
            raw_value = str(value).split()[0].replace("+", "")
            minimum = float(raw_value)
            min_index = SCORE_THRESHOLDS.index(raw_value)

            # next_threshold is the threshold in the SCORE_THRESHOLDS list after the selected threshold
            next_threshold = float(SCORE_THRESHOLDS[min_index + 1]) if min_index + 1 < len(SCORE_THRESHOLDS) else None

            if next_threshold is not None:
                # Keep the values within the threshold range
                data = data[(data[column_name] >= minimum) & (data[column_name] < next_threshold)]
            else:
                # No next threshold, so just filter by the minimum
                data = data[data[column_name] >= minimum]

        # Returns empty table if non-numeric value or value not found in table is found
        except ValueError:
            return pd.DataFrame()

        return data.reset_index(drop=True)

    # Keeps records from the last N days
    def filter_by_date_range(self, data, column_name, value):
        days = DATE_RANGES.get(value)
        # Returns empty table if unknown label
        if days is None:
            return pd.DataFrame()

        # Count from midnight today, so "Last 7 Days" includes a report dated exactly 7 days ago
        cutoff = pd.Timestamp.today().normalize() - timedelta(days=days)
        dates = pd.to_datetime(data[column_name], format=DATE_FORMAT, errors="coerce")

        return data[dates >= cutoff].reset_index(drop=True)

    # Keeps records whose MOM deadline fall within a window
    def filter_by_deadline(self, data, column_name, value):
        # Deadline windows are gotten from DEADLINE_FILTERS
        limits = DEADLINE_FILTERS.get(value)
        if limits is None:
            return pd.DataFrame()

        earliest, latest = limits
        today = pd.Timestamp.today().normalize()
        deadlines = pd.to_datetime(data[column_name], format=DATE_FORMAT, errors="coerce")
        days_left = (deadlines - today).dt.days # "N/A" or invalid deadlines become blanks

        keep = days_left.notna()  # No valid deadline means no match
        if earliest is not None:
            keep &= days_left >= earliest
        if latest is not None:
            keep &= days_left <= latest

        return data[keep].reset_index(drop=True)

    # Keeps records containing the typed keyword, it is not case-sensitive, ignores extra spaces
    def filter_by_keyword(self, data, column_name, value):
        keyword = str(value).strip()
        # Blank keyword returns empty table
        if keyword == "":
            return pd.DataFrame()

        # Regex false means symbols like () + , are treated as plain characters, safe to type
        found = data[column_name].astype(str).str.contains(keyword, case=False, regex=False, na=False)

        return data[found].reset_index(drop=True)

    # Keeps records whose string matches the value exactly, it is not case-sensitive, ignores extra spaces
    def filter_by_text(self, data, column_name, value):
        column_text = data[column_name].astype(str).str.strip().str.lower()

        return data[column_text == str(value).strip().lower()].reset_index(drop=True)

    # Acts as a manager for all other filter functions
    # Chooses the correct filter function for the column that the user chose
    # Returns the rows that match
    def filter_by_value(self, data, column_name, value):
        if column_name not in data.columns:
            return pd.DataFrame()

        if column_name == DEADLINE_FIELD:
            return self.filter_by_deadline(data, column_name, value)

        if pd.api.types.is_numeric_dtype(data[column_name]):
            return self.filter_by_minimum(data, column_name, value)

        if column_name == DATE_FIELD:
            return self.filter_by_date_range(data, column_name, value)

        if column_name in KEYWORD_COLUMNS:
            return self.filter_by_keyword(data, column_name, value)

        return self.filter_by_text(data, column_name, value)

    # This function builds the list of filter options the user sees in the I/O menu
    # For most columns, read the value from the file
    # For score, date and deadline specifically, fixed menu options are given
    def get_unique_values(self, column_name):
        # Loads the saved reports, returns empty list if nothing is saved or the file is unreadable
        table = self.load_records()
        if column_name not in table.columns:
            return []

        # Score column shows predefined ranges instead of showing every score in the file
        if column_name == URGENCY_COLUMN:
            ranges = []
            for i, threshold in enumerate(SCORE_THRESHOLDS):
                if i + 1 < len(SCORE_THRESHOLDS):
                    ranges.append(f"{threshold} to under {SCORE_THRESHOLDS[i + 1]}")
                else:
                    ranges.append(f"{threshold}+")
            return ranges           

        # Fixed windows are offered instead of showing every date
        if column_name == DATE_FIELD:
            return list(DATE_RANGES)

        # Fixed windows are offered instead of showing every date
        if column_name == DEADLINE_FIELD:
            return list(DEADLINE_FILTERS)

        # For any other column, list each distinct saved value once in alphabetical order
        return sorted(table[column_name].dropna().astype(str).unique())

    # Function that io_manager calls once user has chosen a column and a value
    # Every filtered result shown to user is sorted by urgency
    def load_matching_records(self, column_name, value, ascending=False):
        # Loads all valid reports, already cleaned and sorted by urgency
        table = self.load_records(ascending=ascending)
        if table.empty: # Checks if empty, meaning if nothing is saved yet, so nothing to filter by
            return table

        # Keeps only the rows that match the chosen filter, sort by urgency is preserved
        return self.filter_by_value(table, column_name, value)

    def get_chart_options(self):
        return list(CHART_OPTIONS.items())
 
    # Counts each value in a column, leaving out blanks and "unknown ..." answers
    def _count_values(self, table, column):
        values = table[column].dropna().astype(str).str.strip()
        values = values[(values != "") & ~values.str.lower().str.startswith(UNKNOWN_PREFIX)]
        return values.value_counts()
 
    # Draws a bar chart with the count written on each bar. Returns False if there is nothing to draw
    def _draw_bars(self, ax, counts, title, xlabel, horizontal=False, colors=None):
        from matplotlib.ticker import MaxNLocator
        if counts.empty:
            return False
        labels = [str(label) for label in counts.index]
        if horizontal:
            bars = ax.barh(labels, counts.values, color=colors or "#4c78a8")
            ax.invert_yaxis()  # Biggest bar on top
            ax.set_xlabel(xlabel)
        else:
            bars = ax.bar(labels, counts.values, color=colors or "#4c78a8")
            ax.set_ylabel(xlabel)
            ax.tick_params(axis="x", rotation=30)
        ax.bar_label(bars, padding=2)
        ax.set_title(title)
        if xlabel == "Number of incidents":
            # Counts are whole incidents, so never show ticks like 12.5
            (ax.xaxis if horizontal else ax.yaxis).set_major_locator(MaxNLocator(integer=True))
        return True
 
    def _draw_severity(self, ax, table):
        counts = self._count_values(table, "ai_severity").reindex(SEVERITY_ORDER).dropna().astype(int)
        colors = [SEVERITY_COLORS[level] for level in counts.index]
        return self._draw_bars(ax, counts, "Incidents by severity", "Number of incidents", colors=colors)
 
    def _draw_root_cause(self, ax, table):
        counts = self._count_values(table, "root_cause_category")
        return self._draw_bars(ax, counts, "Incidents by root cause", "Number of incidents", horizontal=True)
 
    def _draw_monthly(self, ax, table):
        dates = pd.to_datetime(table[DATE_FIELD], format=DATE_FORMAT, errors="coerce").dropna()
        if dates.empty:
            return False
        counts = dates.dt.to_period("M").value_counts().sort_index()
        # Include months with no incidents, so gaps show as 0 instead of being skipped
        counts = counts.reindex(pd.period_range(counts.index.min(), counts.index.max(), freq="M"), fill_value=0)
        labels = [str(month) for month in counts.index]
        ax.plot(labels, counts.values, marker="o", color="#4c78a8")
        for x, y in zip(labels, counts.values):
            ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 6), ha="center")
        ax.set_title("Incidents per month")
        ax.set_ylabel("Number of incidents")
        ax.set_ylim(0, counts.max() + 1)
        ax.tick_params(axis="x", rotation=45)
        return True
 
    def _draw_location(self, ax, table):
        counts = self._count_values(table, "location").head(TOP_LOCATIONS)
        return self._draw_bars(ax, counts, f"Top {TOP_LOCATIONS} locations", "Number of incidents", horizontal=True)
 
    def _draw_hospitalised(self, ax, table):
        if "hospitalised" not in table.columns:
            return False
        flags = table["hospitalised"].astype(str).str.strip().str.lower() == "true"
        counts = {"Hospitalised": int(flags.sum()), "Not hospitalised": int((~flags).sum())}
        counts = {label: n for label, n in counts.items() if n > 0}
        if not counts:
            return False
        ax.pie(counts.values(), labels=counts.keys(), autopct="%1.0f%%", startangle=90,
               colors=["#d1495b", "#7fb77e"][:len(counts)] if len(counts) == 2 else None)
        ax.set_title("Hospitalised vs not hospitalised")
        return True
 
    def _draw_language(self, ax, table):
        counts = self._count_values(table, "detected_language")
        if counts.empty:
            return False
        ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90)
        ax.set_title("Languages reports were made in")
        return True
 
    def _draw_severity_by_cause(self, ax, table):
        needed = ("root_cause_category", "ai_severity")
        if any(col not in table.columns for col in needed):
            return False
        data = table.dropna(subset=needed)
        if data.empty:
            return False
        grid = pd.crosstab(data["root_cause_category"], data["ai_severity"])
        levels = [level for level in SEVERITY_ORDER if level in grid.columns]
        grid = grid[levels]
        grid = grid.loc[grid.sum(axis=1).sort_values().index]  # Biggest cause ends up on top
        grid.plot(kind="barh", stacked=True, ax=ax, color=[SEVERITY_COLORS[l] for l in levels])
        ax.set_title("Severity within each root cause")
        ax.set_xlabel("Number of incidents")
        ax.set_ylabel("")
        ax.legend(title="Severity")
        return True
 
    def _draw_stoppage(self, ax, table):
        needed = ("root_cause_category", "work_stoppage_hours")
        if any(col not in table.columns for col in needed):
            return False
        data = table[list(needed)].copy()
        data["work_stoppage_hours"] = pd.to_numeric(data["work_stoppage_hours"], errors="coerce").clip(upper=MAX_STOPPAGE_HOURS)
        averages = data.dropna().groupby("root_cause_category")["work_stoppage_hours"].mean().sort_values(ascending=False).round(1)
        return self._draw_bars(ax, averages, f"Average work stoppage by root cause (capped at {MAX_STOPPAGE_HOURS}h)",
                               "Hours", horizontal=True)
 
    # Shows the chart the user asked for.
    # chart_name   : a key of CHART_OPTIONS, or "all" for every chart on one page
    # filter_column, filter_value : optional, chart only the reports matching this filter
    #                (same columns and values as the filter menu, e.g. "ai_severity", "Critical")
    # save_path    : optional, save the picture to this file instead of opening a window
    # Returns (success, message), like save_record, so io_manager can print the message
    def show_chart(self, chart_name, filter_column=None, filter_value=None, save_path=None):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.ticker import MaxNLocator
        except ImportError:
            return False, "matplotlib is not installed. Run: pip install matplotlib"
 
        chart_name = str(chart_name).strip().lower()
        if chart_name != "all" and chart_name not in CHART_OPTIONS:
            return False, f"Unknown chart '{chart_name}'. Choose from: all, " + ", ".join(CHART_OPTIONS)
 
        # Load all reports, or only the ones matching the filter
        if filter_column is not None:
            table = self.load_matching_records(filter_column, filter_value)
        else:
            table = self.load_records()
        if table.empty:
            return False, "No reports to chart" + (" for that filter." if filter_column is not None else " yet.")
 
        names = list(CHART_OPTIONS) if chart_name == "all" else [chart_name]
        columns = 2 if len(names) > 1 else 1
        rows = -(-len(names) // columns)
        fig, axes = plt.subplots(rows, columns, figsize=(7 * columns, 4.5 * rows), squeeze=False)
        axes = axes.flatten()
 
        drawn = 0
        for ax, name in zip(axes, names):
            if getattr(self, f"_draw_{name}")(ax, table):
                drawn += 1
            else:
                ax.set_title(CHART_OPTIONS[name])
                ax.text(0.5, 0.5, "No data to show", ha="center", va="center", transform=ax.transAxes)
                ax.axis("off")
        for ax in axes[len(names):]:
            ax.axis("off")  # Hide any unused slot in the grid
 
        heading = f"Incident Reports ({len(table)} reports)"
        if filter_column is not None:
            heading += f" where {filter_column} = {filter_value}"
        fig.suptitle(heading, fontsize=14, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.97))  # Leave room for the main title
 
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return True, f"Chart saved to {save_path}"
 
        plt.show()  # Blocks until the window is closed
        plt.close(fig)
        return True, "Chart closed."