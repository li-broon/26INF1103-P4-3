# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import messagebox, ttk

from src.io_manager.constants import FILTER_COLUMNS, TABLE_COLUMNS, TRANSCRIPT_COLUMN
from src.gui_manager.constants import (
    ALL_REPORTS, APP_TITLE, BG, DANGER, DANGER_SOFT, KEYWORD_FILTER_COLUMNS, MUTED, STAT_CARDS, SURFACE, SURFACE_ALT, TEXT,
)
from src.gui_manager.theme import card, font
from src.gui_manager.windows.report_window import ReportWindow

# ----- #
# Class
# ----- #

# Tab 2: Browse and Filter Saved Reports, Most Urgent First
class ReportsTab(ttk.Frame):
    def __init__(self, parent, data_manager, formatter):
        super().__init__(parent)
        # Handed in by GUIManager, Used but Not Owned (Association)
        self._data_manager = data_manager
        self._formatter = formatter
        self._table = None  # The Reports Currently Listed (a DataFrame, Most Urgent First)

        # Summary Cards (Always Count Every Saved Report, Whatever the Filter)
        stats_row = tk.Frame(self, bg=BG)
        stats_row.pack(fill="x", padx=24, pady=(20, 12))
        self._stat_labels = {}
        for column, (key, caption, colour) in enumerate(STAT_CARDS):
            stat = card(stats_row)
            stat.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
            stats_row.columnconfigure(column, weight=1, uniform="stats")
            tk.Label(stat, text=caption, font=font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(14, 0))
            number = tk.Label(stat, text="0", font=font(22, "bold"), fg=colour, bg=SURFACE)
            number.pack(anchor="w", padx=18, pady=(0, 12))
            self._stat_labels[key] = number

        # Filter Bar (Buttons Packed First so They Keep their Size when the Window is Narrow)
        bar_card = card(self, fill="x", padx=24, pady=(0, 12))
        bar = tk.Frame(bar_card, bg=SURFACE)
        bar.pack(fill="x", padx=16, pady=12)
        ttk.Button(bar, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Clear", style="Secondary.TButton", command=self.clear_filter).pack(side="right", padx=8)
        ttk.Button(bar, text="Apply", style="Primary.TButton", command=self.apply_filter).pack(side="right")

        ttk.Label(bar, text="FILTER BY", style="CardMuted.TLabel").pack(side="left")
        self._column_box = ttk.Combobox(bar, state="readonly", width=15, font=font(10),
                                        values=[ALL_REPORTS] + [heading for heading, _ in FILTER_COLUMNS])
        self._column_box.set(ALL_REPORTS)
        self._column_box.pack(side="left", padx=(10, 18))
        self._column_box.bind("<<ComboboxSelected>>", self._column_changed)

        ttk.Label(bar, text="VALUE", style="CardMuted.TLabel").pack(side="left")
        self._value_box = ttk.Combobox(bar, state="disabled", width=22, font=font(10))
        self._value_box.pack(side="left", padx=(10, 18))
        self._value_box.bind("<Return>", self.apply_filter)
        self._value_box.bind("<KP_Enter>", self.apply_filter)  # The Number Pad's Enter on Linux and macOS
        self._value_box.bind("<<ComboboxSelected>>", self.apply_filter)

        # Status Line and Hint
        info = tk.Frame(self, bg=BG)
        info.pack(fill="x", padx=26, pady=(0, 8))
        self._status = tk.Label(info, text="", font=font(10, "bold"), fg=TEXT, bg=BG)
        self._status.pack(side="left")
        tk.Label(info, text="Double-click a report to open it   ·   Red rows: hospitalised or MOM reportable",
                 font=font(9), fg=MUTED, bg=BG).pack(side="right")

        # Report Table
        table_card = card(self, fill="both", expand=True, padx=24, pady=(0, 20))
        self._tree = ttk.Treeview(table_card, columns=["number"] + [column for _, column, _ in TABLE_COLUMNS],
                                  show="headings", selectmode="browse")
        self._tree.heading("number", text="NO.")
        self._tree.column("number", width=56, anchor="center", stretch=False)
        centred = ("importance_score", "hospitalised", "ai_severity")
        for heading, column, width in TABLE_COLUMNS:
            anchor = "center" if column in centred else "w"
            self._tree.heading(column, text=heading.upper(), anchor=anchor)
            self._tree.column(column, width=width * 10, anchor=anchor)
        self._tree.tag_configure("odd", background=SURFACE_ALT)
        self._tree.tag_configure("alert", foreground=DANGER, background=DANGER_SOFT)

        scrollbar = ttk.Scrollbar(table_card, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.bind("<Double-1>", self.open_selected)
        self._tree.bind("<Return>", self.open_selected)
        self._tree.bind("<KP_Enter>", self.open_selected)

        # Shown over the Table when there is Nothing to List
        self._empty = tk.Label(table_card, text="", font=font(11), fg=MUTED, bg=SURFACE)

        self.refresh()

    # (Heading, data.csv Column) Chosen in the Column Box, or (None, None) for All Reports
    def _chosen_column(self):
        for heading, column in FILTER_COLUMNS:
            if heading == self._column_box.get():
                return heading, column
        return None, None

    # Fill the Value Box for the Chosen Column: Saved Values to Pick, or Free Typing for Location
    def _column_changed(self, event=None):
        _, column = self._chosen_column()
        self._value_box.set("")
        if column is None:
            self._value_box.configure(state="disabled", values=[])
            self.refresh()
        elif column in KEYWORD_FILTER_COLUMNS:
            self._value_box.configure(state="normal", values=[])
            self._value_box.focus_set()
        else:
            self._value_box.configure(state="readonly", values=self._data_manager.get_unique_values(column))

    # Put a Table of Reports into the Treeview, and Update the Summary Cards from Every Saved Report
    def _show(self, table, status, empty_message=""):
        self._table = table
        self._tree.delete(*self._tree.get_children())
        for number, report in enumerate(table.to_dict("records"), start=1):
            if self._formatter.needs_attention(report):
                tags = ("alert",)
            else:
                tags = ("odd",) if number % 2 == 0 else ()
            self._tree.insert("", "end", iid=str(number), values=self._formatter.table_row_values(number, report), tags=tags)
        self._status.configure(text=status)

        if table.empty:
            self._empty.configure(text=empty_message)
            self._empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._empty.place_forget()

        for key, value in self._formatter.report_stats(self._data_manager.load_records()).items():
            self._stat_labels[key].configure(text=str(value))

    # Reload Every Saved Report, Keeping the Current Filter if One is Applied
    def refresh(self):
        _, column = self._chosen_column()
        if column is not None and self._value_box.get().strip():
            self.apply_filter()
            return
        table = self._data_manager.load_records()
        if table.empty:
            self._show(table, "No reports yet", "No incident reports have been saved yet.")
            return
        self._show(table, f"All reports  ·  {len(table)} total, most urgent first")

    # Show Only the Reports Matching the Chosen Column and Value
    def apply_filter(self, event=None):
        heading, column = self._chosen_column()
        if column is None:
            self.refresh()
            return
        value = self._value_box.get().strip()
        if not value:
            messagebox.showinfo(APP_TITLE, f"Choose or type a value for {heading} first.", parent=self)
            return

        matches = self._data_manager.load_matching_records(column, value)
        if matches.empty:
            self._show(matches, f"{heading}: {value}  ·  0 found", f"No reports found where {heading} is '{value}'.")
            return
        self._show(matches, f"{heading}: {value}  ·  {len(matches)} found, most urgent first")

    # Go Back to Showing Every Report
    def clear_filter(self):
        self._column_box.set(ALL_REPORTS)
        self._column_changed()

    # Open the Highlighted Row in its Own Window (a Double-Click on the Headings or Empty Space is Ignored)
    def open_selected(self, event=None):
        if event is not None and event.num == 1 and self._tree.identify_region(event.x, event.y) != "cell":
            return
        selected = self._tree.selection()
        if not selected or self._table is None:
            return
        number = int(selected[0])
        report = self._table.iloc[number - 1].to_dict()
        transcript = self._data_manager.load_transcript(report.get(TRANSCRIPT_COLUMN))
        ReportWindow(self, self._formatter, report, f"Report #{number}", transcript=transcript)
