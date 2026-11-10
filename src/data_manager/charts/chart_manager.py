# ------- #
# Imports
# ------- #

from src.data_manager.charts.chart_drawer import ChartDrawer

# --------- #
# Constants
# --------- #

PANEL_HEIGHT = 3.8  # Height in inches of one panel of a chart

# ----- #
# Class
# ----- #

# Shows the chart the user asks for: gets the reports from the DataManager and draws them with the matching ChartDrawer(s)
class ChartManager:

    # data_manager gives the reports (anything with load_records and load_matching_records works, e.g. a fake one in the tests)
    # drawers maps each chart name to its ChartDrawer; both are passed in, so any data or set of charts works
    def __init__(self, data_manager, drawers: dict[str, ChartDrawer]) -> None:
        self._data_manager = data_manager
        self._drawers = dict(drawers)  # A copy, so changing the dictionary later changes nothing here

    # The charts the user can choose from, as (name, menu text) pairs
    def get_chart_options(self) -> list[tuple[str, str]]:
        return [(key, drawer.title) for key, drawer in self._drawers.items()]

    # Shows the chart the user asked for.
    # chart_name   : a key of the drawers, or "all" for every chart on one page
    # filter_column, filter_value : optional, chart only the reports matching this filter
    #                (same columns and values as the filter menu, e.g. "ai_severity", "Critical")
    # save_path    : optional, save the picture to this file instead of opening a window
    # Returns (success, message), like save_record, so io_manager can print the message
    def show_chart(self, chart_name: str, filter_column: str | None = None, filter_value: str | None = None, save_path: str | None = None) -> tuple[bool, str]:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return False, "matplotlib is not installed. Run: pip install matplotlib"

        chart_name = str(chart_name).strip().lower()
        if chart_name != "all" and chart_name not in self._drawers:
            return False, f"Unknown chart '{chart_name}'. Choose from: all, " + ", ".join(self._drawers)

        # Load all reports, or only the ones matching the filter
        if filter_column is not None:
            table = self._data_manager.load_matching_records(filter_column, filter_value)
        else:
            table = self._data_manager.load_records()
        if table.empty:
            return False, "No reports to chart" + (" for that filter." if filter_column is not None else " yet.")

        drawers = list(self._drawers.values()) if chart_name == "all" else [self._drawers[chart_name]]
        columns = 2 if len(drawers) > 1 else 1

        # One panel charts go side by side in pairs; a chart with several panels gets a full width row of its own (after the one panel charts)
        small = [drawer for drawer in drawers if drawer.panels == 1]
        big = [drawer for drawer in drawers if drawer.panels > 1]
        rows = [small[i:i + columns] for i in range(0, len(small), columns)] + [[drawer] for drawer in big]
        row_panels = [max(drawer.panels for drawer in row) for row in rows]  # A row is as tall as its tallest chart

        fig = plt.figure(figsize=(11 if columns == 1 else 8 * columns, PANEL_HEIGHT * sum(row_panels)), layout="constrained")
        grid = fig.add_gridspec(len(rows), columns, height_ratios=row_panels)
        for row_number, row in enumerate(rows):
            for column, drawer in enumerate(row):
                full_width = len(row) == 1 and drawer.panels > 1
                ax = fig.add_subplot(grid[row_number, :] if full_width else grid[row_number, column])
                if not drawer.draw(ax, table):
                    ax.set_title(drawer.title)
                    ax.text(0.5, 0.5, "No data to show", ha="center", va="center", transform=ax.transAxes)
                    ax.axis("off")

        heading = f"Incident Reports ({len(table)} reports)"
        if filter_column is not None:
            heading += f" where {filter_column} = {filter_value}"
        fig.suptitle(heading, fontsize=14, fontweight="bold")

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return True, f"Chart saved to {save_path}"

        plt.show()  # Blocks until the window is closed
        plt.close(fig)
        return True, "Chart closed."
