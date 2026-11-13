# ------- #
# Imports
# ------- #

import math
import weakref

from matplotlib.text import Text

from src.data_manager.constants import (
    DETAIL_GID, DETAIL_MIN_SCALE, MAX_TEXT_SCALE, MIN_TEXT_SCALE, MIN_TICK_FONT_SIZE, TICK_LABEL_GAP, YEAR_LABEL_PAD,
)

# ----- #
# Class
# ----- #

# Keeps one chart readable at any size, in a window or a saved picture.
# Text sizes are fixed in points, so without this the labels would keep their size while the window shrinks and pile on top of each other.
# This makes the text grow and shrink with the window (like a zoom), fits each axis' tick labels to the room that axis really has
# (long category names, many months), and hides the small numbers (bar totals, cell numbers) when there is no room for them
class ChartResizer:

    # figure is the window's chart; the size it has now is the size it was laid out for
    def __init__(self, figure) -> None:
        self._figure = figure
        self._design_size = tuple(float(size) for size in figure.get_size_inches())
        self._base_sizes = weakref.WeakKeyDictionary()  # Each text's font size at the design size
        self._thinned = weakref.WeakSet()               # Tick labels hidden to make room, so they can be shown again when there is room
        self._scale = 1.0                               # The scale applied the last time
        figure.canvas.mpl_connect("resize_event", self._on_resize)

    # Stops the user shrinking the window below the point where the chart is still readable (fraction of its normal size).
    # Only some window systems allow this (Tk and Qt do); on the others the window can be shrunk freely and nothing happens here
    def limit_window_size(self, fraction: float = MIN_TEXT_SCALE) -> None:
        width = int(self._design_size[0] * self._figure.dpi * fraction)
        height = int(self._design_size[1] * self._figure.dpi * fraction)
        window = getattr(self._figure.canvas.manager, "window", None)
        try:
            if hasattr(window, "minsize"):             # Tk
                window.minsize(width, height)
            elif hasattr(window, "setMinimumSize"):    # Qt
                window.setMinimumSize(width, height)
        except Exception:
            pass  # A window system that refuses is left as it is

    # Called by the window every time its size changes
    def _on_resize(self, event) -> None:
        self.update()

    # Fits the text to the figure's current size
    def update(self) -> None:
        width, height = (float(size) for size in self._figure.get_size_inches())
        ratio = min(width / self._design_size[0], height / self._design_size[1])
        scale = min(max(ratio, MIN_TEXT_SCALE), MAX_TEXT_SCALE)

        for text in self._figure.findobj(Text):
            # The first time a text is seen, work out its size at the design size (so repeated resizes never shrink it twice)
            base = self._base_sizes.setdefault(text, text.get_fontsize() / self._scale)
            text.set_fontsize(base * scale)
            if text.get_gid() == DETAIL_GID:
                text.set_visible(ratio >= DETAIL_MIN_SCALE)

        for ax in self._figure.axes:
            ax.tick_params(axis="x", which="minor", pad=YEAR_LABEL_PAD * scale)  # The gap above the year labels shrinks too
        self._scale = scale
        self._fit_tick_labels()

    # The window scale alone cannot know how much room each axis has (a panel in a crowded column, a month axis squeezed by a legend),
    # so every axis' tick labels are also fitted to the gap between their ticks
    def _fit_tick_labels(self) -> None:
        canvas = self._figure.canvas
        if not hasattr(canvas, "get_renderer"):
            return  # A window system that cannot measure text: the labels keep the window scale only
        layout = self._figure.get_layout_engine()
        if layout is not None:
            layout.execute(self._figure)  # Place the axes for the current size first, so the room each one has is measured right
        renderer = canvas.get_renderer()
        for label in self._thinned:
            label.set_visible(True)  # Start from every label shown, undoing the thinning done at an earlier size
        self._thinned.clear()
        for ax in self._figure.axes:
            self._fit_axis(ax, ax.xaxis, True, renderer)
            self._fit_axis(ax, ax.yaxis, False, renderer)

    # Shrinks one axis' tick labels until neighbours no longer touch; if even the smallest readable size does not fit, keeps that size
    # and shows every 2nd, 3rd... label instead. along_x says whether the axis runs left to right (x) or bottom to top (y)
    def _fit_axis(self, ax, axis, along_x: bool, renderer) -> None:
        labels = [label for label in axis.get_majorticklabels() if label.get_text()]  # Only the labels the chart shows
        if len(labels) < 2:
            return

        # The smallest gap between neighbouring ticks, in pixels
        positions = sorted(label.get_transform().transform(label.get_position())[0 if along_x else 1] for label in labels)
        gap = min(after - before for before, after in zip(positions, positions[1:]))
        if gap <= 0:
            return

        clearance = TICK_LABEL_GAP * self._figure.dpi / 72
        size = labels[0].get_fontsize()
        needed = max(self._footprint(label, along_x, renderer) for label in labels) + clearance
        passes = 0
        while needed > gap and passes < 3:
            fitted = size * gap / needed  # Text shrinks in proportion to its font size...
            if fitted < MIN_TICK_FONT_SIZE:
                break
            size = fitted
            for label in labels:
                label.set_fontsize(size)
            # ...roughly: glyphs are rounded to whole pixels, so small text comes out a little taller than predicted. Measure again
            needed = max(self._footprint(label, along_x, renderer) for label in labels) + clearance
            passes += 1
        if needed - clearance <= gap:
            return  # The labels fit (at worst with a little less clear space between them than asked for)

        step = math.ceil(needed * MIN_TICK_FONT_SIZE / size / gap)
        for number, label in enumerate(labels):
            label.set_fontsize(MIN_TICK_FONT_SIZE)
            if number % step:
                label.set_visible(False)
                self._thinned.add(label)

    # The room one label needs along its axis, in pixels, allowing for its rotation: a label standing up (90°) only needs its height,
    # a flat one its width, and a slanted one somewhere between (slanted neighbours can overlap in length without touching)
    @staticmethod
    def _footprint(label, along_x: bool, renderer) -> float:
        if label.get_rotation() % 90 == 0:  # Flat or standing: the box it is drawn in is exact
            box = label.get_window_extent(renderer)
            return box.width if along_x else box.height

        font = label.get_fontproperties()
        width, height, descent = renderer.get_text_width_height_descent(label.get_text(), font, ismath=False)
        # Matplotlib draws every line at least as tall as "lp" (a tall letter and a descender), whatever its own letters need
        _, line_height, line_descent = renderer.get_text_width_height_descent("lp", font, ismath=False)
        height = max(height - descent, line_height - line_descent) + max(descent, line_descent)
        angle = math.radians(label.get_rotation() % 180)   # Angle to the x axis
        if not along_x:
            angle = math.pi / 2 - angle                      # ...or to the y axis
        if abs(math.sin(angle)) < 1e-6:
            return width
        return min(height / abs(math.sin(angle)), width * abs(math.cos(angle)) + height * abs(math.sin(angle)))
