# ---------------- #
# Import and Setup
# ---------------- #
import matplotlib
matplotlib.use("agg")  # Draw to memory: no screen is needed (CI and the Docker test command have none)
import matplotlib.pyplot as plt
from matplotlib.backend_bases import ResizeEvent
from matplotlib.figure import Figure

from src.data_manager.charts.chart_resizer import ChartResizer
from src.data_manager.constants import DETAIL_GID, DETAIL_MIN_SCALE, MAX_TEXT_SCALE, MIN_TEXT_SCALE, MIN_TICK_FONT_SIZE

DESIGN_SIZE = (10, 6)  # Inches, the size every chart in these tests is "designed" for
DPI = 100


# ------------ #
# Test Helpers
# ------------ #

# A figure with a real (in memory) canvas, which can measure text
def measuring_figure():
    return plt.figure(figsize=DESIGN_SIZE, dpi=DPI)

# A window of each kind that limit_window_size knows, remembering what it was asked
class TkWindow:
    def __init__(self):
        self.asked = []

    def minsize(self, width, height):
        self.asked.append((width, height))

class QtWindow:
    def __init__(self):
        self.asked = []

    def setMinimumSize(self, width, height):
        self.asked.append((width, height))

# A window system that refuses to limit the size
class RefusingWindow:
    def minsize(self, width, height):
        raise RuntimeError("this window cannot be limited")

# A window with both calls: Tk is asked first and only it is used
class BothWindow(TkWindow):
    def __init__(self):
        super().__init__()
        self.qt_asked = []

    def setMinimumSize(self, width, height):
        self.qt_asked.append((width, height))

# The size in pixels that limit_window_size should ask for at this fraction of the design size
def pixels(fraction):
    return int(DESIGN_SIZE[0] * DPI * fraction), int(DESIGN_SIZE[1] * DPI * fraction)

# Puts the window in the figure's canvas manager (where Tk and Qt keep it) and returns the figure's resizer
def resizer_with_window(window):
    figure = measuring_figure()
    figure.canvas.manager.window = window
    return ChartResizer(figure)

# A figure with 30 long tick labels on its x axis: far too many to fit side by side at any size
def crowded_figure(figure):
    ax = figure.add_subplot()
    ax.bar(range(30), [1] * 30)
    ax.set_xticks(range(30))
    ax.set_xticklabels([f"Long category name {number}" for number in range(30)])
    return ax

# The labels of an axis that the chart shows
def shown_labels(ax):
    return [label for label in ax.get_xticklabels() if label.get_text()]


# ----------------------------- #
# limit_window_size
# ----------------------------- #

# A Tk window is told the smallest size the chart stays readable at (a fraction of its normal size in pixels)
def test_tk_window_gets_a_minimum_size():
    window = TkWindow()
    resizer_with_window(window).limit_window_size()
    assert window.asked == [pixels(MIN_TEXT_SCALE)]

# A Qt window is told the same with its own call
def test_qt_window_gets_a_minimum_size():
    window = QtWindow()
    resizer_with_window(window).limit_window_size()
    assert window.asked == [pixels(MIN_TEXT_SCALE)]

# A different fraction (the "all charts" window allows a smaller one) gives a different size
def test_minimum_size_follows_the_fraction_given():
    window = TkWindow()
    resizer_with_window(window).limit_window_size(0.5)
    assert window.asked == [pixels(0.5)]

# A window with both calls is only asked once, the Tk way
def test_window_with_both_calls_is_limited_once():
    window = BothWindow()
    resizer_with_window(window).limit_window_size()
    assert window.asked == [pixels(MIN_TEXT_SCALE)]
    assert window.qt_asked == []

# A window system that refuses is left as it is: no error reaches the user
def test_refusing_window_is_ignored():
    resizer_with_window(RefusingWindow()).limit_window_size()  # Must not raise

# A canvas with no window at all (a saved picture, or a backend without windows) is left alone too
def test_figure_without_a_window_is_ignored():
    ChartResizer(measuring_figure()).limit_window_size()  # The agg manager has no window
    ChartResizer(Figure(figsize=DESIGN_SIZE, dpi=DPI)).limit_window_size()  # A bare figure has no manager at all


# ---------------------------- #
# update: text scale and details
# ---------------------------- #

# Text grows and shrinks with the window, and always comes back to its own size at the normal size
def test_text_follows_the_window_size():
    figure = measuring_figure()
    text = figure.text(0.5, 0.5, "Title", fontsize=10)
    resizer = ChartResizer(figure)

    figure.set_size_inches(DESIGN_SIZE[0] * 0.8, DESIGN_SIZE[1] * 0.8)
    resizer.update()
    assert round(text.get_fontsize(), 6) == 8.0

    figure.set_size_inches(*DESIGN_SIZE)
    resizer.update()
    assert round(text.get_fontsize(), 6) == 10.0

