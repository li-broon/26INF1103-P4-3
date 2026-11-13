# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from src.gui_manager.constants import (
    APP_SUBTITLE, APP_TITLE, DANGER, EMERGENCY_TEXT, HEADER_BG, HEADER_MUTED, HEADER_TEXT, ICON_FILE, WINDOW_HEIGHT,
    WINDOW_WIDTH, WINDOWS_APP_ID,
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
    def __init__(self, ai_manager, logic_manager, data_manager, chart_manager):
        self._set_up_windows_os()  # Must Happen Before the Window Exists
        super().__init__()
        self._chart_manager = chart_manager  # Handed in, Used but Not Owned (Association)
        self.title(APP_TITLE)

        # True Gives the Report Windows the Icon Too; Tk Copies the Image, so it Need Not be Kept
        self.iconphoto(True, tk.PhotoImage(file=ICON_FILE))
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

        # "View all charts" Button in the Tab Row, Just After the "Saved reports" Tab
        # (Each Tab is its Text Plus 20px Padding on Both Sides, and the Row Starts 20px In, as Set in theme.py)
        tab_font = tkfont.Font(font=font(10, "bold"))
        tabs_end = 20 + sum(tab_font.measure(tabs.tab(tab, "text")) + 40 for tab in tabs.tabs())
        ttk.Button(self, text="View all charts", style="Secondary.TButton",
                   command=self._show_all_charts).place(in_=tabs, x=tabs_end + 16, y=8)

    # Open Every Chart on One Page, Same as "All charts on one page" in the Terminal Menu (Waits Until the Chart Window is Closed)
    def _show_all_charts(self):
        self.configure(cursor="watch")  # Drawing the Charts Takes a Moment
        self.update_idletasks()
        try:
            shown, message = self._chart_manager.show_chart("all")
        finally:
            self.configure(cursor="")  # Always Put the Normal Cursor Back, Even if Drawing Failed

        # e.g. No Reports Saved Yet, or matplotlib Not Installed: Say Why Instead of Doing Nothing
        if not shown:
            messagebox.showinfo(APP_TITLE, message, parent=self)

    # Windows Only: Give the App its Own Taskbar Entry (Showing Our Icon, Not Python's), and Make Text Sharp on Scaled Screens
    def _set_up_windows_os(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Without This, Windows Stretches a Blurry Image
        except (AttributeError, OSError):
            pass  # Not Windows, or an Old Windows Version: Keep the Default
