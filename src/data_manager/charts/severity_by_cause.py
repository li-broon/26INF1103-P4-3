# ------- #
# Imports
# ------- #

import numpy as np
import pandas as pd

from src.data_manager.constants import SEVERITY_ORDER, SEVERITY_SCORES
from src.data_manager.charts.time_chart_drawer import TimeChartDrawer
from src.data_manager.constants import DATE_FIELD

# ----- #
# Class
# ----- #

# How severe each root cause is on average, in three panels. Severity is a number: Low = 1, Medium = 2, High = 3, Critical = 4.
#   1. per year   : bars for the mean and a diamond for the median, one group per root cause
#   2. per month  : heat map of the mean (every year laid out Jan to Dec)
#   3. per month  : heat map of the median
class SeverityByCauseChart(TimeChartDrawer):

    def __init__(self) -> None:
        super().__init__("severity_by_cause", "Mean and median severity by root cause",
                         (DATE_FIELD, "root_cause_category", "ai_severity"), panels=3)

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        data = self._dated(table)
        scores = self._known_values(data, "ai_severity").str.title().map(SEVERITY_SCORES)  # "low" and "Low" count the same
        data = data.assign(cause=self._known_values(data, "root_cause_category"), score=scores).dropna(subset=["cause", "score"])
        if data.empty:
            return False

        causes = data.groupby("cause")["score"].mean().sort_values(ascending=False).index.tolist()  # Most severe cause first
        months = self._month_range(data["_month"])
        yearly_ax, mean_ax, median_ax = self._split_axes(ax, 3)
        self._draw_yearly(yearly_ax, data, causes)
        self._draw_heatmap(mean_ax, data, causes, months, "mean", "Mean severity per month")
        self._draw_heatmap(median_ax, data, causes, months, "median", "Median severity per month")
        return True

    # Panel 1: for each root cause, a bar (mean) and a diamond (median) for each year
    def _draw_yearly(self, ax, data: pd.DataFrame, causes: list[str]) -> None:
        years = sorted(int(year) for year in data["_month"].dt.year.unique())
        stats = data.groupby(["cause", data["_month"].dt.year])["score"].agg(["mean", "median"])
        width = 0.8 / len(years)
        for number, (color, year) in enumerate(zip(self._palette(len(years)), years)):
            offset = (number - (len(years) - 1) / 2) * width
            xs, means, medians = [], [], []
            for position, cause in enumerate(causes):
                if (cause, year) in stats.index:
                    xs.append(position + offset)
                    means.append(stats.loc[(cause, year), "mean"])
                    medians.append(stats.loc[(cause, year), "median"])
            ax.bar(xs, means, width=width, color=color, label=f"{year} mean")
            ax.scatter(xs, medians, marker="D", s=22, color="black", zorder=3, label="Median" if number == 0 else None)
        ax.set_xticks(range(len(causes)))
        ax.set_xticklabels(causes, rotation=30, ha="right", fontsize=8)
        ax.set_yticks(list(SEVERITY_SCORES.values()))
        ax.set_yticklabels([f"{score} {level}" for level, score in SEVERITY_SCORES.items()], fontsize=8)
        ax.set_ylim(0, len(SEVERITY_ORDER) + 0.7)  # Room above the bars for the legend
        ax.set_title("Mean (bars) and median (diamonds) severity per year")
        ax.legend(fontsize=8, loc="upper right", ncol=len(years) + 1)

    # Panels 2 and 3: a grid of root cause (rows) by month (columns), coloured green (Low) to red (Critical). how is "mean" or "median"
    def _draw_heatmap(self, ax, data: pd.DataFrame, causes: list[str], months: pd.PeriodIndex, how: str, title: str) -> None:
        import matplotlib
        grid = data.pivot_table(index="cause", columns="_month", values="score", aggfunc=how).reindex(index=causes, columns=months)
        values = np.ma.masked_invalid(grid.to_numpy(dtype=float))
        colormap = matplotlib.colormaps["RdYlGn_r"].with_extremes(bad="#eeeeee")  # Months with no incidents stay grey
        image = ax.imshow(values, aspect="auto", cmap=colormap, vmin=1, vmax=len(SEVERITY_ORDER), interpolation="nearest")
        if len(months) <= 24:  # Beyond that the numbers would overlap
            for row in range(values.shape[0]):
                for column in range(values.shape[1]):
                    if not values.mask[row, column]:
                        value = values[row, column]
                        shade = "white" if value <= 1.3 or value >= 3.7 else "black"  # White text on the darkest cells
                        ax.text(column, row, f"{value:.1f}", ha="center", va="center", fontsize=7, color=shade)
        ax.set_yticks(range(len(causes)))
        ax.set_yticklabels(causes, fontsize=8)
        ax.set_title(title)
        self._mark_months(ax, months)
        bar = ax.figure.colorbar(image, ax=ax, ticks=list(SEVERITY_SCORES.values()), pad=0.02)
        bar.ax.set_yticklabels(SEVERITY_ORDER, fontsize=7)
