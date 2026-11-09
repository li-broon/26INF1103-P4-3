# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import (
    APP_SUBTITLE, APP_TITLE, DANGER, EMERGENCY_TEXT, HEADER_BG, HEADER_MUTED, HEADER_TEXT, WINDOW_HEIGHT, WINDOW_WIDTH,
)
from src.gui_manager.display.window_report_formatter import WindowReportFormatter
from src.gui_manager.tabs.chat_tab import ChatTab
from src.gui_manager.tabs.reports_tab import ReportsTab
from src.gui_manager.theme import apply_theme, fit_window, font

# ----- #
# Class
# ----- #

# Main Window: the Same Managers as IOManager, Shown in Tabs Instead of the Terminal
class GUIManager(tk.Tk):
    def __init__(self, ai_manager, logic_manager, data_manager):
        self._enable_sharp_text()  # Must Happen Before the Window Exists
        super().__init__()
        self.title(APP_TITLE)
        fit_window(self, WINDOW_WIDTH, WINDOW_HEIGHT)
        apply_theme(self)

        # Header Bar: App Name, then a Full-Width Red Strip with the Emergency Reminder
        header = tk.Frame(self, bg=HEADER_BG)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=HEADER_BG)
        titles.pack(side="left", padx=24, pady=16)
        tk.Label(titles, text=APP_TITLE, font=font(16, "bold"), fg=HEADER_TEXT, bg=HEADER_BG).pack(anchor="w")
        tk.Label(titles, text=APP_SUBTITLE, font=font(10), fg=HEADER_MUTED, bg=HEADER_BG).pack(anchor="w")
        tk.Label(self, text=f"⚠  {EMERGENCY_TEXT}", font=font(10, "bold"), fg="#ffffff", bg=DANGER,
                 pady=7).pack(fill="x")

        # Created and Owned by this Window (Composition); the Managers are Only Handed On
        formatter = WindowReportFormatter()
        tabs = ttk.Notebook(self)
        self._reports_tab = ReportsTab(tabs, data_manager, formatter)
        self._chat_tab = ChatTab(tabs, ai_manager, logic_manager, formatter, on_saved=self._reports_tab.refresh)
        tabs.add(self._chat_tab, text="Report an incident")
        tabs.add(self._reports_tab, text="Saved reports")
        tabs.pack(fill="both", expand=True)

    # Make Text Sharp on Windows Screens Scaled Above 100% (Without This, Windows Stretches a Blurry Image)
    def _enable_sharp_text(self):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass  # Not Windows, or an Old Windows Version: Keep the Default
