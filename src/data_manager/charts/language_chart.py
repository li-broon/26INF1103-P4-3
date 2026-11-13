# ------- #
# Imports
# ------- #

import pandas as pd

from src.data_manager.charts.chart_drawer import ChartDrawer

# ----- #
# Class
# ----- #

# The languages the reports were made in: a pie chart
class LanguageChart(ChartDrawer):

    def __init__(self) -> None:
        super().__init__("language", "Languages reports were made in", ("detected_language",))

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        counts = self._count_values(table, "detected_language")
        if counts.empty:
            return False
        ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90)
        ax.set_title(self._title)
        return True
