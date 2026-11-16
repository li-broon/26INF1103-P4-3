# Imports

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import MUTED, PRIMARY_SOFT, SURFACE, TEXT
from src.gui_manager.theme import Theme

# Class

# Tab 4: pick a chart from the list and it is drawn inside the tab
class ChartsTab(ttk.Frame):
    def __init__(self, parent, chart_manager):
        super().__init__(parent)
        self._chart_manager = chart_manager
        self._canvas = None    # The chart being shown
        self._resizer = None   # Resizes the chart's text when the window changes size
        options = chart_manager.get_chart_options()
        self._choice = tk.StringVar(value=options[0][0] if options else "")

        # Left side: list of charts to choose from
        picker = Theme.card(self, side="left", fill="y", padx=(24, 12), pady=20)
        tk.Label(picker, text="CHOOSE A CHART", font=Theme.font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(16, 8))
        for key, title in options:
            tk.Radiobutton(picker, text=title, value=key, variable=self._choice, command=self.refresh, font=Theme.font(10),
                           fg=TEXT, bg=SURFACE, activebackground=PRIMARY_SOFT, selectcolor=SURFACE, anchor="w",
                           highlightthickness=0, padx=4, pady=4).pack(fill="x", padx=14)
        ttk.Button(picker, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(
            side="bottom", fill="x", padx=18, pady=16)

        # Right side: the chart, or a message if there is no chart
        self._chart_card = Theme.card(self, side="left", fill="both", expand=True, padx=(0, 24), pady=20)
        self._message = tk.Label(self._chart_card, text="Choose a chart on the left.", font=Theme.font(11), fg=MUTED, bg=SURFACE)
        self._message.place(relx=0.5, rely=0.5, anchor="center")

    # Draw the chosen chart using the latest saved reports
    def refresh(self):
        figure, message = self._chart_manager.build_chart(self._choice.get())
        self._clear_chart()
        if figure is None:
            # e.g. no reports yet, or matplotlib not installed
            self._message.configure(text=message)
            self._message.place(relx=0.5, rely=0.5, anchor="center")
            return

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from src.data_manager.charts.chart_resizer import ChartResizer
        self._message.place_forget()
        self._canvas = FigureCanvasTkAgg(figure, master=self._chart_card)
        self._canvas.get_tk_widget().configure(bg=SURFACE, highlightthickness=0)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self._resizer = ChartResizer(figure)
        self._canvas.draw_idle()

    # Remove the old chart before drawing a new one
    def _clear_chart(self):
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        self._canvas = None
        self._resizer = None
