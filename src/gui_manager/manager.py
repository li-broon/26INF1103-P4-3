# Imports

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from src.gui_manager.constants import (
    APP_SUBTITLE, APP_TITLE, DANGER, EMERGENCY_TEXT, HEADER_BG, HEADER_MUTED, HEADER_TEXT, ICON_FILE, WINDOW_HEIGHT,
    WINDOW_WIDTH, WINDOWS_APP_ID,
)
from src.gui_manager.display.window_report_formatter import WindowReportFormatter
from src.gui_manager.tabs.charts_tab import ChartsTab
from src.gui_manager.tabs.chat_tab import ChatTab
from src.gui_manager.tabs.mom_tab import MomTab
from src.gui_manager.tabs.reports_tab import ReportsTab
from src.gui_manager.theme import Theme

# Class

# Main window: shows the app in tabs instead of the terminal
class GUIManager(tk.Tk):
    def __init__(self, ai_manager, logic_manager, data_manager, chart_manager, mom_store=None):
        self._set_up_windows_os()  # Must run before the window is created
        super().__init__()
        self._chart_manager = chart_manager
        self.title(APP_TITLE)

        # App icon (also used by the pop-up windows)
        self.iconphoto(True, tk.PhotoImage(file=ICON_FILE))
        Theme.fit_window(self, WINDOW_WIDTH, WINDOW_HEIGHT)
        Theme.apply(self)

        # Header with the app name, then a red emergency reminder
        header = tk.Frame(self, bg=HEADER_BG)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=HEADER_BG)
        titles.pack(side="left", padx=24, pady=16)
        tk.Label(titles, text=APP_TITLE, font=Theme.font(16, "bold"), fg=HEADER_TEXT, bg=HEADER_BG).pack(anchor="w")
        tk.Label(titles, text=APP_SUBTITLE, font=Theme.font(10), fg=HEADER_MUTED, bg=HEADER_BG).pack(anchor="w")
        tk.Label(self, text=f"⚠  {EMERGENCY_TEXT}", font=Theme.font(10, "bold"), fg="#ffffff", bg=DANGER,
                 pady=7).pack(fill="x")

        # Tabs
        formatter = WindowReportFormatter()
        tabs = ttk.Notebook(self)
        self._reports_tab = ReportsTab(tabs, data_manager, formatter)
        self._mom_tab = MomTab(tabs, mom_store, data_manager, formatter) if mom_store is not None else None
        self._chat_tab = ChatTab(tabs, ai_manager, logic_manager, data_manager, formatter, on_saved=self._refresh_tabs)
        tabs.add(self._chat_tab, text="Report an incident")
        tabs.add(self._reports_tab, text="Saved reports")
        if self._mom_tab is not None:
            tabs.add(self._mom_tab, text="MOM reporting")
        self._charts_tab = ChartsTab(tabs, chart_manager)
        tabs.add(self._charts_tab, text="Charts")
        tabs.pack(fill="both", expand=True)
        # Draw the chart each time the Charts tab is opened
        tabs.bind("<<NotebookTabChanged>>",
                  lambda event: self._charts_tab.refresh() if tabs.select() == str(self._charts_tab) else None)
        # "View all charts" button placed just after the last tab
        tab_font = tkfont.Font(font=Theme.font(10, "bold"))
        tabs_end = 20 + sum(tab_font.measure(tabs.tab(tab, "text")) + 40 for tab in tabs.tabs())
        ttk.Button(self, text="View all charts", style="Secondary.TButton",
                    command=self._show_all_charts).place(in_=tabs, x=tabs_end + 24, y=8)

    # Called after a report is saved so the tables show it
    def _refresh_tabs(self):
        self._reports_tab.refresh()
        if self._mom_tab is not None:
            self._mom_tab.refresh()

    # Open every chart in one window
    def _show_all_charts(self):
        self.configure(cursor="watch")  # Loading cursor while the charts are drawn
        self.update_idletasks()
        try:
            shown, message = self._chart_manager.show_chart("all")
        finally:
            try:
                self.configure(cursor="")  # Put the normal cursor back
            except tk.TclError:
                pass  # The main window was already closed

        # e.g. no reports yet, or matplotlib not installed
        if not shown:
            messagebox.showinfo(APP_TITLE, message, parent=self)

    # Windows only: show our icon in the taskbar and keep text sharp
    def _set_up_windows_os(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Stops blurry text on scaled screens
        except (AttributeError, OSError):
            pass  # Not Windows, so skip this
