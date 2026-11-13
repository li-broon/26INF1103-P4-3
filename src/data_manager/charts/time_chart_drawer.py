# ------- #
# Imports
# ------- #

from abc import ABC

import pandas as pd

from src.data_manager.charts.chart_drawer import ChartDrawer
from src.data_manager.constants import COUNT_LABEL, DATE_FIELD, DATE_FORMAT, DETAIL_GID, MONTH_NAMES, YEAR_LABEL_PAD

# ----- #
# Class
# ----- #

# Base Class for the Charts that Group Incidents by Month and Year: Does the Date Handling and the Month Axis, Each Subclass Says What it Counts
class TimeChartDrawer(ChartDrawer, ABC):

    # The reports that have a valid date, with an extra "_month" column holding the month each one happened in
    @staticmethod
    def _dated(table: pd.DataFrame) -> pd.DataFrame:
        dates = pd.to_datetime(table[DATE_FIELD], format=DATE_FORMAT, errors="coerce")
        data = table.assign(_month=dates.dt.to_period("M"))
        return data.dropna(subset=["_month"])

    # Every month from January of the first year to December of the last year, so each year shows all 12 months
    @staticmethod
    def _month_range(months: pd.Series) -> pd.PeriodIndex:
        return pd.period_range(f"{months.min().year}-01", f"{months.max().year}-12", freq="M")

    # Labels the month axis (one tick per month) and writes each year under its months, with a dashed line between years.
    # The years are the axis' minor tick labels, so the layout makes room for them whatever the window size
    @staticmethod
    def _mark_months(ax, months: pd.PeriodIndex) -> None:
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels([MONTH_NAMES[month.month - 1] for month in months], rotation=90, fontsize=7)
        ax.set_xlim(-0.5, len(months) - 0.5)
        years = sorted({month.year for month in months})
        centers = []
        for year in years:
            positions = [i for i, month in enumerate(months) if month.year == year]
            if positions[0] > 0:
                ax.axvline(positions[0] - 0.5, color="grey", linewidth=0.8, linestyle="--")
            centers.append((positions[0] + positions[-1]) / 2)
        ax.set_xticks(centers, labels=[str(year) for year in years], minor=True)
        ax.tick_params(axis="x", which="minor", length=0, pad=YEAR_LABEL_PAD, labelsize=9)
        for label in ax.get_xticklabels(minor=True):
            label.set_fontweight("bold")

    # Draws one stacked bar per month, split by the values of group_column (e.g. each root cause), with the month's total on top
    def _draw_monthly_stacks(self, ax, data: pd.DataFrame, group_column: str, legend_title: str, title: str) -> None:
        from matplotlib.ticker import MaxNLocator
        months = self._month_range(data["_month"])
        grid = pd.crosstab(data["_month"], data[group_column]).reindex(months, fill_value=0)
        names = grid.sum().sort_values(ascending=False).index  # Biggest group at the bottom of each bar
        positions = list(range(len(months)))
        bottoms = [0] * len(months)
        for color, name in zip(self._palette(len(names)), names):
            values = grid[name].tolist()
            ax.bar(positions, values, bottom=bottoms, label=name, color=color, width=0.8)
            bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
        if len(months) <= 36:  # Beyond that the totals would overlap
            for position, total in zip(positions, bottoms):
                if total:
                    ax.text(position, total, str(total), ha="center", va="bottom", fontsize=7, gid=DETAIL_GID)
        ax.set_title(title)
        ax.set_ylabel(COUNT_LABEL)
        ax.set_ylim(0, max(bottoms) * 1.12 + 0.5)  # Room above the tallest bar for its total
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self._mark_months(ax, months)
        # A long legend gets two columns, so it is not taller than the chart
        ax.legend(title=legend_title, fontsize=8, title_fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1), ncol=1 if len(names) <= 8 else 2)
