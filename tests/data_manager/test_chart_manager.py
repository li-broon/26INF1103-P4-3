import os
import sys
import tempfile
from unittest import mock

import matplotlib
matplotlib.use("agg")  # Draw to memory: no screen is needed (CI and the Docker test command have none)
import matplotlib.pyplot as plt
import pandas as pd

from src.data_manager.charts.chart_manager import (
    ALL_SAVED_HEIGHT, ALL_WIDTH, ALL_WINDOW_HEIGHT, MAX_WINDOW_HEIGHT, WINDOW_HEIGHT, WINDOW_WIDTH, ChartManager,
)
from src.data_manager.charts.default_charts import create_default_charts

CHART_KEYS = list(create_default_charts())

REPORT = {"reporter_name": "Ann", "incident_date": "2026-10-01", "importance_score": 5, "location": "Tuas, bay 2",
          "root_cause_category": "Fire", "detected_language": "English", "ai_severity": "High", "work_stoppage_hours": 1}


# A Data Manager that always gives the same table and remembers how it was asked
class FakeData:
    def __init__(self, table):
        self.table = table
        self.asked = []  # Every call as (method name, arguments)

    def load_records(self, ascending=False):
        self.asked.append(("load_records", ()))
        return self.table

    def load_matching_records(self, column, value):
        self.asked.append(("load_matching_records", (column, value)))
        return self.table

# A table with a few normal reports
def some_reports():
    return pd.DataFrame([REPORT, dict(REPORT, incident_date="2026-11-05", root_cause_category="Electrical")])

# A ChartManager with every default chart, fed by the given data manager
def manager_for(data):
    return ChartManager(data, create_default_charts())

# A table with every column the charts use, but nothing a chart could draw
def unusable_table():
    return pd.DataFrame([dict(REPORT, incident_date="not a date", location="", root_cause_category="",
                              detected_language=float("nan"), ai_severity="")])

# Imports of matplotlib fail while this is in use, like on a computer where it is not installed
def without_matplotlib():
    return mock.patch.dict(sys.modules, {"matplotlib": None, "matplotlib.pyplot": None, "matplotlib.figure": None})


# A chart name that does not exist is refused with the names the user can choose from, and no reports are loaded
def test_unknown_chart_is_refused_and_the_choices_are_listed():
    data = FakeData(some_reports())
    saved, message = manager_for(data).show_chart("pie", save_path="unused.png")
    assert saved is False
    assert "Unknown chart 'pie'" in message
    assert "all" in message and all(key in message for key in CHART_KEYS)
    assert data.asked == []
    assert not os.path.exists("unused.png")

# build_chart (used by the GUI) refuses the same way, giving no figure
def test_build_chart_refuses_an_unknown_chart():
    figure, message = manager_for(FakeData(some_reports())).build_chart("pie")
    assert figure is None
    assert "Unknown chart 'pie'" in message

# An empty name or a name with the wrong kind of value is an unknown chart, not a crash
def test_odd_chart_names_are_unknown_charts():
    for name in ("", "   ", None, 5, "root cause"):
        saved, message = manager_for(FakeData(some_reports())).show_chart(name, save_path="unused.png")
        assert saved is False and message.startswith("Unknown chart"), name

# Capital letters and spaces around the name do not matter
def test_chart_name_ignores_case_and_spaces():
    with tempfile.TemporaryDirectory() as folder:
        for name in ("language", " Language ", "LANGUAGE"):
            path = os.path.join(folder, "chart.png")
            saved, message = manager_for(FakeData(some_reports())).show_chart(name, save_path=path)
            assert saved is True, message
            assert os.path.getsize(path) > 0
            os.remove(path)

# With no reports at all there is nothing to draw, for one chart and for "all"
def test_no_reports_gives_a_message_instead_of_a_chart():
    with tempfile.TemporaryDirectory() as folder:
        for name in ("language", "all"):
            path = os.path.join(folder, "chart.png")
            saved, message = manager_for(FakeData(pd.DataFrame())).show_chart(name, save_path=path)
            assert (saved, message) == (False, "No reports to chart yet.")
            assert not os.path.exists(path)  # Nothing was saved

# build_chart gives no figure when there are no reports
def test_build_chart_with_no_reports_gives_no_figure():
    assert manager_for(FakeData(pd.DataFrame())).build_chart("all") == (None, "No reports to chart yet.")

# When the filter matches nothing the message says so, instead of "yet"
def test_no_reports_for_a_filter_gives_its_own_message():
    data = FakeData(pd.DataFrame())
    assert manager_for(data).show_chart("language", "ai_severity", "Critical", save_path="unused.png") == \
        (False, "No reports to chart for that filter.")
    assert manager_for(data).build_chart("language", "ai_severity", "Critical") == (None, "No reports to chart for that filter.")


# Without a filter every report is loaded; with one only the matching reports are
def test_filter_decides_which_reports_are_loaded():
    data = FakeData(some_reports())
    manager_for(data).build_chart("language")
    assert data.asked == [("load_records", ())]

    data = FakeData(some_reports())
    manager_for(data).build_chart("language", "ai_severity", "Critical")
    assert data.asked == [("load_matching_records", ("ai_severity", "Critical"))]

