# ------- #
# Imports
# ------- #

import weakref

from matplotlib.text import Text

from src.data_manager.constants import DETAIL_GID, DETAIL_MIN_SCALE, MAX_TEXT_SCALE, MIN_TEXT_SCALE, YEAR_LABEL_PAD

# ----- #
# Class
# ----- #

# Keeps one chart window readable when the user makes it bigger or smaller.
# Text sizes are fixed in points, so without this the labels would keep their size while the window shrinks and pile on top of each other.
# This makes the text grow and shrink with the window (like a zoom), and hides the small numbers (bar totals, cell numbers) when there is no room for them
class ChartResizer:

    # figure is the window's chart; the size it has now is the size it was laid out for
    def __init__(self, figure) -> None:
        self._figure = figure
        self._design_size = tuple(float(size) for size in figure.get_size_inches())
        self._base_sizes = weakref.WeakKeyDictionary()  # Each text's font size at the design size
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
