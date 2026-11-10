# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.charts.constants import COUNT_LABEL, MAX_LABEL_LENGTH, OTHER_LABEL, TOP_LOCATIONS
from src.data_manager.charts.time_chart_drawer import TimeChartDrawer
from src.data_manager.constants import DATE_FIELD

# ----- #
# Class
# ----- #

# Where incidents happened, in two panels: per month (stacked, every year Jan to Dec) and per year (bars).
# Only the TOP_LOCATIONS places with the most incidents are named; every other place is grouped as "Other"
class LocationChart(TimeChartDrawer):

    def __init__(self) -> None:
        super().__init__("location", f"Top {TOP_LOCATIONS} locations, per month and per year", (DATE_FIELD, "location"), panels=2)

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        from matplotlib.ticker import MaxNLocator
        data = self._dated(table)
        data = data.assign(place=self._known_values(data, "location")).dropna(subset=["place"])
        if data.empty:
            return False

        # Shorten long names, then keep the top places and group the rest as "Other"
        data["place"] = data["place"].map(lambda name: name if len(name) <= MAX_LABEL_LENGTH else name[:MAX_LABEL_LENGTH - 3] + "...")
        top = data["place"].value_counts().head(TOP_LOCATIONS).index
        data["place"] = data["place"].where(data["place"].isin(top), OTHER_LABEL)

        monthly_ax, yearly_ax = self._split_axes(ax, 2)

        # Panel 1: per month
        self._draw_monthly_stacks(monthly_ax, data, "place", "Location", "Incidents per month, by location")

        # Panel 2: per year, one group of bars per location (biggest on top)
        grid = pd.crosstab(data["place"], data["_month"].dt.year)
        grid = grid.loc[grid.sum(axis=1).sort_values().index]
        grid.plot(kind="barh", ax=yearly_ax, width=0.8)
        for container in yearly_ax.containers:
            yearly_ax.bar_label(container, labels=[str(int(value)) if value else "" for value in container.datavalues], padding=2, fontsize=8)
        yearly_ax.set_title("Incidents per year, by location")
        yearly_ax.set_xlabel(COUNT_LABEL)
        yearly_ax.set_ylabel("")
        yearly_ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        yearly_ax.legend(title="Year", fontsize=8, title_fontsize=8)
        return True