# The title of the picture says how many reports it shows and which filter was used
def test_heading_names_the_reports_and_the_filter():
    figure, _ = manager_for(FakeData(some_reports())).build_chart("language")
    assert figure.texts[0].get_text() == "Incident Reports (2 reports)"

    figure, _ = manager_for(FakeData(some_reports())).build_chart("language", "ai_severity", "Critical")
    assert figure.texts[0].get_text() == "Incident Reports (2 reports) where ai_severity = Critical"


# Without matplotlib the user is told how to install it, and nothing is loaded or saved
def test_missing_matplotlib_is_reported():
    data = FakeData(some_reports())
    with without_matplotlib():
        saved, message = manager_for(data).show_chart("language", save_path="unused.png")
        figure, build_message = manager_for(data).build_chart("language")
    assert saved is False and message == "matplotlib is not installed. Run: pip install matplotlib"
    assert figure is None and build_message == message
    assert data.asked == []
    assert not os.path.exists("unused.png")

# A window needs a screen: with a backend that can only write files the user is told so, and no reports are loaded
def test_window_without_a_screen_is_refused():
    assert matplotlib.get_backend().lower() == "agg"
    data = FakeData(some_reports())
    shown, message = manager_for(data).show_chart("language")
    assert shown is False
    assert "no screen" in message
    assert data.asked == []

# The same backend can still save a picture, which needs no screen
def test_saving_a_picture_needs_no_screen():
    with tempfile.TemporaryDirectory() as folder:
        saved, message = manager_for(FakeData(some_reports())).show_chart("language", save_path=os.path.join(folder, "a.png"))
        assert saved is True, message


# A folder that cannot be made (a file is in the way) gives a message, and the figure is closed
def test_save_into_an_impossible_folder_is_reported():
    plt.close("all")
    with tempfile.TemporaryDirectory() as folder:
        blocker = os.path.join(folder, "blocker")
        open(blocker, "w").close()
        path = os.path.join(blocker, "chart.png")
        saved, message = manager_for(FakeData(some_reports())).show_chart("language", save_path=path)
        assert saved is False
        assert message.startswith(f"Chart could not be saved to {path}: ")
        assert plt.get_fignums() == []  # No half-made figure is left open

# A picture that cannot be written (disk full, file in use) gives the reason, and the figure is closed
def test_save_failure_gives_the_reason():
    plt.close("all")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "chart.png")
        with mock.patch("matplotlib.figure.Figure.savefig", side_effect=OSError("disk full")):
            saved, message = manager_for(FakeData(some_reports())).show_chart("all", save_path=path)
        assert saved is False
        assert message == f"Chart could not be saved to {path}: disk full"
        assert plt.get_fignums() == []

# Saving a picture of every chart works, writes a picture and leaves no figure open
def test_every_chart_and_all_can_be_saved():
    plt.close("all")
    with tempfile.TemporaryDirectory() as folder:
        for name in CHART_KEYS + ["all"]:
            path = os.path.join(folder, f"{name}.png")
            saved, message = manager_for(FakeData(some_reports())).show_chart(name, save_path=path)
            assert saved is True, f"{name}: {message}"
            assert message == f"Chart saved to {path}"
            with open(path, "rb") as picture:
                assert picture.read(8) == b"\x89PNG\r\n\x1a\n", name
        assert plt.get_fignums() == []

# Reports with nothing a chart could draw still give a picture ("No data to show"), never a crash
def test_unusable_reports_still_give_a_picture():
    with tempfile.TemporaryDirectory() as folder:
        for name in CHART_KEYS + ["all"]:
            path = os.path.join(folder, f"{name}.png")
            saved, message = manager_for(FakeData(unusable_table())).show_chart(name, save_path=path)
            assert saved is True, f"{name}: {message}"
            assert os.path.getsize(path) > 0


# With a screen the chart opens in a window, waits for it to close, and leaves no figure open
def test_chart_opens_in_a_window_and_closes_it():
    plt.close("all")
    with mock.patch("matplotlib.get_backend", return_value="tkagg"), mock.patch("matplotlib.pyplot.show") as show, \
            mock.patch("matplotlib.backend_bases.FigureManagerBase.set_window_title") as set_title:
        shown, message = manager_for(FakeData(some_reports())).show_chart("language")
    assert (shown, message) == (True, "Chart closed.")
    show.assert_called_once()
    assert set_title.call_args == mock.call(create_default_charts()["language"].title)  # Last named after its chart (pyplot first called it "Figure 1")
    assert plt.get_fignums() == []

# "all" opens one window for every chart, named "All charts"
def test_all_charts_open_in_one_window():
    plt.close("all")
    with mock.patch("matplotlib.get_backend", return_value="qtagg"), mock.patch("matplotlib.pyplot.show") as show, \
            mock.patch("matplotlib.backend_bases.FigureManagerBase.set_window_title") as set_title:
        shown, _ = manager_for(FakeData(some_reports())).show_chart("all")
    assert shown is True
    show.assert_called_once()
    assert set_title.call_args == mock.call("All charts")

