# ---------------- #
# Import and Setup
# ---------------- #
import os
import tempfile
from types import SimpleNamespace

import matplotlib
matplotlib.use("agg")  # Draw to memory: no screen is needed (CI and the Docker test command have none)
import matplotlib.pyplot as plt
import pandas as pd

from src.data_manager.charts.chart_manager import ChartManager
from src.data_manager.charts.chart_resizer import ChartResizer
from src.data_manager.charts.default_charts import create_default_charts
from src.data_manager.constants import MIN_TICK_FONT_SIZE

# Ten root causes, the longest category list the charts show
CAUSES = ["Struck by Object", "Electrical", "Safety Procedure Breach", "Chemical", "Fall from Height",
          "Water", "Fire", "Machinery", "Slip or Trip", "Other"]
LABEL_SIZE = 8

REPORT = {"reporter_name": "Ann", "incident_date": "2026-10-01", "importance_score": 5, "location": "Tuas, bay 2",
          "root_cause_category": "Fire", "detected_language": "English", "ai_severity": "High", "work_stoppage_hours": 1}


# ------------ #
# Test Helpers
# ------------ #

# A bar chart with one bar per cause named on the y axis, in a figure of the given size in inches
def chart_with_cause_labels(width, height):
    figure = plt.figure(figsize=(width, height), layout="constrained")
    ax = figure.add_subplot()
    ax.barh(range(len(CAUSES)), [1] * len(CAUSES))
    ax.set_yticks(range(len(CAUSES)), labels=CAUSES, fontsize=LABEL_SIZE)
    return figure, ax

# The y tick labels that are shown, as drawn (bottom to top), with their font size and box on the picture
def drawn_labels(ax):
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    labels = [label for label in ax.get_yticklabels() if label.get_visible() and label.get_text()]
    return sorted(((label.get_fontsize(), label.get_window_extent(renderer)) for label in labels), key=lambda item: item[1].y0)

# True if no label's box reaches into the next one's
def none_touch(labels):
    return all(lower.y1 <= upper.y0 for (_, lower), (_, upper) in zip(labels, labels[1:]))

# A ChartManager fed by a Data Manager that always gives the same table
def manager_for(table):
    return ChartManager(SimpleNamespace(load_records=lambda ascending=False: table, load_matching_records=lambda c, v: table),
                        create_default_charts())


# ------------------- #
# ChartResizer Tests
# ------------------- #

# With room to spare the labels keep the size the chart gave them, and all of them are shown
def test_labels_with_enough_room_keep_their_size():
    figure, ax = chart_with_cause_labels(6, 8)
    ChartResizer(figure).update()
    labels = drawn_labels(ax)
    assert len(labels) == len(CAUSES)
    assert all(size == LABEL_SIZE for size, _ in labels)
    assert none_touch(labels)
    plt.close(figure)

# In a short panel the labels shrink, but only as far as the smallest readable size, until neighbours no longer touch
def test_crowded_labels_shrink_until_they_no_longer_touch():
    figure, ax = chart_with_cause_labels(6, 1.5)
    ChartResizer(figure).update()
    labels = drawn_labels(ax)
    assert len(labels) == len(CAUSES)
    assert all(MIN_TICK_FONT_SIZE <= size < LABEL_SIZE for size, _ in labels)
    assert none_touch(labels)
    plt.close(figure)

# When even the smallest readable size does not fit, every 2nd (3rd...) label is shown at that size instead of a jumble;
# making the chart big again brings every label back at full size
def test_labels_are_thinned_out_when_too_small_to_fit_then_restored():
    figure, ax = chart_with_cause_labels(6, 1.0)
    resizer = ChartResizer(figure)
    resizer.update()
    labels = drawn_labels(ax)
    assert 1 < len(labels) < len(CAUSES)
    assert all(size == MIN_TICK_FONT_SIZE for size, _ in labels)
    assert none_touch(labels)

    figure.set_size_inches(6, 8)
    resizer.update()
    labels = drawn_labels(ax)
    assert len(labels) == len(CAUSES)
    assert all(size == LABEL_SIZE for size, _ in labels)
    plt.close(figure)


# ------------------- #
# ChartManager Tests
# ------------------- #

# Reports with every severity blank still give a picture (the severity panels say "No data") instead of a crash
def test_blank_severities_do_not_crash_the_severity_chart():
    table = pd.DataFrame([dict(REPORT, ai_severity=float("nan"))] * 3)
    with tempfile.TemporaryDirectory() as folder:
        for chart in ("severity_by_cause", "all"):
            saved, message = manager_for(table).show_chart(chart, save_path=os.path.join(folder, f"{chart}.png"))
            assert saved is True, message

# Saving into a folder that does not exist yet (the app started outside the project folder) creates it rather than crashing
def test_saving_a_chart_creates_the_folder():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "new", "deeper", "chart.png")
        saved, message = manager_for(pd.DataFrame([REPORT])).show_chart("language", save_path=path)
        assert saved is True and os.path.getsize(path) > 0
