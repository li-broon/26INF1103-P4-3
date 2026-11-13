# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.charts.time_chart_drawer import TimeChartDrawer
from src.data_manager.constants import COUNT_LABEL, DATE_FIELD, MONTH_NAMES

# ----- #
# Class
# ----- #

# Incidents per month: one line for each year (Jan to Dec), so the years can be compared
class MonthlyChart(TimeChartDrawer):

    def __init__(self) -> None:
        super().__init__("monthly", "Incidents per month, per year", (DATE_FIELD,))

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        from matplotlib.ticker import MaxNLocator
        data = self._dated(table)
        if data.empty:
            return False
        months = data["_month"]
        counts = months.value_counts()
        years = sorted(int(year) for year in months.dt.year.unique())
        last_month = int(months[months.dt.year == years[-1]].dt.month.max())  # The latest year stops at its last month, so later months do not look like zero incidents

        highest = 0
        for color, year in zip(self._palette(len(years)), years):
            shown = last_month if year == years[-1] else 12
            values = [int(counts.get(pd.Period(year=year, month=month, freq="M"), 0)) for month in range(1, shown + 1)]
            highest = max(highest, max(values))
            ax.plot(range(shown), values, marker="o", color=color, label=f"{year} ({sum(values)} incidents)")
            for position, value in enumerate(values):
                ax.annotate(str(value), (position, value), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7, color=color)

        ax.set_xticks(range(12))
        ax.set_xticklabels(MONTH_NAMES)
        ax.set_ylim(0, highest + 1)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylabel(COUNT_LABEL)
        ax.set_title(self._title)
        ax.legend(title="Year", fontsize=8, title_fontsize=8)
        return True