# A window system that cannot name its windows does not stop the chart from opening
def test_window_without_a_title_still_opens():
    def refuse_the_chart_title(title):
        if not title.startswith("Figure"):  # pyplot's own first name for a window is allowed
            raise AttributeError("no window title")

    with mock.patch("matplotlib.get_backend", return_value="tkagg"), mock.patch("matplotlib.pyplot.show") as show, \
            mock.patch("matplotlib.backend_bases.FigureManagerBase.set_window_title", side_effect=refuse_the_chart_title):
        shown, message = manager_for(FakeData(some_reports())).show_chart("language")
    assert (shown, message) == (True, "Chart closed.")
    show.assert_called_once()


# The GUI gets a figure of its own that matplotlib's window manager does not know about
def test_build_chart_gives_a_figure_that_is_not_opened_anywhere():
    plt.close("all")
    figure, message = manager_for(FakeData(some_reports())).build_chart("all")
    assert message == "Chart drawn."
    assert figure is not None and len(figure.axes) >= len(CHART_KEYS)
    assert plt.get_fignums() == []

# A chart with nothing to draw says "No data to show" in place of the chart
def test_build_chart_says_no_data_to_show_when_a_chart_has_nothing():
    for name in CHART_KEYS:
        figure, message = manager_for(FakeData(unusable_table())).build_chart(name)
        assert message == "Chart drawn.", name
        assert [text.get_text() for text in figure.axes[0].texts] == ["No data to show"], name

# One chart is not drawn with the others: "language" has a single pie, and "all" has them all
def test_build_chart_draws_only_the_chart_asked_for():
    figure, _ = manager_for(FakeData(some_reports())).build_chart("language")
    assert [ax.get_title() for ax in figure.axes] == [create_default_charts()["language"].title]


# The menu offers every chart as (name, menu text), in order
def test_chart_options_list_every_chart_in_order():
    options = manager_for(FakeData(some_reports())).get_chart_options()
    assert options == [(key, chart.title) for key, chart in create_default_charts().items()]
    assert [key for key, _ in options] == CHART_KEYS

# The manager keeps its own copy of the charts: changing the dictionary afterwards changes nothing
def test_manager_keeps_its_own_copy_of_the_charts():
    charts = create_default_charts()
    manager = ChartManager(FakeData(some_reports()), charts)
    charts.pop("language")
    assert "language" in [key for key, _ in manager.get_chart_options()]
    with tempfile.TemporaryDirectory() as folder:
        saved, message = manager.show_chart("language", save_path=os.path.join(folder, "chart.png"))
        assert saved is True, message

# A manager with no charts refuses every name except "all"
def test_manager_with_no_charts_has_nothing_to_offer():
    manager = ChartManager(FakeData(some_reports()), {})
    assert manager.get_chart_options() == []
    assert manager.show_chart("language", save_path="unused.png") == (False, "Unknown chart 'language'. Choose from: all, ")

# One chart is as wide as a window and as tall as its panels need, up to the screen's limit
def test_figure_size_of_one_chart_follows_its_panels():
    charts = create_default_charts()
    assert ChartManager._figure_size([charts["language"]], True) == (WINDOW_WIDTH, WINDOW_HEIGHT)
    assert ChartManager._figure_size([charts["location"]], True)[1] == min(MAX_WINDOW_HEIGHT, WINDOW_HEIGHT + 3.2)
    assert ChartManager._figure_size([charts["severity_by_cause"]], True) == (WINDOW_WIDTH, MAX_WINDOW_HEIGHT)

# Several charts share a big dashboard; a saved picture has no screen to fit, so it is taller than a window
def test_figure_size_of_all_charts_depends_on_window_or_picture():
    drawers = list(create_default_charts().values())
    assert ChartManager._figure_size(drawers, True) == (ALL_WIDTH, ALL_WINDOW_HEIGHT)
    assert ChartManager._figure_size(drawers, False) == (ALL_WIDTH, ALL_SAVED_HEIGHT)

# One chart stays in one column
def test_one_chart_stays_in_one_column():
    drawer = create_default_charts()["language"]
    assert ChartManager._split_into_columns([drawer]) == [[drawer]]

# Several charts are shared between two columns of about the same height, each chart once, in menu order inside its column
def test_charts_are_shared_between_two_balanced_columns():
    drawers = list(create_default_charts().values())
    columns = ChartManager._split_into_columns(drawers)
    assert len(columns) == 2
    assert sorted(drawer.key for column in columns for drawer in column) == sorted(CHART_KEYS)
    for column in columns:
        keys = [drawer.key for drawer in column]
        assert keys == [key for key in CHART_KEYS if key in keys]
    heights = [sum(drawer.height for drawer in column) for column in columns]
    assert abs(heights[0] - heights[1]) <= max(drawer.height for drawer in drawers)