# Resizing again and again at the same size never shrinks the text twice
def test_repeated_updates_do_not_shrink_text_further():
    figure = measuring_figure()
    text = figure.text(0.5, 0.5, "Title", fontsize=10)
    resizer = ChartResizer(figure)
    figure.set_size_inches(DESIGN_SIZE[0] * 0.8, DESIGN_SIZE[1] * 0.8)
    for _ in range(4):
        resizer.update()
    assert round(text.get_fontsize(), 6) == 8.0

# A text that appears after the window was already scaled is taken at its current size as the scaled size, so it is not scaled twice
def test_a_text_added_after_scaling_is_not_scaled_twice():
    figure = measuring_figure()
    figure.text(0.5, 0.5, "First", fontsize=10)
    resizer = ChartResizer(figure)
    figure.set_size_inches(DESIGN_SIZE[0] * 0.8, DESIGN_SIZE[1] * 0.8)
    resizer.update()

    later = figure.text(0.5, 0.2, "Later", fontsize=8)  # 8 points is already the 80% size of a 10-point text
    resizer.update()
    assert round(later.get_fontsize(), 6) == 8.0

# A tiny window does not shrink the text below the minimum scale, and a huge one does not grow it past the maximum
def test_text_scale_has_a_minimum_and_a_maximum():
    figure = measuring_figure()
    text = figure.text(0.5, 0.5, "Title", fontsize=10)
    resizer = ChartResizer(figure)

    figure.set_size_inches(DESIGN_SIZE[0] * 0.1, DESIGN_SIZE[1] * 0.1)
    resizer.update()
    assert round(text.get_fontsize(), 6) == round(10 * MIN_TEXT_SCALE, 6)

    figure.set_size_inches(DESIGN_SIZE[0] * 5, DESIGN_SIZE[1] * 5)
    resizer.update()
    assert round(text.get_fontsize(), 6) == round(10 * MAX_TEXT_SCALE, 6)

# Small numbers (tagged as details) are hidden when the window is too small for them, and shown again when it grows back
def test_details_are_hidden_in_a_small_window_and_come_back():
    figure = measuring_figure()
    detail = figure.text(0.5, 0.5, "7")
    detail.set_gid(DETAIL_GID)
    other = figure.text(0.5, 0.2, "Title")
    resizer = ChartResizer(figure)

    figure.set_size_inches(DESIGN_SIZE[0] * (DETAIL_MIN_SCALE - 0.1), DESIGN_SIZE[1] * (DETAIL_MIN_SCALE - 0.1))
    resizer.update()
    assert detail.get_visible() is False
    assert other.get_visible() is True  # Only the details go

    figure.set_size_inches(*DESIGN_SIZE)
    resizer.update()
    assert detail.get_visible() is True

# The window's resize event is what calls update
def test_resize_event_updates_the_text():
    figure = measuring_figure()
    text = figure.text(0.5, 0.5, "Title", fontsize=10)
    resizer = ChartResizer(figure)  # Matplotlib only keeps a weak link to it, so the test must hold on to it like the Chart Manager does
    figure.set_size_inches(DESIGN_SIZE[0] * 0.8, DESIGN_SIZE[1] * 0.8)
    figure.canvas.callbacks.process("resize_event", ResizeEvent("resize_event", figure.canvas))  # What a window sends when its corner is dragged
    assert round(text.get_fontsize(), 6) == 8.0


# ------------------------ #
# _fit_tick_labels
# ------------------------ #

# A canvas that cannot measure text cannot fit labels: they keep the window scale only, and none is hidden
def test_labels_keep_the_window_scale_when_text_cannot_be_measured():
    figure = Figure(figsize=DESIGN_SIZE, dpi=DPI)  # A bare figure's canvas has no get_renderer
    assert not hasattr(figure.canvas, "get_renderer")
    ax = crowded_figure(figure)
    normal_size = shown_labels(ax)[0].get_fontsize()

    resizer = ChartResizer(figure)
    figure.set_size_inches(DESIGN_SIZE[0] * 0.8, DESIGN_SIZE[1] * 0.8)
    resizer.update()

    labels = shown_labels(ax)
    assert all(label.get_visible() for label in labels)  # Nothing is thinned out
    assert all(round(label.get_fontsize(), 6) == round(normal_size * 0.8, 6) for label in labels)  # Only the window scale

