# ------- #
# Imports
# ------- #

import os

from src.data_manager.charts.chart_drawer import ChartDrawer
from src.data_manager.charts.chart_resizer import ChartResizer

# --------- #
# Constants
# --------- #

# Window sizes in inches (a window is 100 pixels per inch, so these fit a normal laptop screen)
WINDOW_WIDTH = 11                 # One chart on its own
WINDOW_HEIGHT = 5.0               # ...with one panel
EXTRA_PANEL_HEIGHT = 3.2          # Added for each extra panel, up to MAX_WINDOW_HEIGHT
MAX_WINDOW_HEIGHT = 8.0

ALL_WIDTH = 16                    # All the charts together in one window (or one saved picture)
ALL_WINDOW_HEIGHT = 9
ALL_SAVED_HEIGHT = 12             # A saved picture has no screen to fit, so it gets more room
ALL_MIN_WINDOW_SCALE = 0.75       # With five charts in it the window cannot be shrunk as far as a window with one

NO_SCREEN_BACKENDS = ("agg", "cairo", "pdf", "pgf", "ps", "svg", "template")  # Matplotlib backends that can only write files

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

    # Shows the chart the user asked for, in a window that follows its size (each chart of "all" gets its own window).
    # chart_name   : a key of the drawers, or "all" for every chart
    # filter_column, filter_value : optional, chart only the reports matching this filter
    #                (same columns and values as the filter menu, e.g. "ai_severity", "Critical")
    # save_path    : optional, save the picture to this file instead of opening a window ("all" is saved as one picture)
    # Returns (success, message), like save_record, so io_manager can print the message
    def show_chart(self, chart_name: str, filter_column: str | None = None, filter_value: str | None = None, save_path: str | None = None) -> tuple[bool, str]:
        try:
            import matplotlib
            import matplotlib.pyplot as plt
        except ImportError:
            return False, "matplotlib is not installed. Run: pip install matplotlib"

        # A window needs a screen (e.g. a Docker container without one has none): say so instead of silently showing nothing
        if not save_path and matplotlib.get_backend().lower() in NO_SCREEN_BACKENDS:
            return False, "This computer has no screen to show charts on. Run with a display (see 'Running the GUI with Docker' in README.md)."

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

        heading = f"Incident Reports ({len(table)} reports)"
        if filter_column is not None:
            heading += f" where {filter_column} = {filter_value}"
        drawers = list(self._drawers.values()) if chart_name == "all" else [self._drawers[chart_name]]

        if save_path:
            figure = self._build_figure(drawers, table, heading, for_window=False)
            ChartResizer(figure).update()  # A picture has one size, but its tick labels still have to fit their room
            try:
                os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)  # e.g. the app was started outside the project folder
                figure.savefig(save_path, dpi=150, bbox_inches="tight")
            except OSError as error:
                return False, f"Chart could not be saved to {save_path}: {error}"
            finally:
                plt.close(figure)
            return True, f"Chart saved to {save_path}"

        # One window, however many charts it holds
        figure = self._build_figure(drawers, table, heading, for_window=True)
        resizer = ChartResizer(figure)  # Matplotlib only keeps a weak link to a resizer, so it is kept here until the window is closed
        resizer.update()
        if len(drawers) > 1:
            resizer.limit_window_size(ALL_MIN_WINDOW_SCALE)
        else:
            resizer.limit_window_size()
        try:
            figure.canvas.manager.set_window_title(drawers[0].title if len(drawers) == 1 else "All charts")
        except AttributeError:
            pass  # Some backends have no window title
        plt.show()  # Blocks until the window is closed
        plt.close(figure)
        del resizer
        return True, "Chart closed."

    # Draws the drawers on one new figure and returns it.
    # With several charts the figure is a dashboard of two columns as equal in height as possible, each keeping the menu order
    # for_window: a window has to fit a screen; a saved picture can be taller
    def _build_figure(self, drawers: list[ChartDrawer], table, heading: str, for_window: bool):
        import matplotlib.pyplot as plt
        columns = self._split_into_columns(drawers)

        if len(drawers) == 1:
            width, height = WINDOW_WIDTH, min(MAX_WINDOW_HEIGHT, WINDOW_HEIGHT + EXTRA_PANEL_HEIGHT * (drawers[0].panels - 1))
        else:
            width, height = ALL_WIDTH, ALL_WINDOW_HEIGHT if for_window else ALL_SAVED_HEIGHT

        figure = plt.figure(figsize=(width, height), layout="constrained")
        grid = figure.add_gridspec(1, len(columns))
        for number, column in enumerate(columns):
            # Each chart gets the share of the column's height that it asks for
            column_grid = grid[0, number].subgridspec(len(column), 1, height_ratios=[drawer.height for drawer in column])
            for row, drawer in enumerate(column):
                ax = figure.add_subplot(column_grid[row])
                if not drawer.draw(ax, table):
                    ax.set_title(drawer.title)
                    ax.text(0.5, 0.5, "No data to show", ha="center", va="center", transform=ax.transAxes)
                    ax.axis("off")

        figure.suptitle(heading, fontsize=14, fontweight="bold")
        return figure

    # Shares the charts between a left and a right column so the columns are as close in height as possible (a 3 panel chart
    # is not stacked under a 2 panel one while 3 small charts share the other side), keeping the menu order inside each column.
    # One chart on its own stays in a single column
    @staticmethod
    def _split_into_columns(drawers: list[ChartDrawer]) -> list[list[ChartDrawer]]:
        if len(drawers) == 1:
            return [list(drawers)]
        columns = [[], []]
        heights = [0.0, 0.0]
        for drawer in sorted(drawers, key=lambda drawer: drawer.height, reverse=True):  # Tallest first, each into the shorter column
            shorter = 0 if heights[0] <= heights[1] else 1
            columns[shorter].append(drawer)
            heights[shorter] += drawer.height
        return [[drawer for drawer in drawers if drawer in column] for column in columns]
