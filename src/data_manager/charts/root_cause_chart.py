# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.charts.time_chart_drawer import TimeChartDrawer
from src.data_manager.constants import DATE_FIELD

# ----- #
# Class
# ----- #

# How often each root cause happened in each month: one stacked bar per month, with every year laid out Jan to Dec
class RootCauseChart(TimeChartDrawer):

    def __init__(self) -> None:
        super().__init__("root_cause", "Root causes per month, per year", (DATE_FIELD, "root_cause_category"))

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        data = self._dated(table)
        data = data.assign(cause=self._known_values(data, "root_cause_category")).dropna(subset=["cause"])
        if data.empty:
            return False
        self._draw_monthly_stacks(ax, data, "cause", "Root cause", self._title)
        return True
