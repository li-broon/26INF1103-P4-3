# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import MUTED, PRIMARY_SOFT, SURFACE, TEXT
from src.gui_manager.theme import card, font

# ----- #
# Class
# ----- #

# Tab 4: One Chart at a Time. Pick a Chart on the Left and it is Drawn Inside the Tab (No Extra Window, the App Keeps Working)
class ChartsTab(ttk.Frame):
    def __init__(self, parent, chart_manager):
        super().__init__(parent)
        self._chart_manager = chart_manager  # Handed in by GUIManager, Used but Not Owned (Association)
        self._canvas = None                  # The Chart Currently Shown (a Matplotlib Tk Canvas), Replaced on Every Redraw
        self._resizer = None                 # Keeps the Chart's Text Readable as the Tab Changes Size (Must be Kept Alive)
        options = chart_manager.get_chart_options()
        self._choice = tk.StringVar(value=options[0][0] if options else "")

        # Left: the List of Charts (Taken from the ChartManager, so a New Chart Shows Up Here Without Changing this Tab)
        picker = card(self, side="left", fill="y", padx=(24, 12), pady=20)
        tk.Label(picker, text="CHOOSE A CHART", font=font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(16, 8))
        for key, title in options:
            tk.Radiobutton(picker, text=title, value=key, variable=self._choice, command=self.refresh, font=font(10),
                           fg=TEXT, bg=SURFACE, activebackground=PRIMARY_SOFT, selectcolor=SURFACE, anchor="w",
                           highlightthickness=0, padx=4, pady=4).pack(fill="x", padx=14)
        ttk.Button(picker, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(
            side="bottom", fill="x", padx=18, pady=16)

        # Right: the Chart Itself, or a Message Saying Why there is No Chart
        self._chart_card = card(self, side="left", fill="both", expand=True, padx=(0, 24), pady=20)
        self._message = tk.Label(self._chart_card, text="Choose a chart on the left.", font=font(11), fg=MUTED, bg=SURFACE)
        self._message.place(relx=0.5, rely=0.5, anchor="center")

    # Draw the Chosen Chart Again from the Saved Reports (Called on a Click, on Refresh, and Each Time the Tab is Opened)
    def refresh(self):
        figure, message = self._chart_manager.build_chart(self._choice.get())
        self._clear_chart()
        if figure is None:
            # e.g. No Reports Saved Yet, or matplotlib Not Installed: Say Why Instead of an Empty Space
            self._message.configure(text=message)
            self._message.place(relx=0.5, rely=0.5, anchor="center")
            return

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from src.data_manager.charts.chart_resizer import ChartResizer
        self._message.place_forget()
        self._canvas = FigureCanvasTkAgg(figure, master=self._chart_card)
        self._canvas.get_tk_widget().configure(bg=SURFACE, highlightthickness=0)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self._resizer = ChartResizer(figure)  # Refits the Text Each Time the Canvas is Resized
        self._canvas.draw_idle()

    # Remove the Old Chart so Redrawing Many Times Does Not Pile Up Canvases
    def _clear_chart(self):
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        self._canvas = None
        self._resizer = None
