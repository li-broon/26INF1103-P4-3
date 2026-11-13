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
        options = chart_manager.get_chart_options()
        self._choice = tk.StringVar(value=options[0][0] if options else "")

        # Left: the List of Charts (Taken from the ChartManager, so a New Chart Shows Up Here Without Changing this Tab)
        picker = card(self, side="left", fill="y", padx=(24, 12), pady=20)
        tk.Label(picker, text="CHOOSE A CHART", font=font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(16, 8))
        for key, title in options:
            tk.Radiobutton(picker, text=title, value=key, variable=self._choice, font=font(10),
                           fg=TEXT, bg=SURFACE, activebackground=PRIMARY_SOFT, selectcolor=SURFACE, anchor="w",
                           highlightthickness=0, padx=4, pady=4).pack(fill="x", padx=14)

        # Right: the Chart Itself, or a Message Saying Why there is No Chart
        self._chart_card = card(self, side="left", fill="both", expand=True, padx=(0, 24), pady=20)
        self._message = tk.Label(self._chart_card, text="Choose a chart on the left.", font=font(11), fg=MUTED, bg=SURFACE)
        self._message.place(relx=0.5, rely=0.5, anchor="center")
