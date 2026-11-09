from abc import ABC, abstractmethod

import pandas as pd

from src.data_manager.constants import BAR_COLOR, COUNT_LABEL, UNKNOWN_PREFIX

# Base Class for the Charts the User can ask for (one per Chart): Does the Shared Checks and Helpers, Each Subclass only says how its Chart is drawn
class ChartDrawer(ABC):

    # key is the name the user types (e.g. "severity"), title is the text shown in the chart menu and above an empty chart
    # required_columns are the columns this chart needs; if one is missing the chart says "No data to show" instead of crashing
    def __init__(self, key: str, title: str, required_columns: tuple[str, ...] = ()) -> None:
        self._key = key
        self._title = title
        self._required_columns = required_columns

    # The name of this chart (read only)
    @property
    def key(self) -> str:
        return self._key

    # The menu text of this chart (read only)
    @property
    def title(self) -> str:
        return self._title

    # Draws the chart on ax. Returns False if there is nothing to draw (missing column or no data)
    def draw(self, ax, table: pd.DataFrame) -> bool:
        if any(column not in table.columns for column in self._required_columns):
            return False
        return self._draw(ax, table)

    # How this chart is drawn (Every Subclass Must Say)
    @abstractmethod
    def _draw(self, ax, table: pd.DataFrame) -> bool:
        pass

    # Counts each value in a column, leaving out blanks and "unknown ..." answers
    @staticmethod
    def _count_values(table: pd.DataFrame, column: str) -> pd.Series:
        values = table[column].dropna().astype(str).str.strip()
        values = values[(values != "") & ~values.str.lower().str.startswith(UNKNOWN_PREFIX)]
        return values.value_counts()

    # Draws a bar chart with the count written on each bar. Returns False if there is nothing to draw
    @staticmethod
    def _draw_bars(ax, counts: pd.Series, title: str, xlabel: str, horizontal: bool = False, colors=None) -> bool:
        from matplotlib.ticker import MaxNLocator
        if counts.empty:
            return False
        labels = [str(label) for label in counts.index]
        if horizontal:
            bars = ax.barh(labels, counts.values, color=colors or BAR_COLOR)
            ax.invert_yaxis()  # Biggest bar on top
            ax.set_xlabel(xlabel)
        else:
            bars = ax.bar(labels, counts.values, color=colors or BAR_COLOR)
            ax.set_ylabel(xlabel)
            ax.tick_params(axis="x", rotation=30)
        ax.bar_label(bars, padding=2)
        ax.set_title(title)
        if xlabel == COUNT_LABEL:
            # Counts are whole incidents, so never show ticks like 12.5
            (ax.xaxis if horizontal else ax.yaxis).set_major_locator(MaxNLocator(integer=True))
        return True