# The same crowded labels on a canvas that can measure are made to fit (smaller or thinned out)
def test_labels_are_fitted_when_text_can_be_measured():
    figure = measuring_figure()
    ax = crowded_figure(figure)
    before = shown_labels(ax)[0].get_fontsize()
    ChartResizer(figure).update()
    labels = shown_labels(ax)
    assert any(not label.get_visible() for label in labels) or labels[0].get_fontsize() < before

# Do any two neighbouring tick labels of the axis touch? (Hidden labels do not count.)
def labels_touch(figure, ax):
    renderer = figure.canvas.get_renderer()
    boxes = [label.get_window_extent(renderer) for label in shown_labels(ax) if label.get_visible()]
    return any(left.x1 > right.x0 for left, right in zip(boxes, boxes[1:]))

# 12 labels that touch at their normal size are made smaller, but only as much as needed (not all the way down to the minimum),
# and that is enough: all are still shown and none touches
def test_slightly_crowded_labels_shrink_until_they_fit():
    figure = measuring_figure()
    ax = figure.add_subplot()
    ax.bar(range(12), [1] * 12)
    ax.set_xticks(range(12))
    ax.set_xticklabels([f"Category {number}" for number in range(12)])
    normal_size = shown_labels(ax)[0].get_fontsize()
    assert labels_touch(figure, ax)  # The test only means something if they overlap to begin with

    ChartResizer(figure).update()

    labels = shown_labels(ax)
    assert MIN_TICK_FONT_SIZE + 0.5 < labels[0].get_fontsize() < normal_size  # Smaller, but clearly above the minimum size
    assert all(label.get_visible() for label in labels)
    assert not labels_touch(figure, ax)

# Two ticks on the same spot have no gap to fit into, so their labels are left alone
def test_ticks_on_the_same_spot_are_left_alone():
    figure = measuring_figure()
    ax = figure.add_subplot()
    ax.set_xticks([1, 1])
    ax.set_xticklabels(["first", "second"])
    before = [label.get_fontsize() for label in shown_labels(ax)]
    ChartResizer(figure).update()
    assert [label.get_fontsize() for label in shown_labels(ax)] == before
    assert all(label.get_visible() for label in shown_labels(ax))

# An axis with fewer than two labels has nothing to fit
def test_a_single_label_is_left_alone():
    figure = measuring_figure()
    ax = figure.add_subplot()
    ax.set_xticks([1])
    ax.set_xticklabels(["only"])
    ChartResizer(figure).update()
    assert shown_labels(ax)[0].get_visible() is True


# ------------------------ #
# _footprint
# ------------------------ #

# A label of 40 letters, so its width is much more than its height
def long_label(figure, rotation):
    return figure.text(0.5, 0.5, "A very long category name for a tick", rotation=rotation)

# The room a label takes along its axis, measured with the figure's own renderer
def footprint(figure, label, along_x):
    return ChartResizer._footprint(label, along_x, figure.canvas.get_renderer())

# A flat label needs its width along a horizontal axis; one standing up needs only its height, so it needs far less
def test_flat_label_takes_its_width_and_standing_label_its_height():
    figure = measuring_figure()
    flat, standing = long_label(figure, 0), long_label(figure, 90)
    assert footprint(figure, flat, True) > 5 * footprint(figure, standing, True)

# Along a vertical axis it is the other way round: a flat label only needs its height
def test_vertical_axis_flips_which_side_counts():
    figure = measuring_figure()
    flat, standing = long_label(figure, 0), long_label(figure, 90)
    assert footprint(figure, flat, False) < footprint(figure, standing, False)

# A slanted label needs less than a flat one, because neighbours can overlap in length without touching
def test_slanted_label_needs_less_than_a_flat_one():
    figure = measuring_figure()
    flat, slanted = long_label(figure, 0), long_label(figure, 45)
    assert footprint(figure, slanted, True) < footprint(figure, flat, True)

# 45 degrees is slanted the same way for both axes
def test_45_degrees_is_the_same_on_both_axes():
    figure = measuring_figure()
    slanted = long_label(figure, 45)
    assert round(footprint(figure, slanted, True), 6) == round(footprint(figure, slanted, False), 6)

# A label 30 degrees off the x axis is 60 degrees off the y axis, so the two measures agree
def test_vertical_axis_measures_from_its_own_axis():
    figure = measuring_figure()
    thirty, sixty = long_label(figure, 30), long_label(figure, 60)
    assert round(footprint(figure, thirty, False), 6) == round(footprint(figure, sixty, True), 6)

# A label that is only a hair off flat is treated as flat: it needs its width (and the measure does not divide by ~0)
def test_almost_flat_label_needs_its_width():
    figure = measuring_figure()
    flat, almost_flat = long_label(figure, 0), long_label(figure, 1e-9)
    assert abs(footprint(figure, almost_flat, True) - footprint(figure, flat, True)) < 2  # Pixels
