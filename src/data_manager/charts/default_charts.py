# ------- #
# Imports
# ------- #

from src.data_manager.charts.chart_drawer import ChartDrawer
from src.data_manager.charts.location_chart import LocationChart
from src.data_manager.charts.monthly_chart import MonthlyChart
from src.data_manager.charts.root_cause_chart import RootCauseChart
from src.data_manager.charts.severity_by_cause_chart import SeverityByCauseChart

# ---------- #
# Function
# ---------- #

# Builds the app's charts as a dictionary of chart name -> chart, in the order the menu shows them
def create_default_charts() -> dict[str, ChartDrawer]:
    charts = [RootCauseChart(), MonthlyChart(), LocationChart(),
              SeverityByCauseChart()]
    return {chart.key: chart for chart in charts}
