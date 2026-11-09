import pandas as pd

from src.data_manager.constants import DATE_FORMAT, DATE_FIELD

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